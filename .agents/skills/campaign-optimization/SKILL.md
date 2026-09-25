---
name: campaign-optimization
description: Autonomously improve MarketingOS from real campaign runs until its generated emails meet a sellable-result bar, using subscription quota and persistent case state.
---

# Campaign optimization operator

Load only the relevant `docs/optimization/<case>/state.json`, `journal.md` and
`case.json` after this skill. The case directory holds immutable run snapshots.
Do not reread implementation files unless an interface fails or a diagnosis
requires it. The AI chooses the audience, scenario, defect, correction and stop
point; the script only performs reliable API operations and capture.

## Setup

Invoking this skill authorizes generator changes, tests and real draft generations
using the configured subscription quota until the sellable-result bar below is met.
There is no default total generation limit or unsuccessful-cycle limit. Continue
without asking for renewed permission between cycles. Honor any explicit user cap.
Older case limits and cycle-stop flags are historical when superseded by this
authorization; record the reopened state before continuing.

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
backend/.venv/Scripts/python.exe scripts/optimize_campaign.py run --case docs/optimization/orqagent/case.json
backend/.venv/Scripts/python.exe scripts/optimize_campaign.py resume --case docs/optimization/orqagent/case.json
backend/.venv/Scripts/python.exe scripts/optimize_campaign.py compare --case docs/optimization/orqagent/case.json --before <execution-id> --after <execution-id>
```

`case.json` needs `brand_id` and `campaign_id`; a new case can reuse the script.
`inspect` snapshots brand, knowledge, audience, campaign and forecast. `run`
records the execution ID immediately in `state.json`, polls to a terminal state,
then saves `runs/<execution_id>/{campaign,forecast,result,logs,timeline}.json`.
`resume` collects an interrupted run without buying another. Missing snapshot
responses appear as `.error.json`. Defaults: 2700-second wait, 10-second polls,
no total generation cap; flags configure polling, timeout and an optional user cap.
Each invocation launches only one generation, allowing diagnosis before the next.
A timeout requests cooperative
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
open or click estimates as customer measurements. Use billed evaluation when it
answers a concrete unresolved quality question; check `--dry-run` first and record
why its quota cost is useful. Do not rerun unchanged failures blindly.

## Decision and safety loop

Set a stable grid before the first correction: factual support, audience fit,
offer/benefit/action clarity, argument specificity, subject/body/CTA continuity,
unsupported promises or repetition, HTML rendering, status/duration/cost. Mark
missing source facts separately from generator defects. Quote before/after
assets and cite saved evidence IDs; model scores alone do not prove improvement.

### Iteration quality note

At the end of **every completed iteration** — diagnosis, correction, targeted
tests and required validation checks, followed by a regenerated run when one is
needed to assess the change — append a short, reader-friendly quality note to
`journal.md` and update the matching summary in `state.json`. This is a progress
report, not a substitute for the sellable-result verdict.

Use a 0–100 internal product-quality score for the generated deliverable. Score
the same stable grid on every iteration: factual support (25), audience and offer
clarity (20), specificity and persuasive argument (20), subject/body/CTA
continuity (15), polish and rendering (10), and absence of unsupported promises
or repetition (10). State the score as an informed review judgment, not a model
measurement or customer outcome. Do not invent a score if a generation did not
complete; instead record `not scored` and why.

Keep the note compact (roughly 3–6 lines) and include: iteration number; current
score and change versus the previous scored iteration; the best score so far and
which iteration/run achieved it; 1–2 concrete strengths; the most important
remaining defect; tests/run evidence; and the next action or the final
sellable-result verdict. Preserve score history so the "best so far" figure is
the maximum among all comparable completed iterations in the case, not merely
the previous run. If inputs, audience, or evaluation conditions changed, label
the score non-comparable and start a separately labelled comparison track.

Suggested durable `state.json` shape (add fields without discarding existing
case state): `quality_history` entries with `iteration`, `execution_id`,
`score`, `comparable`, `strengths`, `remaining_defect`, `evidence`, and
`next_action`; plus `quality_best` with the best comparable `score`,
`iteration`, and `execution_id`. Recompute `quality_best` after every scored
iteration. A passing test suite assesses the implementation only; it must never
raise the product-quality score without inspection of the resulting assets.

Judge the actual delivered email(s) against a sellable-result bar: a reasonable
buyer in the target market could use the copy after ordinary brand review and
minor personalization, and could plausibly find the result worth paying for.
This requires supported claims, clear audience and offer, a specific and
persuasive reason to act, a coherent subject/body/CTA, and polished copy and
rendering without material defects. Base the judgment on the saved assets and
source evidence, not a model score or an untested claim about actual customer
willingness to pay. Record the concrete strengths and remaining defects in
`journal.md` and the verdict in `state.json`.
Record cause, hypothesis and expected observable change in `journal.md` before
editing. Change the generator, run targeted tests plus required lint/test checks,
then regenerate on unchanged inputs. Validate the project on another relevant
audience or campaign scenario before claiming general sellability; one good email
only establishes that case. Update `state.json` with
conclusions and next action. Stop successfully as soon as the delivered email(s)
meet the sellable-result bar; do not buy more runs or keep polishing for marginal
scores once the reviewed cases support the intended product scope. Unsuccessful
cycles require a revised diagnosis, implementation or scenario, not automatic
termination. Continue autonomously until success, user interruption, an explicit
user budget, or a genuine external blocker such as unavailable quota or login.
Repair local failures autonomously. Record external blockers as incomplete with
the exact resume action. Never claim actual willingness to pay without real buyer
evidence: the operational target is supported, persuasive, usable paid-quality copy.

Real runs spend subscription quota. Track failed runs, internal retries and
reader/judge calls as well as successful generations. Observe per-run duration and token
caps. `estimated_cost_usd` is an estimate, not a billing guarantee. Generate
drafts only: no sending, production deployment or secret exposure. Keep changes
on the current branch and preserve unrelated local work.
