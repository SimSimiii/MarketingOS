# Infrastructure as code

Everything AWS holds for MarketingOS. Serverless end to end: Lambda (zip
packages only - no container image anywhere), API Gateway, S3, CloudFront,
Aurora Serverless v2, SSM Parameter Store. Four files here, four SAM or
CloudFormation templates beside the code they deploy, and one ordered runbook
below.

| File | Creates | Deployed |
|---|---|---|
| [`parameters.sh`](parameters.sh) | Eight SSM SecureStrings, five of them generated | once, first; never overwrites |
| [`database.yaml`](database.yaml) | VPC, two private subnets, two security groups, Aurora Serverless v2 Postgres | once, by hand |
| [`pipeline.yaml`](pipeline.yaml) | Five CodeBuild projects (GitHub through CodeConnections, webhooks), two IAM roles, artifact bucket | once, then updated |
| [`edge.yaml`](edge.yaml) | Three empty WAF web ACLs and three CloudFront **Free plan** subscriptions — **us-east-1** | twice: ACLs first, plans once the distributions exist |
| [`worker.yaml`](worker.yaml) | ECS Fargate service, ALB — **optional, not serverless, not deployed** | only for subscription billing |

The application stacks are not here, deliberately: a SAM template belongs next
to the code it packages, because `CodeUri: ./` is relative to it.
`backend/template.yaml`, `frontend/template.yaml`,
`administration/backend/template.yaml` and `landing-page/template.yaml` are
deployed by the CodeBuild projects `pipeline.yaml` creates.

## How a request travels

```
                 ┌─ /api/*          → API Gateway (HTTP) → Lambda (FastAPI, Python) ─┐
app.orqagent.com ┼─ /_next/static/* → S3 (build assets, OAC)                          ├→ Aurora Serverless v2
 (CloudFront)    └─ everything else → Lambda (Next.js server, Node.js, zip)           │   (private subnets)
                                                                                      │
admin.orqagent.com ┬─ /api/*        → API Gateway (HTTP) → Lambda (FastAPI, Python) ─┘
 (CloudFront)      └─ everything else → S3 (static export)

orqagent.com (CloudFront) → S3 (index.html)
```

Each domain is one CloudFront distribution, so the browser never leaves its
origin: no CORS, and no API hostname baked into a bundle. The console's pages
are rendered per request with the caller's cookie, which is why the console
has a server at all where the back-office is a static export; its own route
handlers live under `/bff/*` because `/api/*` belongs to the API.

---

## What each service is for, and what it costs

Monthly, eu-west-3, at the traffic this product currently has — which is none.

| Service | Why it is there | Idle cost |
|---|---|---|
| **Aurora Serverless v2** Postgres 16, 0–2 ACU | The only durable state. Pauses to zero after 5 idle minutes and bills storage only; the first request after that waits ~15 s for it to resume. The Lambdas open a connection per request so a frozen container cannot hold it awake. | ~$0.10 storage + ~$0.07 per hour actually used |
| **Lambda** × 8 (`api`, `migrate`, `console-web`, `plan`, `craft`, `finish`, `admin-api`, `admin-bootstrap`) | All zip packages. Python on arm64; the console is Node.js 22 on x86_64 with the AWS Lambda Web Adapter layer. | $0 (the permanent free tier covers 1M requests) |
| **API Gateway** (HTTP API) × 2 | The entry point to the Python Lambdas, reached through CloudFront's `/api/*`. | ~$0 ($1 per million requests) |
| **CloudFront** × 3 | Console, back-office, landing. On the flat-rate **Free plan**, which needs `PriceClass_All`. | $0 |
| **WAF** × 3 web ACLs | Empty. The Free plan will not subscribe a distribution without one, and includes it. | $0 |
| **S3** × 4 | Console assets, back-office export, landing page, build artifacts. All private; the three sites are read through an OAC. | < $0.10 |
| **SSM Parameter Store** | The eight secrets, as standard SecureStrings under the AWS-managed key. | $0 |
| **Step Functions** | Drives the campaign loop (plan → craft × N → finish). | $0 (4,000 transitions free) |
| **CodeBuild** | Five projects, built on push by webhook, each only when its own directory changed. | ~$0.05–0.15 per build |
| **CloudWatch** | Logs with a retention on every group, two alarms. | < $0.50 |
| **Route 53** | The existing `orqagent.com` zone; each stack writes its own alias records. | $0.50 (the zone) |
| **ACM, CodeConnections, VPC** | The us-east-1 wildcard certificate, the GitHub link, a VPC with no NAT and no public IP. | $0 |

