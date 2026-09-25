# Infrastructure as code

Everything AWS holds for MarketingOS, as CloudFormation. Four templates here,
four SAM templates beside the code they deploy, and one ordered runbook below.

| Template | Creates | Deployed |
|---|---|---|
| [`secrets.yaml`](secrets.yaml) | Eight Secrets Manager secrets, five of them generated | once, first |
| [`database.yaml`](database.yaml) | VPC, two private subnets, two security groups, RDS Postgres | once, by hand |
| [`pipeline.yaml`](pipeline.yaml) | Five CodeBuild projects, two IAM roles, ECR, artifact bucket | once, then updated |
| [`edge.yaml`](edge.yaml) | Three WAF web ACLs and three CloudFront **Free plan** subscriptions — **us-east-1** | twice: ACLs first, plans once the distributions exist |
| [`worker.yaml`](worker.yaml) | ECS Fargate service, ALB, public subnets — **optional** | only for subscription billing |

The application stacks are not here, deliberately: a SAM template belongs next
to the code it packages, because `CodeUri: ./` is relative to it.
`backend/template.yaml`, `frontend/template.yaml`,
`administration/backend/template.yaml` and `landing-page/template.yaml` are
deployed by the CodeBuild projects `pipeline.yaml` creates.

> **On the filename.** SAM looks for `template.yaml` or `template.yml` and has
> done since it shipped; `sam.yml` is not a name it reads. The four templates
> above already exist under the name the tooling expects, so nothing here
> renames them.

---

## What each service is for, and what it costs

Monthly, eu-west-3, at the traffic this product currently has — which is none.

### Deployed by default

| Service | Why it is there | Idle cost |
|---|---|---|
| **RDS Postgres** `db.t4g.micro`, 20 GB gp3 | The only durable state. Every table hangs off `Brand` or `Campaign`; multi-tenancy is `owner_id` on those two. | ~$15 |
| **Secrets Manager** × 8 | `JWT_SECRET`, `PASSWORD_PEPPER`, the two admin secrets, the DB password, `DATABASE_URL`, and the two vendor API keys. | ~$3.20 |
| **Lambda** (`api`, `migrate`, `console`, `plan`, `craft`, `finish`) | Scales to zero. The API is arm64 and ~1 GB; the console is an x86 container image; the three campaign steps are 2 GB and 900s. | ~$0 |
| **API Gateway** (HTTP API) × 2 | $1.00 per million requests. HTTP, not REST — nothing needs usage plans, because auth is a bearer token the app verifies itself. | ~$0 |
| **CloudFront** × 3 | Console, back-office, landing page. Flat-rate **Free plan**, WAF included. `PriceClass_All` - the plans refuse `_100`. | $0 |
| **S3** × 3 | Back-office export, landing page, build artifacts. All private, all read through an OAC. | <$1 |
| **ECR** | The console image, last 10 retained by lifecycle policy. | ~$1 |
| **Step Functions** | Drives the campaign loop. Standard workflows are $25 per million transitions; a five-email run is about nine. | ~$0 |
| **CodeBuild** | Billed per build-minute; nothing runs between pushes. | ~$1 |
| **CloudWatch Logs** | Retention is set on every group. An unbounded group is the cost nobody notices. | ~$1 |

**≈ $22/month**, almost all of it RDS.

### Not deployed, and why

- **NAT Gateway** — $32/month before a byte moves. Nothing in the Lambda
  stacks calls the open web: `app/market/` does, and market work cannot run on
  Lambda anyway. The worker reaches the internet from a public subnet instead.
- **ElastiCache / Redis** — the SSE broker and `ExecutionRegistry` are
  in-memory and process-local. Correct for one worker, and the first thing a
  second one would need.
- **SQS** — there is no durable job handoff yet. See the worker section.
- **RDS Multi-AZ** — doubles the bill for a standby. Worth it when losing an
  afternoon costs more than that.
