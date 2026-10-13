# Deploying MarketingOS

> **Lambda rollout, 12 October 2026:** email launch dispatches a Standard Step Functions
> workflow (Plan, Craft per email, Finish), with durable admission, budgets,
> cancellation and failure recovery. Knowledge compilation, LinkedIn tools and market jobs use an
> asynchronous Lambda with persisted status. Production uses metered API providers,
> private Aurora, and the NAT egress stack in `iac/egress.yaml`.
> Provider keys must be valid in SSM before real generation is usable. LinkedIn campaigns finish in the planning Lambda.
> Synchronous model-based image ingestion is not migrated by this workflow.
> Credit billing is refused on distributed jobs until integrated.
> Apply migrations through `d91c382aa410`; see [rollout evidence](deployments/2026-10-12.md).

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

Everything that runs is a Python Lambda behind API Gateway; everything the
browser loads - both consoles and the landing page - is static on S3; Aurora
Serverless v2 pauses to zero; secrets are in SSM Parameter Store. Deploys are
CodeBuild builds started by hand, on the branch chosen at start. Each product is one CloudFront domain with
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

With `CAMPAIGN_WORKFLOW_ARN` set, email generation is handed to Step Functions before
returning to the browser. Model work executes in separate Lambda invocations and
stores the request, context, cursor, usage and cancellation in PostgreSQL.
Ambiguous model failures are not automatically retried; accepted emails are recovered.
An individual step still has a 900-second ceiling, so a slow step can degrade a run.
The 15-minute reconciler repairs stranded campaign and background admissions.

With `BACKGROUND_FUNCTION_NAME` set, market and knowledge launchers dispatch an
asynchronous Lambda, with a durable claim preventing duplicate delivery from buying
another run. These jobs have a single-invocation 900-second limit. Failure and timeout
are visible through saved status. Their model budget stops new calls before timeout.

Job Lambdas read `/marketingos/<environment>/anthropic-api-key` and `openai-api-key`
from SSM with a 60-second cache. API usage is billed separately from CLI subscriptions.
The private subnets need NAT egress for model APIs; `iac/egress.yaml` provisions a
single NAT gateway. This incurs ongoing charges and is not a multi-AZ egress design.
The scheduled reconciler can also prevent Aurora from remaining paused for long.

Without these deployment variables, the local single-process CLI execution path stays
available. Its in-memory admission and cancellation require a single persistent worker.

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
- **The console is a static export**, like the back-office. Its build bakes
  `NEXT_PUBLIC_API_URL=/api` (relative, so a domain change needs no rebuild).
  The API sets the session cookies itself - the access token readable by the
  console's script, the refresh token httpOnly and scoped to `/api/auth` - and
  a CloudFront function serves the one page exported per dynamic route for
  every real id, redirecting slash-less paths to the slashed form the export
  was built in.
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

- **Prepaid payments remain disabled in this deployment.** Stripe checkout and
  credit accounting exist in code but still require the qualification in
  `docs/billing.md` before activation. The
  MRR figure on the overview is the plan mix times a price map in
  `ADMIN_PLAN_PRICES` — an estimate, and labelled one.
- **No email.** No verification, no password reset by mail. `UserStatus.PENDING`
  and `email_verified_at` exist so turning verification on later is a policy
  change rather than a migration; a forgotten password is currently a support
  request and `scripts/create_user --reset-password`.
- **Password attempts are limited per identity and endpoint in the database.**
  API Gateway also throttles per stage; a distributed attack across many
  identities still needs a separate edge policy.
- **A single worker.** The SSE broker and the execution registry are in-memory
  and process-local. Correct for one worker, and the first thing a second one
  would have to move to Redis.
