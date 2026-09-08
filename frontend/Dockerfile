# MarketingOS console - Next.js on Lambda, via the AWS Lambda Web Adapter.
#
# Why an image and not a zip: this app renders on the server. Its pages are
# server components that call the API with the caller's cookie, so exporting it
# to static HTML is not an option - the pages would be rendered at build time,
# before anybody had signed in.
#
# The Web Adapter is an extension that translates a Lambda invocation into an
# ordinary HTTP request to localhost, so Next runs unmodified. No custom
# handler, no adapter library, nothing to keep in step with Next's releases -
# which matters on a framework that has renamed a file convention this year.
#
# Build with `sam build` (see template.yaml) rather than by hand; SAM tags and
# pushes it to ECR as part of the deploy.

# ── Dependencies ─────────────────────────────────────────────────────────────
FROM public.ecr.aws/docker/library/node:22-slim AS deps
WORKDIR /app
COPY package.json package-lock.json ./
# `npm ci` from the lockfile: a deploy that resolves versions afresh is a
# deploy that can differ from the one that was tested.
RUN npm ci

# ── Build ────────────────────────────────────────────────────────────────────
FROM public.ecr.aws/docker/library/node:22-slim AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# NEXT_PUBLIC_* is inlined into the client bundle at build time, so these have
# to be present here. They are not secrets - they are the API's public URL and
# a boolean - which is why they are build arguments rather than runtime config.
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_AUTH_REQUIRED=true
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_AUTH_REQUIRED=$NEXT_PUBLIC_AUTH_REQUIRED
ENV NEXT_TELEMETRY_DISABLED=1

RUN npm run build

# ── Runtime ──────────────────────────────────────────────────────────────────
FROM public.ecr.aws/docker/library/node:22-slim AS runner
WORKDIR /app

# The adapter, copied in as a Lambda extension.
COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:0.9.1 /lambda-adapter /opt/extensions/lambda-adapter

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000
# How long the adapter waits for Next to answer its first health check before
# declaring the container dead. A cold start of the Next server is comfortably
# under this; the default is not.
ENV AWS_LWA_READINESS_CHECK_PATH=/api/health
ENV AWS_LWA_READINESS_CHECK_PROTOCOL=http

# Not root. The adapter and Next both run happily as an unprivileged user, and
# a container that never needs to write outside /tmp has no reason to be able
# to.
RUN groupadd --system --gid 1001 nodejs \
 && useradd --system --uid 1001 --gid nodejs nextjs

# `standalone` already contains the server and the node_modules it reaches;
# `static` and `public` are served from disk beside it.
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/public ./public

USER nextjs
EXPOSE 3000
CMD ["node", "server.js"]