- **WAF on the APIs** — the three distributions carry one each (a per-IP rate
  limit, from `edge.yaml`, paid for by the Free plan). The two HTTP APIs are
  reached directly, so API Gateway's per-stage throttles are what they have.
- **A paid CloudFront bill** — the three distributions sit on the flat-rate
  **Free plan** (`edge.yaml`), which also covers their WAF. Three is the
  account's hard ceiling on Free plans; a fourth distribution is
  pay-as-you-go. Each subscribed distribution needs a web ACL of its own, and
  that ACL can't be removed afterwards without leaving the plan.

Domains: `pipeline.yaml`, `frontend/template.yaml`,
`administration/backend/template.yaml` and `landing-page/template.yaml` all
take a domain, a us-east-1 ACM certificate and a Route 53 zone id, and write
their own alias records when given all three. The APIs stay on their
`execute-api` URLs.

### If the worker is deployed

| Service | Idle cost |
|---|---|
| Fargate, 0.5 vCPU / 1 GB, arm64, always on | ~$13 |
| Application Load Balancer | ~$17 |
| Public IPv4 on the task | ~$4 |

**+ ≈ $34/month.** Only needed to bill a subscription instead of a card — the campaign state machine runs every preset on Lambda without it.

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

Ordered, because each step consumes the previous one's outputs. `REGION` and
`ENV` are yours; the examples use `eu-west-3` and `prod`.

```bash
export AWS_DEFAULT_REGION=eu-west-3 ENV=prod
```

### 0. What is live today (prod, eu-west-3)

| | |
|---|---|
| Landing | https://orqagent.com |
| Console | https://app.orqagent.com |
| Back-office | https://admin.orqagent.com |
| Platform API | `ApiEndpoint` of `marketingos-api-prod` (+ `/api`) |
| Stacks | `marketingos-{secrets,data,pipeline,api,console,admin,landing}-prod` in eu-west-3, `marketingos-edge-prod` in us-east-1 |

`ALLOW_PUBLIC_SIGNUP` is **on** (`AllowPublicSignup=true` on the pipeline
stack) so the first account can be made from `/register`; turn it off and
rebuild the API once it exists.

