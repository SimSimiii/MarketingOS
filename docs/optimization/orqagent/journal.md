# orqAgent campaign optimization journal

## 2026-09-19 — verdict du périmètre testé

- Le second scénario est validé dans `docs/optimization/orqagent-support` : deux
  emails français livrés, note interne 87/100 sur la piste OpenAI, HTML contrôlé
  sur bureau et 390 px. La piste Claude reste à 70/100, son retest ayant été
  interrompu par la limite de session avant tout livrable.
- Avec le cas Slack/Notion 1521ac36 déjà validé sur les modèles par défaut, les
  deux scénarios prévus atteignent le seuil vendable après revue de marque ordinaire.
  Arrêt conforme au skill : aucune génération supplémentaire pour du polissage marginal.

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

## 2026-09-17 — renewed allowance and hypothesis before correction

- User explicitly authorized up to two additional real generations; total case cap
  is now four. Failed runs count; no separate billed bench or judge evaluation.
  Keep the existing campaign, audience, sources and policy unchanged.
- Diagnosis from retest 09656c17: the brief's `why_it_fails` says nobody owns
  internal tooling after the build, while its reader only considers a build.
  The delivered copy invents a March departure. General audience cautions coexist
  with a stronger instruction to copy an objection word for word and answer it.
- Hypothesis: require a selected-audience applicability check before assigning
  objections, permit an empty objection, and remove the writer's unconditional
  requirement to answer one. A conditional does not rescue an irrelevant premise.
  Apply audience provenance checks to `why_it_fails` and subject strategy too.
- Expected observable change: no asserted build, staffing vacancy, employee departure,
  or invented deadline; a clear Slack/document product and concrete next action;
  no credit count or unsupported integration claim. Existing review grid unchanged.
  This adds no model calls. Run existing prompt/pipeline tests and full backend checks.
- Resume command after checks: backend/.venv/Scripts/python.exe
  scripts/optimize_campaign.py run --case docs/optimization/orqagent/case.json
  --max-runs 4. If a run is pending use `resume` instead.

## Retest: fcf62d03-4f63-47e6-a6e9-c2f4dd2213d1

- Completed on unchanged campaign fields, knowledge and audience snapshots (API values
  compared before launch). Readiness allowed generation without override. Third total
  generation; one of the renewed two-run allowance used. Eight recorded role executions,
  297.9 seconds, estimated $3.9202. Role records are not individual provider-call
  counts: the reader panels and candidate batches contain multiple internal calls.
- Validation before generation: 31 targeted tests passed; Ruff clean; full backend suite
  1,243 passed with the same two dependency warnings. Frontend unchanged.
- Factual support: no credit count or invented March departure. New useful line:
  "Upload your handbook documents, or sync Notion pages over OAuth" (E11, E94),
  followed by Slack OAuth and channel replies (E90). This addresses the old upload-only
  gap with existing source facts rather than inventing an integration. Product setup
  duration remains tied to the first agent, not company-wide deployment (E24).
- Audience fit: still unsuccessful. Old: "who owns it in March, when whoever built it
  has moved on." New: "Build a Slack bot over the handbook and you own it. Indefinitely."
  followed by "That is usually where the idea stops." No known departure is asserted,
  but an unestablished reason for not building is still central. The brief again selected
  "Nobody here owns internal tooling" despite its own prohibition. Reader feedback
  identifies that dread as plausible rather than confirmed.
- Offer/benefit/action clarity: product, Slack/document mechanism and free account CTA
  are understandable; all three saved readers understood it. Product appears after
  three problem paragraphs, so orientation is still delayed. P.S. repeats the task.
- Specificity and continuity: removal of the analytics paragraph keeps this closer to
  the handbook job. However the final subject "The same policy question, for the fourth
  time this week" invents a frequency and shifts away from the maintenance headline.
  This was introduced by the later subject-line pass, whose prompt has no explicit
  audience-history constraint. Saved simulated pull remains 7; no measured click gain.
- Source gaps: issue-tracker coverage and data handling remain unanswered; reader wishes
  are not permission to invent either. Notion support is present in E94 and is no longer
  a missing-fact issue. No customer proof has appeared.
- HTML: exported email.html beside result.json and inspected in the local browser.
  Readable desktop paragraphs, headline, CTA and footer; no visible overlap or clipping.
  This is browser rendering, not verification in email clients or mobile viewports.
  CTA points to the brand homepage, whereas the brief describes signup; unchanged link
  configuration limits how direct this step is.
- Capture repair: relative --case paths caused relative_to(ROOT) to fail after snapshots
  were saved. Resolve the supplied case path once after parsing. `resume` then collected
  the same completed ID successfully; no duplicate generation. Both compare commands
  passed, as did Ruff on the runner. Immutable source result/log/timeline files retained.