**≈ $1–5/month** depending on how many hours the database is awake and how
many builds run. The previous shape - an RDS instance, eight Secrets Manager
secrets, an ECR image - was about $22 before a single user.

### Not deployed, and why

- **NAT Gateway** — $32/month before a byte moves. Nothing in the Lambda
  stacks calls the open web: `app/market/` does, and market work cannot run on
  Lambda anyway. It is also what a campaign run on Lambda would need to reach
  Anthropic or OpenAI - see *Billing* below.
- **ElastiCache / Redis** — the SSE broker and `ExecutionRegistry` are
  in-memory and process-local. Correct for one worker, and the first thing a
  second one would need.
- **SQS** — there is no durable job handoff yet. See the worker section.
- **Secrets Manager** — nothing here rotates, and two of the secrets must never
  rotate at all; Parameter Store holds them for nothing.
- **WAF rules, Shield, Multi-AZ, RDS Proxy** — protection and availability for
  traffic that does not exist yet.

---

## Compute, and why it is split the way it is

The API Lambda is **not** split by URL prefix, and the campaign pipeline **is**
split by email. Both were decided from measurements rather than taste.

### Splitting the API by route buys nothing

Importing a *single* route module pulled 190 `app.*` modules, the whole
marketing pipeline included, because every route imports `app/api/deps.py` and
that imported `CampaignService` and `KnowledgeService` at module scope:

```
python -X importtime -c "import app.main"     # 3.28s, 1363 modules
```

So an auth-only Lambda and a market-only Lambda would have had *identical* cold
starts. Eight functions, eight log groups, eight sets of alarms, nothing
measurable gained.

What did pay was removing work the function can never do. `claude_agent_sdk`
cost 0.98s of that import and bundles a **210 MB** CLI binary, and the API
function is forbidden from calling a model at all. It now lives behind the
`cli` extra in `pyproject.toml` and is absent from `requirements.txt`:

```
python -X importtime -c "import app.main"     # 2.19s, 1073 modules
```

A third off the cold start, 210 MB out of a 250 MB budget, one dependency
moved - and no new functions.

### The campaign pipeline is split by email, because it has to be

The presets set their own deadlines, and two of the three are past Lambda's
ceiling:

| Preset | Budget | Calls per email | Fits in one Lambda? |
|---|---|---|---|
| `fast` | 420s | 2-4 | yes |
| `balanced` | 1200s | 10-35 | **no** |
| `maximum` | 2400s | 10-44 | **no** |

But one email at `balanced` is roughly four minutes, well inside 900 seconds.
So the unit of work is an email, and the loop lives in Step Functions where
there is no timeout to exceed:

```
Plan ──▶ MoreEmails ──yes──▶ CraftEmail ──┐
            │  ▲                          │
            │  └──────────────────────────┘
            no
            ▼
         Finish
```

Three functions, all in `backend/template.yaml`, all reading
`backend/step_handlers.py`. Emails are **sequential, not parallel**: each is
written with `previous=` the ones before it, so a fan-out would produce five
first emails rather than a sequence.

Nothing but an execution id travels between states. The brief, the accepted
copy and the outcomes live in `campaignrunstate`; the artifacts, corpus and
market maps are reloaded from their own tables — which is both why the payload
stays far under the 256 KB state limit and why a step can run in a process that
has never seen the run.

`CraftEmail` is **idempotent on position**: the cursor and the email advance in
one commit, so a step retried after a timeout that had in fact succeeded writes
the next email rather than a duplicate.

### Billing, and the one setting that decides it

`AI_BILLING` picks which pair of backends `app.ai.factory` builds:

| | `subscription` (default) | `api` |
|---|---|---|
| Backends | `claude` / `codex` CLIs | Anthropic + OpenAI HTTP APIs |
| Pays | the operator's plans | a card, per token |
| Needs | an authenticated `$HOME`, subprocesses | an API key |
| Host | a laptop | **Lambda** |

It is never inferred from whether a key is present. A missing key raises rather
than falling back, because the two cost wildly different amounts and a
deployment that quietly started charging a card would be the mirror image of
the accident `_clean_env()` exists to prevent.

The three campaign functions set `AI_BILLING=api` and `JOB_HOST=true`. The API
function sets neither, and must not: `work_limits` refuses model work on a
Lambda without `JOB_HOST`, and that refusal is what stops a 30-second gateway
request from accepting a twenty-minute campaign.

