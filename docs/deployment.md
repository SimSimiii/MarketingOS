# Deploying MarketingOS

Five stacks, deployed in this order, each consuming the previous one's outputs.

| # | What | Where | Deployed by |
|---|------|-------|-------------|
| 1 | Postgres + the VPC around it | `infrastructure/database.yaml` | by hand, once |
| 2 | Platform API | `backend/` | CodeBuild → `backend/buildspec.yml` |
| 3 | Console (the product) | `frontend/` | CodeBuild → `frontend/buildspec.yml` |
| 4 | Back-office API + hosting | `administration/backend/` | CodeBuild → its `buildspec.yml` |
| 5 | Back-office console | `administration/frontend/` | CodeBuild → its `buildspec.yml` |

Plus `landing-page/`, which is independent of all of them except for the URL it
links to.

---

## Read this first: what does not run on Lambda

The API stack serves everything **except starting a campaign run.**

A run drives the `claude` and `codex` CLIs as subprocesses for minutes at a
time, streams its progress over SSE, and keeps its cancellation registry in the
process's memory. A Lambda function is capped at fifteen minutes, has no CLI on
its image, scales to twenty copies that cannot see each other's registry, and
its SSE response is buffered by API Gateway. All four fail at once.

So `POST /campaigns/{id}/start` and `GET /executions/{id}/stream` need a
**long-running worker**: one container or one small EC2 instance running the
same `uvicorn app.main:app`, with the CLIs installed and authenticated, pointed
at the same database. Route those two paths there and everything else at the
Lambda. Nothing in the code needs to change - it is the same application - which
is why this is a routing decision rather than a rewrite.

If that split is not worth the trouble yet, run the whole API on that one
container and use the Lambda stack for the back-office only, which is pure CRUD
and fits Lambda exactly.

This is also why `AI_PROVIDER` credentials do not appear anywhere in these
templates. Both providers bill a *subscription* through their CLI, and
`_clean_env()` in each provider strips the vendor API key from the subprocess
environment specifically so a stray key cannot silently move billing onto a
card. A Lambda that never runs a campaign never needs either.

---

## 1. Database and network

```bash
aws cloudformation deploy \
  --template-file infrastructure/database.yaml \
  --stack-name marketingos-data-prod \
  --parameter-overrides Environment=prod DBPassword="$(openssl rand -base64 24 | tr -d '/@\"')" \
  --capabilities CAPABILITY_IAM
```

Take `DatabaseEndpoint`, `VpcSubnetIds` and `VpcSecurityGroups` from the
outputs. Build the URL yourself and put it in Secrets Manager:

```
postgresql+psycopg://marketingos:<password>@<endpoint>:5432/marketingos
```

The instance is not publicly reachable, on purpose. Schema changes go through
the migration Lambda in the next stack, not through a laptop.

## 2. Secrets

Generate three, once, and never rotate two of them casually:

```bash
python -c "import secrets; print(secrets.token_hex(32))"   # JWT_SECRET
python -c "import secrets; print(secrets.token_hex(32))"   # PASSWORD_PEPPER
python -c "import secrets; print(secrets.token_hex(32))"   # ADMIN_JWT_SECRET
python -c "import secrets; print(secrets.token_hex(32))"   # ADMIN_PWD_PEPPER
```

- `JWT_SECRET` — rotating it signs everybody out. Survivable.
- `PASSWORD_PEPPER` — **rotating it invalidates every password in the
  database.** Treat it as permanent from the moment there is a second account.
- `ADMIN_JWT_SECRET` must differ from `JWT_SECRET`. The back-office buildspec
  fails the build if they match; two systems that accept each other's tokens
  are one system.
- `ADMIN_PWD_PEPPER` must be the value `bootstrap_admin.py` ran with, or no
  operator can sign in.

A production process refuses to start while `JWT_SECRET` or `PASSWORD_PEPPER`
are still their development defaults, and forces `AUTH_REQUIRED` on regardless
of what the parameter said. Both are startup failures rather than warnings,
because the alternative failure is silent.

## 3. Platform API

Create a CodeBuild project pointed at `backend/buildspec.yml` with the
environment variables listed at the top of `backend/samconfig.yaml`. The build
runs `ruff` and the full test suite before it deploys (~90 seconds, no model
quota - the suite is scripted-provider based), then invokes the migration
Lambda and fails if the migration fails.

Output `ApiEndpoint` is the base URL. The console wants it **with `/api`
appended**.

Migrations run separately from the API on purpose: concurrent cold starts would
race each other through the same revisions. To run one by hand:

```bash
aws lambda invoke --function-name marketingos-migrate-prod --payload '{}' out.json && cat out.json
```

## 4. Console

`frontend/buildspec.yml`. Needs **privileged mode** on the CodeBuild project -
it builds a Docker image - and an ECR repository.

The console renders on the server (its pages are server components that call
the API with the caller's cookie), so it cannot be a static export the way the
back-office is. It runs as a Lambda container image behind the AWS Lambda Web
Adapter, fronted by CloudFront. `NEXT_PUBLIC_API_URL` and
`NEXT_PUBLIC_AUTH_REQUIRED` are inlined into the client bundle at **image build
time**, so changing either needs a rebuild, not a stack update.

Then put the console's URL into the API's `CORS_ORIGINS` and redeploy the API.

## 5. Back-office

`administration/backend/buildspec.yml` first — it vendors `backend/app` into
the admin bundle so both share one definition of every model, builds an
isolated stack (`marketingos-admin-*`), and creates the console's bucket and
distribution.

First deploy is a two-step: `ADMIN_CORS_ORIGINS` has to name a CloudFront
domain that does not exist until the stack is created. Deploy, read
`AdminConsoleUrl`, set it, deploy again.

Then create the first operator. It has to run inside the VPC or through a
tunnel, with the same `ADMIN_PWD_PEPPER` the Lambda has:

```bash
cd administration/backend
PYTHONPATH=../../backend python -m scripts.bootstrap_admin --email you@example.com
```

Then `administration/frontend/buildspec.yml` for the console itself.

## 6. Landing page

```bash
aws cloudformation deploy \
  --template-file landing-page/template.yaml \
  --stack-name marketingos-landing-prod \
  --parameter-overrides Environment=prod
```

Then a CodeBuild project on `landing-page/buildspec.yml` with
`CONSOLE_APP_URL` set to the console's URL (no trailing slash). The build
fails if any `CONSOLE_APP_URL` placeholder survives substitution, so the page
can never ship with a dead sign-in link.

---

## Letting people in

Public signup is **off** by default (`ALLOW_PUBLIC_SIGNUP=false`). Every run
spends model quota, so an open form is a bill rather than a funnel until there
is metering behind it. Invite testers by hand:

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
