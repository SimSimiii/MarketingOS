# MarketingOS worker - the persistent process a campaign run needs.
#
# Not a Lambda image. This is the container behind iac/worker.yaml, and it
# exists because a run drives two vendor CLIs as subprocesses for minutes at a
# time, keeps its execution registry and SSE broker in memory, and outlives
# anything Lambda will hold open. `app/runtime/work_limits.py` refuses to take
# a reservation when AWS_LAMBDA_FUNCTION_NAME is set, so on Lambda every job
# answers 503 by design; this image is the other half of that sentence.
#
# It runs the same `app.main:app` as `uvicorn` does locally. There is no
# worker-specific entry point and no Lambda-specific branch, because an
# application that behaves differently depending on how it was started is a bug
# waiting for a deployment to reveal it.
#
# Build and push it by hand, or from a sixth CodeBuild project modelled on the
# console's - see the runbook in iac/README.md.

# ── Python dependencies ──────────────────────────────────────────────────────
FROM public.ecr.aws/docker/library/python:3.12-slim AS deps

# build-essential and libpq-dev for anything that still compiles on arm64;
# dropped from the runtime stage, which is why this is a separate one.
RUN apt-get update \
 && apt-get install --yes --no-install-recommends build-essential libpq-dev \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY requirements.txt ./

# requirements.txt rather than requirements.lock: the lock carries the dev
# extra (pytest, ruff, the evaluation harness) and this image does not run
# tests. --require-hashes is what makes a deploy reproduce the build that was
# tested rather than whatever PyPI resolves today.
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir --require-hashes --prefix=/install -r requirements.txt

# ── Runtime ──────────────────────────────────────────────────────────────────
FROM public.ecr.aws/docker/library/python:3.12-slim AS runtime

# curl is the container health check in worker.yaml; libpq5 is psycopg's
# runtime half; nodejs and npm are here because both providers are CLIs that
# ship as npm packages, not Python libraries.
RUN apt-get update \
 && apt-get install --yes --no-install-recommends curl libpq5 ca-certificates gnupg \
 && mkdir -p /etc/apt/keyrings \
 && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key \
      | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
 && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_22.x nodistro main" \
      > /etc/apt/sources.list.d/nodesource.list \
 && apt-get update \
 && apt-get install --yes --no-install-recommends nodejs \
 && rm -rf /var/lib/apt/lists/*

# The two vendor CLIs, as build arguments so a version can be pinned without
# editing this file. Pinning matters more here than it looks: both providers
# parse what the CLI prints, so a release that changes an output format breaks
# a campaign rather than failing a build, and it does it whenever the image
# happens to be rebuilt.
#
# CLAUDE_CLI_VERSION is the version this repository has actually been run
# against. CODEX_CLI_VERSION defaults to `latest` because no version of it has
# been verified here - pin it to whatever `codex --version` reports on the
# machine where a run last worked, rather than trusting this default.
ARG CLAUDE_CLI_VERSION=2.1.162
ARG CODEX_CLI_VERSION=latest
RUN npm install --global --no-fund --no-audit \
      "@anthropic-ai/claude-code@${CLAUDE_CLI_VERSION}" \
      "@openai/codex@${CODEX_CLI_VERSION}" \
 && npm cache clean --force

COPY --from=deps /install /usr/local

# Not root. The CLIs write their OAuth credentials under $HOME, so this user
# needs a home it owns - worker.yaml mounts a volume over it so a sign-in
# survives a restart of the process, though not a replacement of the task.
RUN groupadd --system --gid 1001 app \
 && useradd --system --uid 1001 --gid app --home-dir /home/app --create-home app

WORKDIR /srv
COPY --chown=app:app . /srv

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HOME=/home/app \
    APP_ENV=production \
    PORT=8000

# No ANTHROPIC_API_KEY and no OPENAI_API_KEY, in this file or in the task
# definition. Both providers bill a subscription through their CLI, and a
# visible API key makes the CLI switch to API-key billing and charge a card.
# `_clean_env()` in each provider strips the key defensively; not setting it is
# the other half.

USER app
EXPOSE 8000

# One worker process, and that is a correctness constraint rather than a
# sizing one: the execution registry and the SSE broker are in-memory and
# process-local, and `reap_orphaned_executions()` at startup fails every
# execution still marked RUNNING. A second process would kill the first one's
# campaigns. See docs/deployment.md.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
