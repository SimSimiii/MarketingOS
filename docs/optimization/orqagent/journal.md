# orqAgent campaign optimization journal

## 2026-09-16 — initial setup

- Case: existing campaign `263108f8db044003b3bf2ce5c4089439`, brand
  `78013376199f464f962a44702513e895`, audience "Ops or IT generalist
  standing up an internal Slack answer-bot over company docs". This campaign
  has an existing maximum preset and branded HTML setting. Its exact request
  and full context will be captured by `inspect` before a new generation.
- Session limit: two real generations, one correction cycle, at most 2700
  seconds per wait. Each generation uses its saved policy token and duration
  limits. No extra billed judge or bench call. Transport retries are included.
- The working tree was already modified across backend prompts, tests and
  frontend files when this session began. Those changes are preexisting and
  remain uncommitted. Baseline generation therefore measures that working tree.
- Review grid: `.agents/skills/campaign-optimization/SKILL.md`. Do not change it to improve a
  score. Record evidence from assets, role traces and source material.
- Resume: read `state.json`. If an entry has no `result_dir`, restart the local
  backend and run `backend/.venv/Scripts/python.exe scripts/optimize_campaign.py
  resume`. Then inspect its `runs/<execution_id>/` files. Never regenerate it
  solely because the previous Codex turn ended.

## Baseline: 42230750-28b9-4c96-b8c2-614d14a36ed2

- Real completed generation, 2026-09-16 20:05–20:10 UTC; one email, estimated
  $4.074, 472,926 input tokens and 88,602 output tokens. Snapshot:
  `runs/42230750-28b9-4c96-b8c2-614d14a36ed2/`.
- The email accurately introduces orqAgent as an agent over documents with a
  Slack connection, and gives a concrete test CTA. HTML was produced (7,431
  characters). The recorded panel understood the offer, but its simulated
  click estimate is not a commercial outcome.
- Clear contract breach: the brief's `must_not_say` prohibits credit counts
  because published pricing tables disagree. The delivered email says
  "$0 to start — 1,500 free credits, no card required." The writer prompt
  contained "1,500 free credits" as a supposedly generic specificity example.
  The evidence gate licensed the figure from the broader corpus, which cannot
  enforce the brief's narrower claim boundary.
- Audience assumption: the brief forbids claiming the reader has no tooling
  owner, but its objection is "Nobody here owns internal tooling". The
  delivered email says "If nobody at your company owns internal tooling".
  This is conditional, but spends space on a premise the selected reader's
  documented situation does not establish. A reader panel called it a mismatch.
- Hypothesis before correction: remove the prompt's numerical example, require
  the writer to check forbidden details even when they occur elsewhere in the
  prompt, and require the strategist to reconcile objections with prohibitions.
  Expected observable result: a new email has no credit count or assumed team
  history, retains a specific Slack/doc mechanism and clear CTA.
- Correction: `backend/prompts/writer.md` and `backend/prompts/strategist.md`.
  No new role or model call; local prompt change is sufficient because the
  defect is contradictory instructions and contamination, not a missing
  orchestration phase.

## Retest: 09656c17-c783-47d0-9587-ff95a6da80de

- Real completed generation, 2026-09-16 20:12–20:18 UTC; one email, estimated
  $3.9866, 9 role calls, 321.8 seconds. Snapshot:
  `runs/09656c17-c783-47d0-9587-ff95a6da80de/`. The baseline had 9 calls,
  292.8 seconds. Combined estimated cost: $8.0606. These are app estimates,
  not subscription invoices.
- The prohibited "1,500 free credits" line disappeared. The retest says
  "Start for free" and "no credit card is required", which the baseline
  brief allowed. Both emails introduce orqAgent and have a CTA to the brand
  site. Both HTML assets are complete documents with the same site link.
- A new audience error prevents claiming overall improvement: "who owns it
  in March, when whoever built it has moved on" imagines a future departure
  and a build that may not exist. The email also spends a paragraph on P95,
  token usage and spend trends, widening a Slack/doc argument. The baseline
  instead assumed "nobody at your company owns internal tooling". Reader
  reports on both runs marked the situation broadly relevant but called out
  these unsupported details. Both delivered reports say pull 7, understood
  and relevant; those model estimates do not settle the comparison.
- The strategist generated a different brief on retest, so removal of the
  credit count is observed, but cannot be attributed solely to prompt edits.
  No second scenario fit the two-generation limit. The budget stops the loop
  here; the correction remains a plausible guardrail, not a proven overall
  quality gain. No local modifications from before this session were reverted
  or committed.
- Verification: Ruff clean; 40 targeted tests passed; full backend suite
  1,243 passed with two dependency deprecation warnings. The new runner's
  `inspect`, `run` and `compare` actions executed against the real local API.
  `resume` uses the same persisted execution ID but was not exercised after
  an actual interruption.

## Next cycle

Inspect the saved briefs and reader reports first. Test the hypothesis that
the strategist's forced objection framing and the writer's "answer the no"
instruction create unsupported recipient histories. Preserve a concrete
objection, but express it without asserting a build, abandoned owner or future
employee departure. Record the expected textual change before editing.
Only then deliberately raise the total `--max-runs` above 2 in the case
command and journal, run a new generation, and compare with both saved emails.
For example, after recording a new two-run allowance, start the backend as
the skill describes and run:
`backend/.venv/Scripts/python.exe scripts/optimize_campaign.py run --case docs/optimization/orqagent/case.json --max-runs 4`.
If the Slack/doc scenario still cannot establish a supported buyer concern,
choose a second audience from `audience.json` and create a new case with its
own fixed brief. Do not rerun either completed execution.
