# Deploying MarketingOS

Five stacks, deployed in this order, each consuming the previous one's outputs.

| # | What | Where | Deployed by |
|---|------|-------|-------------|
| 1 | Aurora Serverless v2 Postgres + the VPC around it | `iac/database.yaml` | by hand, once |
| 2 | Platform API | `backend/` | CodeBuild → `backend/buildspec.yml` |
| 3 | Console (the product) | `frontend/` | CodeBuild → `frontend/buildspec.yml` |
| 4 | Back-office API + hosting | `administration/backend/` | CodeBuild → its `buildspec.yml` |
| 5 | Back-office console | `administration/frontend/` | CodeBuild → its `buildspec.yml` |

Plus `landing-page/`, which is independent of all of them except for the URL it
links to.

The CloudFormation for everything those stacks sit on - the secrets, the
database, the five CodeBuild projects, the CloudFront Free-plan subscriptions
and the optional worker - is in [iac/](../iac/README.md), which also carries
the request path, the per-service cost breakdown and **the ordered runbook.
Follow that one**; this page explains the constraints behind it.

Everything that runs is serverless and a zip package: Python Lambdas behind
API Gateway for both APIs, a Node.js Lambda for the console's server-rendered
pages, S3 for everything static, Aurora Serverless v2 that pauses to zero,
secrets in SSM Parameter Store. Each product is one CloudFront domain with
`/api/*` routed to its API Gateway, so browsers never make a cross-origin call.

---

## Run monitoring and background execution

The September security corrections, quota semantics, dependency locks and database upgrade
procedure are documented in [review-implementation.md](review-implementation.md). Apply the
new migrations before restarting an existing installation. Model job admission now returns
HTTP 503 on Lambda instead of accepting work that this host cannot finish.

The console uses short authenticated HTTP requests to read saved progress. The
Runs board, execution details, market research and knowledge compilation load
on entry and refresh only when the user presses Refresh. No browser opens an
SSE connection or polls periodically. The legacy `/executions/{id}/stream`
endpoint remains for compatibility; the console does not need it.

