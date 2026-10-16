# Friend preflight — 13 October 2026

## Export correction hypothesis — 14 October

The downloaded text contains the CTA label but no URL; the HTML contains the correct product link. Persistence calls the copy-only renderer instead of passing the resolved presentation destination. Use the same resolved destination for text and HTML, validate it with the existing URL policy, and preserve source assets. Verify with deterministic renderer and API tests; no new model run is needed to test rendering.

New independent case; historical iFixit runs remain unchanged. Hypothesis: current generator delivers one usable French email and preserves US scope and non-exhaustive warranty exclusions. Stable quality grid: facts 25, audience/offer 20, argument 20, continuity 15, rendering 10, unsupported promises/repetition 10. Inspect actual delivered text and source ledger; test results alone do not raise quality. This generation measures model behavior, not a code smoke test. No outbound messages.

## Competitor positioning correction hypothesis

Saved Plausible market analysis classified "Trial signups increased 84%" and visitor-to-trial conversion rates under price. The deterministic ledger classifier treats any occurrence of `trial` as a commercial term. Remove that ambiguous marker while preserving free offers and explicit trial durations. Expected result: growth statistics no longer create a false pricing territory; explicit price evidence and actual trial offers retain their classification. Verify with regression tests, without another market model call.

## Iteration 1 — French e-commerce result

84/100 internal review judgment; first score in this new comparison track, best 84 (run b361b5d4-0808-4838-9b4f-2327f7843472). Facts 25/25, audience 18/20, argument 14/20, continuity 11/15, polish 7/10, unsupported/repetition 9/10. Not comparable to earlier three-email English runs.
Kit composition matches R2/R3; US warranty and documented consumables match R14–R19, with “Parmi” preserving a non-exhaustive list and R5 supporting the conditions link. No invented discount, urgency, delivery or repair outcome.
Remaining weaknesses: long warranty paragraph and warranty-heavy preheader; no price; HTML declares English for French text. Copy usable with normal brand review and minor editing; browser rendering still to inspect.
Completed in 7m20s, estimated processing cost $4.2364 (subscription run; not an invoice), 727,868 input and 54,328 output tokens. One email delivered, no reported errors or contract violations. No further paid run justified for marginal copy polishing.

### Rendering and functional verification
Mobile design preview is readable without horizontal clipping; its iframe scrolls. Text download succeeds. Score remains 84 after inspection; no score increase from tests. Synthetic local pending execution verified the new disabled start button; the fixture was removed immediately.
Backend: 1,478 tests passed, 2 existing deprecation warnings, Ruff clean. Frontend after the button change: lint/typecheck clean, 17 tests pass. New fixes are local, not deployed.
Mehdi production account created via temporary IAM-only Lambda, with an atomic audit record, normal owner role in its own workspace, free plan and five runs. Temporary function deleted. Actual login/me succeed, workspace lists empty, admin API rejects its token (401), logout succeeds. No notification sent.

## Iteration 2 — deterministic export correction

84/100, unchanged; best remains iteration 1 at 84 for the same generated copy. No new model call. Re-rendered the saved asset with the corrected text renderer, reviewed the CTA line, and saved `email.fr.corrected.txt`; original run snapshots unchanged.
Supported content and US warranty scope remain strengths. The text CTA now carries the same destination as HTML; explicit destinations also survive checkpoint recovery. Warranty density and HTML language declaration remain defects. Targeted renderer/API/recovery tests pass; full regression and final deployment pending.

### Final verification — 14 October
Final suite: 1,483 local tests pass; AWS: 1,478 pass, five skipped. Ruff/schema/migration/dependency checks pass. All three fixes deployed successfully (console cc822a6, API 16553a1). Post-deploy app/health/ready/admin health return 200, anonymous campaigns 401; database readiness 0.25s in this warm check. Production draft setup/cleanup also passed without spending quota. The real production generation happy path remains explicitly unverified.