**Cost has not been measured.** A `balanced` five-email campaign is 50 to 175
input-heavy calls. `ModelSession` counts tokens already — run one real campaign
locally and read the counters before pointing production at a card. The system
prompt is sent with `cache_control`, which is the single largest lever, since
every craft call resends the same role prompt and the same Evidence Ledger.

## Runbook

Ordered, because each step consumes the previous one's outputs. The examples
use `eu-west-3` and `prod`.

```bash
export AWS_DEFAULT_REGION=eu-west-3 ENV=prod
```

**On Windows**, two things about the CLI: set `AWS_CLI_FILE_ENCODING=UTF-8`
before any `file://` template (they contain box-drawing characters the default
code page cannot decode), and `MSYS_NO_PATHCONV=1` in Git Bash, which otherwise
rewrites `/aws/codebuild/...` and `/prod` into Windows paths.

### 0. What is live today (prod)

| | |
|---|---|
| Landing | https://orqagent.com |
| Console | https://app.orqagent.com |
| Back-office | https://admin.orqagent.com |
| Stacks, eu-west-3 | `marketingos-{data,pipeline,api,console,admin,landing}-prod` |
| Stack, us-east-1 | `marketingos-edge-prod` |

Public signup is **off**: testers get their accounts from the back-office
(step 10).

### 1. Parameters

```bash
ENV=prod bash iac/parameters.sh
```

Five values are generated and never printed. It never overwrites an existing
parameter, which is the point: `password-pepper` and `admin-pwd-pepper` are
folded into every password hash and must never change.

### 2. Database and network

```bash
aws cloudformation deploy \
  --template-file iac/database.yaml \
  --stack-name "marketingos-data-$ENV" \
  --parameter-overrides "Environment=$ENV" \
  --capabilities CAPABILITY_IAM
```

The master password is resolved from `/marketingos/$ENV/db-password` by
CloudFormation. About ten minutes. Then write the URL the other stacks read:

```bash
ENDPOINT=$(aws cloudformation describe-stacks --stack-name "marketingos-data-$ENV" \
  --query "Stacks[0].Outputs[?OutputKey=='DatabaseEndpoint'].OutputValue" --output text)
PASSWORD=$(aws ssm get-parameter --name "/marketingos/$ENV/db-password" \
  --with-decryption --query Parameter.Value --output text)
aws ssm put-parameter --overwrite --type SecureString \
  --name "/marketingos/$ENV/database-url" \
  --value "postgresql+psycopg://marketingos:$PASSWORD@$ENDPOINT:5432/marketingos"
```

Keep the subnets and security group; step 4 wants them:

```bash
aws cloudformation describe-stacks --stack-name "marketingos-data-$ENV" \
  --query "Stacks[0].Outputs" --output table
```

### 3. GitHub, and the Free-plan web ACLs

CodeBuild clones through a **CodeConnections** connection to GitHub, created
once in the console (Developer Tools → Connections) because it is an OAuth
grant. Its ARN is `GitHubConnectionArn` in step 4.

```bash
aws cloudformation deploy --region us-east-1 \
  --template-file iac/edge.yaml \
  --stack-name "marketingos-edge-$ENV" \
  --parameter-overrides "Environment=$ENV"
```

Three empty ACLs, one per distribution. Their ARNs go to the pipeline stack
(`ConsoleWebAclArn`, `AdminWebAclArn`) and to the landing stack (`WebAclArn`).

### 4. The five CodeBuild projects

```bash
aws cloudformation deploy \
  --template-file iac/pipeline.yaml \
  --stack-name "marketingos-pipeline-$ENV" \
  --parameter-overrides \
      "Environment=$ENV" \
      "GitHubRepositoryUrl=https://github.com/<owner>/MarketingOS" \
      "GitHubConnectionArn=arn:aws:codeconnections:..." \
      "VpcSubnetIds=subnet-aaa,subnet-bbb" "VpcSecurityGroups=sg-aaa" \
      "CertificateArn=arn:aws:acm:us-east-1:..." "HostedZoneId=Z..." \
      "ConsoleDomain=app.example.com" "AdminDomain=admin.example.com" \
      "CorsOrigins=https://app.example.com" "AdminCorsOrigins=https://admin.example.com" \
      "ConsoleAppUrl=https://app.example.com" \
      "ConsoleWebAclArn=..." "AdminWebAclArn=..." \
  --capabilities CAPABILITY_NAMED_IAM
```