- Conclusion: local gains (Notion path, fewer tangents, removed departure) do not establish
  overall improvement. This is the second unsuccessful correction cycle including the
  previous session, so stop under the skill's two-cycle rule. Do not consume the fourth
  generation automatically. Prompt edits remain unproven guardrails, not a demonstrated win.
- Next diagnosis: inspect how objection_detail can expand a selected objection back to
  the generic audience-model entry, and how the final subject pass receives audience
  constraints. Address the source/propagation of premises rather than appending more
  general writing cautions. Existing captures permit this investigation without quota.
- Exact resume: no pending execution. Read state.json and this entry first. After an
  explicit decision to reopen optimization and a recorded new hypothesis/correction,
  the remaining already-authorized generation is launched with:
  backend/.venv/Scripts/python.exe scripts/optimize_campaign.py run --case
  docs/optimization/orqagent/case.json --max-runs 4. If interrupted, use `resume`.

## 2026-09-17 — quota-free follow-up diagnosis

- Resumed inspection only. The two-unsuccessful-cycle stop remains in force.
  No generation, provider call, generator edit or backend startup occurred.
- `backend/app/knowledge/artifacts.py:551` confirms a propagation risk:
  `objection_detail` matches word overlap against global audience objections and
  returns the whole matching entry, without selected-segment or prohibition context.
  `backend/app/marketing/writer.py:203` passes that expansion to the writer.
  This can restore a broader premise, but does not establish the latest failure's
  cause: its brief already selected the unsupported objection.
- `backend/app/marketing/subject_lines.py:189` confirms that subject generation
  receives body, incumbent subject/preview, idea, objection, strategy and voice,
  but no audience grounding or brief prohibitions. The subject prompt invites a
  reader moment or existing belief without the writer's audience-history constraint.
  The latest saved logs record the winning subject as "The same policy question,
  for the fourth time this week". Alternatives do pass an optional deterministic
  screen; this finding is missing context, not absence of all checks.
- Hypothesis for a deliberately reopened cycle: preserve the selected objection
  instead of replacing it with a generic entry, qualify supporting material by
  audience applicability, and pass audience grounding and prohibitions to subject
  generation. Expected result: no invented ownership history or question frequency,
  retaining the supported Slack/document mechanism. No extra model call is needed.
  First verify context propagation with scripted tests; a later real run is needed
  to establish copy-quality improvement.
- Verdict unchanged: incomplete; sellable-result bar not met. Remaining allowance
  and exact resume command above are unchanged. Do not auto-launch a generation or
  count this diagnosis as a successful correction cycle.

## 2026-09-17 — autonomous optimization explicitly reopened

- User removed artificial cycle and generation limits and authorized continuing code
  changes, tests and paid subscription generations until sellable output. Historical
  caps and stop flags are superseded; per-run resource limits remain operational.
- Before-edit hypothesis: generic objection expansion and missing subject context
  allow unsupported audience premises to survive. Preserve the brief-selected
  objection, distinguish supporting product evidence from recipient facts, and pass
  selected audience grounding plus prohibitions to subject generation.
- Expected observable change: no invented staffing history or frequency, clear
  Slack/document benefit and coherent subject/body/CTA. No new model calls per run.
- Verify with scripted context-boundary tests, full backend tests and Ruff, then
  regenerate the unchanged case. Review actual assets and sources; model scores
  alone cannot establish improvement. Validate another scenario before concluding
  project-level sellability. Actual buyer willingness remains unmeasured.

- Implemented context correction in objection expansion and subject generation. Also
  found an unconditional fourth candidate opening instruction requiring an objection;
  it now falls back to the documented capability when no concern is supported.
- Verification: skill validator passed; Ruff app/tests and runner passed; 1,245 backend
  tests passed (two existing dependency warnings), plus three runner tests added after
  collection. Runner tests verify unlimited default, explicit cap, and pending-run guard.
- Real retest launched: abd6d6ab-4532-4259-a7fb-5ebf6881207e. Same campaign fields;
  readiness permits generation without override, knowledge reused, forecast 13–54 calls.
  Backend launch config referenced by AGENTS.md is absent and no preview launcher is
  available; started the skill's uvicorn command as a hidden local process instead.

## Retest abd6d6ab — remaining defects and next correction

- Completed in 267.5 seconds, estimated $3.6985. Subject no longer invents a weekly
  count; no employee departure or ownerless-team assertion is delivered. The build
  comparison now describes work, rather than attributing an unconfirmed past build.
- Copy remains mediocre: headline "The Slack handbook bot is now a configuration"
  translates strategy into an abstract noun, and an Analytics/credits paragraph
  interrupts the handbook argument without helping the signup decision. Notion sync
  is absent again. The 1,500 credits are permitted by this run's brief (unlike the
  earlier baseline), so their return is not a breach of its must_not_say boundary;
  published plan inconsistencies still make plan-level promises risky.