This removes streaming from the hosting requirements, but **does not turn the
current model runner into a Lambda job**. Campaigns, compilation, market
research and LinkedIn work still launch tasks in the API process and invoke
subscription-authenticated CLIs. Returning HTTP 202 does not transfer that work
to a durable worker. Standard Lambda invocations have a maximum duration of
900 seconds, and unfinished background work cannot be relied on after the
handler returns. See [AWS timeout documentation](https://docs.aws.amazon.com/lambda/latest/dg/configuration-timeout.html)
and [execution lifecycle](https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtime-environment.html).

For the current implementation, run the API as a single persistent process
with the CLIs installed and authenticated. A container can provide this; an EC2
machine dedicated to streaming is unnecessary. Do not split only campaign
start and stream routes onto a worker: restart, cancellation, market job status
and compilation also depend on process-local state. Startup recovery assumes
one worker and must not run independently on multiple replicas sharing a DB.

A future deployment with no continuously running worker needs an explicit job
handoff (for example a durable queue plus on-demand container tasks), shared
Postgres storage, durable cancellation/status for every job type, CLI credential
provisioning, and worker-aware recovery. None of that infrastructure is deployed
by this feature. The Lambda stack remains suitable for reads/CRUD with lifespan
startup recovery disabled, not for the existing in-process job launchers.

LinkedIn search/message status, results, usage and errors are persisted in
`linkedinrun`; an interrupted job is marked failed at single-worker startup so
it can be retried explicitly. This preserves history, not resumable execution.

Both providers continue to bill through their CLIs. `_clean_env()` still strips
vendor API keys to prevent an accidental switch to API-key billing.

---

## The constraints behind the runbook

- **The database is private.** Aurora sits in private subnets with no NAT and
  no public endpoint. Schema changes go through the migration Lambda, which
  the API build invokes after every deploy and fails on; routine operator
  tasks go through functions too (`marketingos-admin-bootstrap-<env>`).
- **The first request after an idle spell waits.** Aurora pauses after five
  minutes without a connection and takes ~15 seconds to resume. On Lambda the
  engine opens one connection per request (`app/core/database.py`) - a pooled
  connection held by a frozen container would keep it awake and billing.
- **Secrets are SSM SecureStrings**, created by `iac/parameters.sh`, which
  never overwrites. `JWT_SECRET` can rotate (it signs everybody out);
  `PASSWORD_PEPPER` and `ADMIN_PWD_PEPPER` can never rotate, because every
  password hash is made with them. A production process refuses to start with
  the development values of the first two, and forces `AUTH_REQUIRED` on.
- **The two signing secrets must differ.** `ADMIN_JWT_SECRET` and `JWT_SECRET`
  are generated independently; the back-office buildspec fails if they match.
  The back-office does receive the platform's `PASSWORD_PEPPER` - under the
  name `PLATFORM_PASSWORD_PEPPER`, and only to create test accounts.
- **The console renders on the server**, which is why it is a Lambda and not a
  bucket like the back-office. Its build bakes `NEXT_PUBLIC_API_URL=/api`
  (relative, so a domain change needs no rebuild); its server side reads
  `API_INTERNAL_URL`, set by the stack. Its own route handlers - sign-in,
  refresh, downloads - live under `/bff/*`, because `/api/*` on the same domain
  is the API's.
- **CloudFront error pages apply to every behavior**, API included. The
  back-office maps only 404 to its error page, so an API 403 stays JSON.

---

## Letting people in

Public signup is **off** by default (`ALLOW_PUBLIC_SIGNUP=false`). Every run
spends model quota, so an open form is a bill rather than a funnel until there
is metering behind it. On AWS, testers get their accounts from the back-office:
**Accounts → Create a test account**, with a password you choose or one
generated and shown once. Against a database you can reach directly (a laptop),
the script does the same:

```bash
cd backend
python -m scripts.create_user --email tester@example.com --plan pro --quota 25
```

An existing database from before accounts existed has brands and campaigns with
no owner. The migration leaves them that way deliberately - there was nobody to
attribute them to, and guessing would hand somebody's work to an account they
never created. Adopt them explicitly:

```bash
python -m scripts.claim_workspace --email you@example.com --dry-run
python -m scripts.claim_workspace --email you@example.com
```

Until that runs, unowned rows are invisible on any deployment with
`AUTH_REQUIRED=true`.

### Upgrading a development database

A local `marketingos.db` was built by `init_db()`, which runs
`SQLModel.metadata.create_all` on every startup. That creates missing *tables*
and never missing *columns*, so starting the server after pulling this branch
leaves a database with the four new account tables and without
`brand.owner_id` — and the first page load fails with:

```
sqlite3.OperationalError: no such column: campaign.owner_id
```

The migrations are guarded against exactly this and will skip whatever
`create_all` already made, but the version table has to say where it is
first. Check it, stamp it at the revision that describes the schema you
actually have, then upgrade:

```bash
cd backend
.venv/Scripts/python.exe -m alembic current
.venv/Scripts/python.exe -m alembic stamp <that revision>
.venv/Scripts/python.exe -m alembic upgrade head
.venv/Scripts/python.exe -m alembic check   # should say: no new upgrade operations
```

Take a copy of the file first. `alembic check` at the end is the part that
matters — it compares the migrated schema against the models and is the only
thing that will tell you the two now agree.

---

## Trying it locally

`.claude/launch.json` has four extra entries beside the usual pair:

- `backend-auth` — the API on :8010 with `AUTH_REQUIRED=true`,
  `ALLOW_PUBLIC_SIGNUP=true`, against `marketingos-auth-demo.db`, so the real
  dev database is untouched.
- `frontend-auth` — the console on :3010 pointed at it.
- `admin-api` / `admin-console` — the back-office on :8011 and :3011, against
  that same demo database.

Sign up at <http://localhost:3010/register>, then:

```bash
cd administration/backend
PYTHONPATH=../../backend DATABASE_URL=sqlite:///../../backend/marketingos-auth-demo.db \
  python -m scripts.bootstrap_admin --email you@example.com
```

and the account shows up in the back-office at <http://localhost:3011>.

---

## What is deliberately missing

- **No payment processing.** `UserPlan` and the quota counters exist, the
  back-office can read and grant against them, and nothing charges anybody. The
  MRR figure on the overview is the plan mix times a price map in
  `ADMIN_PLAN_PRICES` — an estimate, and labelled one.
- **No email.** No verification, no password reset by mail. `UserStatus.PENDING`
  and `email_verified_at` exist so turning verification on later is a policy
  change rather than a migration; a forgotten password is currently a support
  request and `scripts/create_user --reset-password`.
- **No rate limiting beyond API Gateway's.** The throttles in the templates are
  per-stage, not per-account.
- **A single worker.** The SSE broker and the execution registry are in-memory
  and process-local. Correct for one worker, and the first thing a second one
  would have to move to Redis.
