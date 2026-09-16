---
name: campaign-optimization
description: Operate MarketingOS campaigns and autonomously improve their generated quality from saved real runs, with bounded model spending and persistent case state.
---

# Campaign optimization operator

Load only the relevant `docs/optimization/<case>/state.json`, `journal.md` and
`case.json` after this skill. The case directory holds immutable run snapshots.
Do not reread implementation files unless an interface fails or a diagnosis
requires it. The AI chooses the audience, scenario, defect, correction and stop
point; the script only performs reliable API operations and capture.

## Setup

From the repository root, start the backend in a separate terminal:

```powershell
cd backend
.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The virtual environment, `backend/.env`, local SQLite database, and the
configured provider's CLI subscription login are prerequisites. API base is
`http://127.0.0.1:8000/api`. If auth is enabled, set `MARKETINGOS_TOKEN` in the
process environment; never save the token. Use `Authorization: Bearer <token>`.
All paths below are under `/api`. Check `GET /health` for `{"status":"ok"}`.

## Operational interfaces

| Operation | Request | Key response |
| --- | --- | --- |
| Find brand | `GET /brands` | array of `id`, `name`, `website_url` |
| Brand knowledge | `GET /brands/{brand_id}/knowledge` | `artifacts`, `evidence_count`, `gaps`, `version` |
| Audiences | `GET /market/{brand_id}/audience` | `map.segments`, `research`, `relevance` |
| Existing campaigns | `GET /campaigns?brand_id={brand_id}` | array of `id`, `request`, `audience_segment`, `policy`, `model_overrides` |
| Create brief/campaign | `POST /campaigns` JSON `name`, `request` (at least 10 chars), `brand_id`, optional `audience_segment`, `policy_preset`, `email_tier`, `model_overrides`, `sender_name`, `sender_role`, `cta_url` | `CampaignRead` with `id` |
| Cost and call forecast | `GET /campaigns/{id}/forecast` | `low`, `high` calls, `knowledge_reused`, observed estimated cost per email |
| Readiness | `GET /campaigns/{id}/generation-advice` | `can_generate`, `override_required`, `reasons` |
| Launch | `POST /campaigns/{id}/start` JSON `{}` (or `{"generate_anyway":true}` only with a recorded reason) | HTTP 202, execution `id`, `status` |
| Poll | `GET /executions/{id}/status` | `status`, `error_message`, `agent_executions`, `assets`, `estimated_cost_usd` |
| Deliverables and traces | `GET /executions/{id}/result`; `/assets`; `/logs?include_debug=true`; `/timeline` | `result.report`, text/HTML assets, role inputs/outputs, errors, durations, tokens and estimated costs, events |
| Cancel | `POST /executions/{id}/cancel` | HTTP 202, `{"status":"cancelling"}`; poll until terminal |

Use the case runner for durable launch and collection:

```powershell
backend/.venv/Scripts/python.exe scripts/optimize_campaign.py inspect --case docs/optimization/orqagent/case.json
backend/.venv/Scripts/python.exe scripts/optimize_campaign.py run --case docs/optimization/orqagent/case.json --max-runs 2
backend/.venv/Scripts/python.exe scripts/optimize_campaign.py resume --case docs/optimization/orqagent/case.json
backend/.venv/Scripts/python.exe scripts/optimize_campaign.py compare --case docs/optimization/orqagent/case.json --before <execution-id> --after <execution-id>
```

`case.json` needs `brand_id` and `campaign_id`; a new case can reuse the script.
`inspect` snapshots brand, knowledge, audience, campaign and forecast. `run`
records the execution ID immediately in `state.json`, polls to a terminal state,
then saves `runs/<execution_id>/{campaign,forecast,result,logs,timeline}.json`.
`resume` collects an interrupted run without buying another. Missing snapshot
responses appear as `.error.json`. Defaults: 2700-second wait, 10-second polls,
two total generations; flags configure all three. A timeout requests cooperative
cancellation. If the server died, restart it first; startup marks orphaned runs
failed. Never start another run while an entry lacks `result_dir`.
`compare` reads saved results only and writes a side-by-side JSON with the actual
assets, report, call count, time and estimated cost; the AI evaluates the claims.

Known failures: connection refused means start the backend; HTTP 401 means
provide a fresh `MARKETINGOS_TOKEN` when auth is enabled; campaign HTTP 422
usually identifies an invalid audience, model override or target in its
`detail`; a provider CLI/auth error appears in execution `error_message` and
logs, so repair that login before spending another generation. An HTTP 409 on
start means inspect the already-running execution rather than retrying blind.
CLI model names in overrides are catalog slugs, not tiers. Do not place API
keys in `.env` to fix subscription CLI errors.

For direct API operations beyond the runner, use `Invoke-RestMethod` with the
method and JSON body in the table. Keep a newly chosen case's input JSON in its
case directory before launch. Compare runs using the saved `result.json` assets,
brief, report, role traces and HTML, with the same case inputs. The free
deterministic quality evaluator is `backend/.venv/Scripts/python.exe -m
app.evaluation.runner --compare <before-dir> <after-dir>` from `backend/` when
those directories are runner evaluation outputs. Do not present its simulated
open or click estimates as customer measurements. Billed evaluation commands
need a separate explicit call budget; check `--dry-run` first.

## Decision and safety loop

Set a stable grid before the first correction: factual support, audience fit,
offer/benefit/action clarity, argument specificity, subject/body/CTA continuity,
unsupported promises or repetition, HTML rendering, status/duration/cost. Mark
missing source facts separately from generator defects. Quote before/after
assets and cite saved evidence IDs; model scores alone do not prove improvement.
Record cause, hypothesis and expected observable change in `journal.md` before
editing. Change the generator, run targeted tests plus required lint/test checks,
then regenerate on unchanged inputs. Consider a second scenario when budget
permits. Update `state.json` with conclusions and next action. Stop on confirmed
improvement, exhausted generation limit, two unsuccessful cycles, or a genuine
external blocker. Preserve the exact resume action.

Real runs spend subscription quota. Count failed runs, internal retries and
reader/judge calls in the generation limit. Observe policy duration and token
caps. `estimated_cost_usd` is an estimate, not a billing guarantee. Generate
drafts only: no sending, production deployment or secret exposure. Keep changes
on the current branch and preserve unrelated local work.