Webhooks are off until `EnableWebhooks=true`. Turn them on once every
project has gone green by hand: from then on a push to the branch rebuilds
only the projects whose directory it touched.

### 5. Platform API

```bash
aws codebuild start-build --project-name "marketingos-build-api-$ENV"
```

Lints, runs the full suite (no model quota), deploys, then invokes the
migrator and fails the build if the migration fails. It must precede the
console: the console stack imports its endpoint.

### 6. Console

```bash
aws codebuild start-build --project-name "marketingos-build-console-$ENV"
```

`next build` on the build host, the standalone server zipped into a Node.js
Lambda, `.next/static` synced to S3. The browser's API URL is `/api`, so
changing the domain needs no rebuild.

### 7. Back-office

```bash
aws codebuild start-build --project-name "marketingos-build-admin-api-$ENV"
```

Then set `AdminFrontendBucket` and `AdminDistributionId` from its outputs on
the pipeline stack, and:

```bash
aws codebuild start-build --project-name "marketingos-build-admin-ui-$ENV"
```

### 8. Landing page

```bash
aws cloudformation deploy \
  --template-file landing-page/template.yaml \
  --stack-name "marketingos-landing-$ENV" \
  --parameter-overrides "Environment=$ENV" "DomainName=example.com" \
      "CertificateArn=..." "HostedZoneId=Z..." "WebAclArn=..."
```

Then set `LandingBucket`, `LandingDistributionId` and `ConsoleAppUrl` (no
trailing slash) on the pipeline stack, and build
`marketingos-build-landing-$ENV`.

### 9. Subscribe the three distributions to the Free plan

```bash
aws cloudformation deploy --region us-east-1 \
  --template-file iac/edge.yaml \
  --stack-name "marketingos-edge-$ENV" \
  --parameter-overrides "Environment=$ENV" \
      ConsoleDistributionId=E... AdminDistributionId=E... LandingDistributionId=E...
```

Three is the account's ceiling on Free plans; one held elsewhere has to be
cancelled first. A distribution restricted to `PriceClass_100` is refused as
"not eligible for this subscription tier".

### 10. People: the first operator, then testers

The database is not reachable from outside the VPC, so the operator bootstrap
is a function with no HTTP route. Run it yourself, with your own password -
it is never stored anywhere but as a bcrypt hash:

```bash
aws lambda invoke --function-name "marketingos-admin-bootstrap-$ENV" \
  --cli-binary-format raw-in-base64-out \
  --payload '{"email": "you@example.com", "password": "at-least-12-characters"}' out.json
cat out.json
```

`"reset_password": true` in the payload resets an existing operator. That
operator is the only one who can sign in to the back-office until they add
others under *Operators*.

Tester accounts are created in the back-office under **Accounts → Create a
test account** (role `admin` or above). Leave the password blank to have one
generated and shown once.

### Building from a working tree instead of GitHub

Every project also builds from a zip in the artifact bucket - how a change
that is not pushed yet reaches AWS. Zip the tracked and untracked-but-not-ignored
files with their unix mode bits (`ruff`'s `EXE001` reads them), upload it, and
pass the object version, without which CodeBuild looks for a version called
`master`:

```bash
aws s3 cp source.zip s3://marketingos-artifacts-<account>-prod/source/marketingos-source.zip
V=$(aws s3api head-object --bucket marketingos-artifacts-<account>-prod \
  --key source/marketingos-source.zip --query VersionId --output text)
aws codebuild start-build --project-name marketingos-build-api-prod \
  --source-type-override S3 \
  --source-location-override marketingos-artifacts-<account>-prod/source/marketingos-source.zip \
  --source-version "$V"
```

### The worker — optional, and the one thing here that is not serverless

A Fargate container with the `claude` and `codex` CLIs, for billing campaign
runs to a subscription rather than an API key. Not deployed. `backend/Dockerfile`
builds its image and `worker.yaml` runs it; see the comments in both.

---

## Tearing it down

Reverse order. Some things survive on purpose, and a delete that appears to
succeed will leave them: the Aurora cluster (`DeletionPolicy: Snapshot`), the
SSM parameters (`parameters.sh` made them, not a stack), and the S3 buckets
with their contents.

That is deliberate for `password-pepper` above all — it is folded into every
bcrypt hash in the database, so deleting it makes every password in every
account permanently unverifiable. A stack delete must not be able to do that by
accident.