**Building from a working tree instead of GitHub.** Every project also builds
from a zip in the artifact bucket, which is how a change that is not pushed yet
reaches AWS. Zip the tracked and untracked-but-not-ignored files (keep the unix
mode bits: `ruff`'s `EXE001` reads them), upload it, and pass the object
version:

```bash
aws s3 cp source.zip s3://marketingos-artifacts-<account>-prod/source/marketingos-source.zip
V=$(aws s3api head-object --bucket marketingos-artifacts-<account>-prod \
  --key source/marketingos-source.zip --query VersionId --output text)
aws codebuild start-build --project-name marketingos-build-api-prod \
  --source-type-override S3 \
  --source-location-override marketingos-artifacts-<account>-prod/source/marketingos-source.zip \
  --source-version "$V"
```

Without `--source-version` CodeBuild looks for an object version called
`master` and fails in `DOWNLOAD_SOURCE`.

**On Windows**, two things about the CLI: set `AWS_CLI_FILE_ENCODING=UTF-8`
before any `file://` template (they contain box-drawing characters the default
code page cannot decode), and `MSYS_NO_PATHCONV=1` in Git Bash, which otherwise
rewrites `/aws/codebuild/...` and `/prod` into Windows paths.

### 1. Secrets

```bash
aws cloudformation deploy \
  --template-file iac/secrets.yaml \
  --stack-name "marketingos-secrets-$ENV" \
  --parameter-overrides "Environment=$ENV"
```

Five values are generated and never printed. `DATABASE_URL` is a placeholder
until step 2 fills it.

### 2. Database and network

The password is passed as a dynamic reference, so it never transits a shell or
a shell history:

```bash
aws cloudformation deploy \
  --template-file iac/database.yaml \
  --stack-name "marketingos-data-$ENV" \
  --parameter-overrides "Environment=$ENV" \
      "DBPassword={{resolve:secretsmanager:marketingos/$ENV/db-password:SecretString}}" \
  --capabilities CAPABILITY_IAM
```

Ten to fifteen minutes. Then write the URL that other stacks read:

```bash
ENDPOINT=$(aws cloudformation describe-stacks --stack-name "marketingos-data-$ENV" \
  --query "Stacks[0].Outputs[?OutputKey=='DatabaseEndpoint'].OutputValue" --output text)
PASSWORD=$(aws secretsmanager get-secret-value --secret-id "marketingos/$ENV/db-password" \
  --query SecretString --output text)
aws secretsmanager put-secret-value --secret-id "marketingos/$ENV/database-url" \
  --secret-string "postgresql+psycopg://marketingos:$PASSWORD@$ENDPOINT:5432/marketingos"
```

Keep the subnets and security group; the next step wants them:

```bash
aws cloudformation describe-stacks --stack-name "marketingos-data-$ENV" \
  --query "Stacks[0].Outputs" --output table
```

### 3. Authorise CodeBuild against GitHub

Once per account and region, and not something a template can express — it is
an OAuth grant:

```bash
aws codebuild import-source-credentials \
  --server-type GITHUB --auth-type PERSONAL_ACCESS_TOKEN \
  --token "$GITHUB_TOKEN"
```

A fine-grained token needs *Contents: read* and *Webhooks: read and write* on
this repository. Without the webhook scope the projects still build on demand;
they just cannot be triggered by a push.

### 3b. Web ACLs for the CloudFront Free plan

```bash
aws cloudformation deploy --region us-east-1 \
  --template-file iac/edge.yaml \
  --stack-name "marketingos-edge-$ENV" \
  --parameter-overrides "Environment=$ENV"
```

Three ACLs, one per distribution. Their ARNs go to the pipeline stack
(`ConsoleWebAclArn`, `AdminWebAclArn`) and to the landing stack
(`WebAclArn`). The subscriptions come in step 9b, once the distributions exist.

### 4. The five CodeBuild projects

```bash
aws cloudformation deploy \
  --template-file iac/pipeline.yaml \
  --stack-name "marketingos-pipeline-$ENV" \
  --parameter-overrides \
      "Environment=$ENV" \
      "GitHubRepositoryUrl=https://github.com/<owner>/MarketingOS" \
      "SourceBranch=master" \
      "VpcSubnetIds=subnet-aaa,subnet-bbb" \
      "VpcSecurityGroups=sg-aaa" \
  --capabilities CAPABILITY_NAMED_IAM
```

Webhooks are **off** by default. Turn them on with
`EnableWebhooks=true` once each project has gone green by hand — a webhook
enabled before the variables are right means the next push deploys a
half-configured stack.

### 5. Platform API

```bash
aws codebuild start-build --project-name "marketingos-build-api-$ENV"
```

Lints, runs the full suite (~1,170 tests, no model quota), deploys, then
invokes the migrator and fails the build if the migration fails. Take
`ApiEndpoint` and **append `/api`**:

```bash
aws cloudformation describe-stacks --stack-name "marketingos-api-$ENV" \
  --query "Stacks[0].Outputs[?OutputKey=='ApiEndpoint'].OutputValue" --output text
```

### 6. Console

Feed the API URL back in, then build:

```bash
aws cloudformation deploy \
  --template-file iac/pipeline.yaml \
  --stack-name "marketingos-pipeline-$ENV" \
  --parameter-overrides "Environment=$ENV" \
      "GitHubRepositoryUrl=https://github.com/<owner>/MarketingOS" \
      "ApiUrl=https://xxxx.execute-api.$AWS_DEFAULT_REGION.amazonaws.com/$ENV/api" \
  --capabilities CAPABILITY_NAMED_IAM

aws codebuild start-build --project-name "marketingos-build-console-$ENV"
```

`NEXT_PUBLIC_API_URL` is inlined into the client bundle at **image build
time**, so changing it later means another build, not a stack update.

Then put the console's URL into `CorsOrigins` and rebuild the API — the
browser refuses every call until that lands.

### 7. Back-office

Two builds, and the first one twice. `ADMIN_CORS_ORIGINS` has to name a
CloudFront domain that does not exist until the stack is created:

```bash
aws codebuild start-build --project-name "marketingos-build-admin-api-$ENV"
# read AdminConsoleUrl, set AdminCorsOrigins on the pipeline stack, then:
aws codebuild start-build --project-name "marketingos-build-admin-api-$ENV"
aws codebuild start-build --project-name "marketingos-build-admin-ui-$ENV"
```

The first operator has to be created from inside the VPC or through a tunnel,
with the same `ADMIN_PWD_PEPPER` the Lambda has — see
[docs/deployment.md](../docs/deployment.md).

### 8. Landing page

```bash
aws cloudformation deploy \
  --template-file landing-page/template.yaml \
  --stack-name "marketingos-landing-$ENV" \
  --parameter-overrides "Environment=$ENV"
```

Then set `LandingBucket`, `LandingDistributionId` and `ConsoleAppUrl` (no
trailing slash — the build fails on one) on the pipeline stack and:

```bash
aws codebuild start-build --project-name "marketingos-build-landing-$ENV"
```

### 9b. Subscribe the three distributions to the Free plan

```bash
aws cloudformation deploy --region us-east-1 \
  --template-file iac/edge.yaml \
  --stack-name "marketingos-edge-$ENV" \
  --parameter-overrides "Environment=$ENV" \
      ConsoleDistributionId=E... AdminDistributionId=E... LandingDistributionId=E...
```

Three is the account's ceiling on Free plans; one already held elsewhere has to
be cancelled first. A distribution restricted to `PriceClass_100` is refused
as "not eligible for this subscription tier".

### 9c. The first back-office operator

The database is not reachable from outside the VPC, so the bootstrap script is
also a function with no HTTP route:

```bash
aws lambda invoke --function-name "marketingos-admin-bootstrap-$ENV" \
  --cli-binary-format raw-in-base64-out \
  --payload '{"email": "you@example.com", "password": "at-least-12-characters"}' out.json
cat out.json
```

`"reset_password": true` in the payload resets an existing operator instead.

### 9. The worker — optional

Build and push the image. There is no CodeBuild project for it, because five
was the number asked for; adding a sixth is a copy of `ConsoleBuild` in
`pipeline.yaml` with `backend/Dockerfile` as its source.

```bash
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
REPO="$ACCOUNT.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/marketingos-worker-$ENV"

aws ecr create-repository --repository-name "marketingos-worker-$ENV"
aws ecr get-login-password | docker login --username AWS --password-stdin "${REPO%%/*}"

docker build --platform linux/arm64 -t "$REPO:latest" backend/
docker push "$REPO:latest"
```

`--platform linux/arm64` matters: `worker.yaml` asks Fargate for ARM64, and an
x86 image against it fails at task start with an exec-format error rather than
at build.

```bash
aws cloudformation deploy \
  --template-file iac/worker.yaml \
  --stack-name "marketingos-worker-$ENV" \
  --parameter-overrides "Environment=$ENV" \
      "VpcId=vpc-xxx" "DatabaseSecurityGroupId=sg-xxx" \
      "ImageUri=$REPO:latest" \
      "CorsOrigins=https://<console domain>" \
  --capabilities CAPABILITY_NAMED_IAM
```

Then sign the two CLIs in, as described above, and repoint the console's
`ApiUrl` at `WorkerUrl` + `/api`.

---

## Tearing it down

Reverse order. Three things survive on purpose, and a delete that appears to
succeed will leave them: the RDS instance (`DeletionPolicy: Snapshot`), the six
secrets, and both S3 buckets with their contents.

That is deliberate for `PASSWORD_PEPPER` above all — it is folded into every
bcrypt hash in the database, so deleting it makes every password in every
account permanently unverifiable. A stack delete must not be able to do that by
accident.