- Concrete rendering defect: brief call_to_action explicitly includes the known offer
  URL https://app.orqagent.com/sign-up, but delivered HTML links the signup button to
  the brand homepage. Desktop browser rendering is otherwise readable.
- Before-edit hypothesis: the renderer only receives a campaign/brand fallback URL,
  ignoring a brief-selected licensed offer URL. Resolve a unique exact known offer
  URL from the planned action when no explicit campaign CTA overrides it. Keep the
  decision in marketing code, with no new model calls. Test unknown/ambiguous URLs
  and explicit overrides. Expected change: signup buttons point to signup.
- Also revise existing opening/headline instructions (rather than add another list):
  announcement candidates may open on the useful product action; headline output
  must describe what the reader can do, not turn strategy nouns into a slogan.
- Continue: not yet a sellable-result verdict. Run backend checks and another
  unchanged-input generation, then the prepared second scenario.

- CTA/opening correction checks: 1,255 backend tests passed; Ruff clean.
  Retest 3f4af5b3-dfc2-4788-a6df-6b6021b4fc55 launched on unchanged campaign inputs.

## 2026-09-18 — retest 3f4af5b3 and upstream contamination hypothesis

- Retest completed, estimated $3.7141, 290.5 seconds. Actual signup href is now
  https://app.orqagent.com/sign-up. Headline improved to "Put an answer-bot in
  Slack over your own handbook" and the opening explicitly announces orqAgent.
- Still incomplete: delivered text asserts "it has no owner" after imagining a
  company-wide production system. Readiness scores did not prevent this assumption.
- Inspected actual saved inputs: the discovery map says "no internal tools team",
  "abandoned attempt" and "nobody owns"; the relevance dossier also supplies an
  objection "Nobody here owns internal tooling" explicitly marked inferred with
  empty provenance. Both are rendered into strategy even when verified audience
  research is loaded. Merely editing writer cautions did not prevent their reuse.
- Before-edit hypothesis: when a researched audience has already been selected,
  omit the superseded discovery map and unrelated compiler personas from strategy,
  and omit unsourced objection proposals from both knowledge and dossier prompt
  blocks. Preserve product evidence, verified research, sourced objections, original
  saved artifacts, and the legacy fallback when no research exists. The planner
  can still reason about relevant concerns from the remaining facts.
- Expected change: no borrowed abandoned-build/ownerless-team premise; a useful
  Slack/document action grounded in the actual selected audience. No extra calls.
  Test prompt boundaries and immutability, then full checks and unchanged-input run.

- Upstream-context correction verification: 1,256 backend tests passed (two
  existing dependency warnings), Ruff and diff whitespace checks passed. Product
  knowledge artifacts equal the original saved snapshot. Real retest started:
  1521ac36-679b-408f-928e-46cd6bde0129.

## Retest 1521ac36 — case-level sellable-result verdict

- Completed in 253.3 seconds; estimated $3.5323; 34 recorded model calls started
  and finished. Same campaign/source inputs. Role execution counts are not model
  call counts; the comparison script's legacy agent_calls key counts role records.
- Factual support: Notion OAuth and page/database sync (E94), Slack OAuth and
  channel replies (E90), retrieval without a managed vector DB (E11), signup
  credits (E25), no card (E39). No unsupported customer proof, invented frequency,
  staffing vacancy or departure is asserted. Claim units remain within sources.
- Audience fit: a concrete optional configuration route for someone considering
  the documented Slack/handbook task. "Standing up ... reads like an integration
  project" evaluates the task; it no longer asserts a build was abandoned or has
  no owner. Reader inferences that this implies being mid-build are not assertions
  present in the actual text.
- Offer/action: "orqAgent is now available: a no-code platform for building AI
  agents" supplies orientation. "one agent and two connections" is then explained
  with the two licensed integrations. The test asks for one policy question and
  makes company-wide adoption a later decision, not a promised rollout result.
- Specificity/continuity: the subject's recurring handbook question, Notion/Slack
  mechanism, and test CTA form one argument. Analytics and ownership digressions
  are absent. The P.S. adds trial mechanics rather than repeating the test.
- HTML: inspected the actual delivered export on desktop and at a 390px viewport,
  including the bottom CTA/footer. Readable, no overlap or horizontal overflow
  (DOM content width equals client width). Actual button href is the licensed
  https://app.orqagent.com/sign-up. This is browser QA, not an email-client matrix.
- Remaining source gaps: production reliability evidence, security review material
  and issue-tracker support remain incomplete; the email does not invent them.
  These are adoption questions beyond the small evaluation it proposes. No real
  opens, clicks, purchases or willingness-to-pay observations exist.
- Verdict: meets the fixed case-level sellable-result bar after normal brand review
  and personalization. This is a qualitative asset judgment, not derived from
  simulated pull. Do not buy marginal polishing runs. French two-email support
  validation is now running as 1283bf9c-517a-4228-9084-d6751a9244c6.
