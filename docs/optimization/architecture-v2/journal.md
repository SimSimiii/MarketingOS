# Architecture v2 — 17 October 2026

## Diagnosis before implementation

Confirmed defects: structured evidence scope lost in dossier input/snapshots; shared sender name counted as eight testimonial attributions; intent exists only in generated request text; rejected problem can force first-feature/documentation fallback; literal problem matching can discard paraphrases; repeated full evidence representations consume context.

Hypothesis: persistent user intent, explicit proposition references, scope-preserving evidence contracts and decision-selected context will improve fidelity and specificity. Repair must preserve campaign objective and route to the defective level. Existing bounded recovery and independent cold reading remain useful.

Baseline source archive is immutable and hashed in state.json. No new generated deliverable is scored yet. Stable review grid: factual support25, audience/offer20, specific argument20, continuity15, polish10, absence of unsupported promises/repetition10. Announcement cases are assessed as announcements; non-buyers are not assumed cold.

First validate all structural changes with scripted providers and contrasting fixtures. Each subsequent model experiment is limited to24 provider attempts including repairs/retries,750000 reported tokens checked between calls and1800seconds. Record exact inputs, arms, prompt versions, source references, costs and diagnosis before each experiment. No automatic repeats of an unchanged failure. Existing historical 76/100 remains on its original non-comparable track.

## Iteration 1 — structural implementation and scripted validation

1687 backend tests passed,2 dependency warnings,155.81seconds. Frontend27 tests,lint and types passed; disposable migration roundtrip/parity passed. Intent is persisted with legacy unknowns; proposition references survive paraphrases; invalid primary arguments may select whole alternatives without changing CTA; evidence context/provenance is preserved; lexical proof hints no longer veto revisions; selected raw excerpts reach the first draft. Scope-only tests distinguish valid functional announcements from an invalid problem requiring the existing bounded strategist correction.

No quality score yet. The next experiment freezes six cases (one recorded Tally, five labelled synthetic fixtures); three are held out from prompt changes. First create one common current Tally dossier, bounded to4 provider attempts,200000 reported tokens checked between calls,600seconds. This is separate from generation quality and identical for all three comparison arms. Each case then shares24 attempts,750000 reported tokens,1800active seconds across baseline/proposed/simple arms and any pairwise evaluation. Baseline is the hash-verified source archive; same compiled facts, request, audience and model. Limited policies are explicitly reported; not a comparison of the full balanced presets. Purpose: assess proposition/action fidelity and useful specificity, including the final source retrieval correction, not code correctness or conversion.

## Evaluation setup correction before comparative round2

The common dossier used1 provider attempt,44177 reported tokens,39.23seconds. The first proposed Tally run then exposed a read-adapter inconsistency: capability-profile creation used refreshed source metadata, while profile reads rebuilt the fingerprint from raw stored artifacts. It was falsely marked stale. That diagnostic run completed6 calls,176590 tokens,135.31seconds and an uncalibrated6/10 reader assessment; no coordinator quality score or improvement claim is assigned.

Fixed profile reads to use the same ArtifactStore context; added an invariant covering repeated reuse, metadata edits and unchanged historical rows. The original common dossier and first input remain immutable. New tally-announcement-v2.json mechanically rebinds temporary profile identifiers after verifying every dossier evidence quote,source and structured context is identical, and confirms CURRENT through the actual service. No second dossier model call. Round2 uses this current frozen input; round1 is excluded from comparisons. Five synthetic input files are now preserved on repeated preparation. No prompt tuning is allowed on the three held-out cases.

Round2: six cases, three generator arms, same frozen inputs and configured subscription model. Each case shares24 attempts,750000 reported tokens and1800active seconds across arms and comparisons. The simple arm deliberately uses one direct writer and one independent reader, retaining factual gates. Baseline and proposed use one candidate/reader, critic and at most one rewrite. Model repairs/retries count. Stop and diagnose a provider/auth or structural failure rather than launching duplicate arms.

## Direct production path — validation plan (18 October, Paris)

Round2 favors the simple arm unanimously over proposed on four of five completed comparisons; B2B is mixed. This supports an explicit deterministic shortcut for single emails, not removal of planning for sequences. New campaigns expose auto/direct/planned; historical campaigns retain planned. The direct path binds a unique source action before writing and retains factual gates and a blind read. A blocked draft is withheld; a weak reader assessment is visible without buying rewrites.

Thin-service recovery crossed from ledgerloop.example to an unrelated ledgerloop.co.za entity. Exclude that proposed output from comparative editorial claims; its judges lacked the recovered context. Fix identity anchoring and reject cross-domain redirects, homonyms and reserved synthetic domains. The shared 24-attempt thin-service ceiling was reached during judging; do not extend or retry it.

One new production-direct activation run is authorized for qualitative verification of the final wiring: at most4 provider attempts,150000 reported tokens checked between calls,300 seconds, same frozen source material and request. No model-based duel or critic. The run must actually use direct mode, preserve customer relationship, bind the known connect-drive destination, retain the indexing limit and pass factual gates. Scripted validation precedes the run. This is a fresh diagnostic track, not a replacement for frozen round2 outputs.

The activation production-direct check completed in2 calls,44446 reported tokens,29.92seconds; factual gates clean, correct connect-drive URL and indexing limit. A second contrasting B2C production-direct check on the frozen consumer-offer case is now planned under a separate4-attempt/150000-token/300-second ceiling, with no prompt edits. It verifies workshop scope, hand building versus wheel, collection after firing, and programme CTA. No additional judges are purchased.

## Completed review — 18 October 2026 (Paris)

Iteration 2, B2B planned: 86/100, first score on its own track (no comparable delta).
Specific read-only customer view and sample-board action; remaining procedural wording
is an ordinary edit. Best on track 86, round2/b2b-acquisition/proposed.

Iteration 3, activation direct: 88/100, first score on separate track. Customer
relationship, first-folder threshold and action URL preserved; remove repeated
indexing explanation at ordinary brand review. Unknown permissions/providers stay
unknown. Best on track 88, production-direct/activation/direct.

Iteration 4, B2C direct: 89/100, first score on separate track. Clear beginner offer,
hand building without wheel, post-firing collection and programme link. Tighten the
weekend headline. Best on track 89, production-direct/consumer-offer/direct.

These are coordinator judgments using the unchanged 25/20/20/15/10/10 grid, not
customer measurements. HTML inspected at 1280/390 px and CTA URLs verified. Direct
reader scores remain 6/10 and statuses degraded; they are not overridden. Outputs
are usable after ordinary brand review in the observed scope. Historical Tally 76
is non-comparable. Universal sellability and conversion remain unproven.

Validation: full suite 1709 passed, 2 dependency warnings; final targeted suites
70,75,19 passed with overlap. Frontend 27 tests, lint, types and static build;
Ruff/API schema; temporary migration and verified local migration passed. No test
pass is counted as a quality gain. The same old Tally email has 0 attributions versus
its historical 8, without editing history.

Total recorded provider attempts 117 and reported tokens 2861510 includes common
dossier, excluded stale-context diagnostic, three-arm generations, anonymous
judgments and two production-direct checks. Thin-service hit its 24-attempt ceiling
during judging; remaining ballot not bought. All snapshots retained.

Implementation complete for the agreed architecture scope. Automatic requires a
single explicit job and unambiguous documented action destination. Planned remains
for sequences and ambiguous/unsupported jobs. Supplied domains anchor material
recovery, including redirect checks. Remaining source gaps require actual brand
facts. No emails sent, production deployment, branch switch or commit.
Final report: docs/reviews/architecture-quality-implementation-2026-10-18.md.
