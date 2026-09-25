# Resend / Supabase campaign quality

## Iteration 1 — implementation hypothesis

Cause observed in the supplied run: the craft loop can replace only `single_idea` while retaining the original need, mechanism, evidence, objection and CTA. That permits internally mixed emails such as a volume subject, a templates body, a Supabase audience and a generic signup CTA.

Hypothesis: make the Strategist provide complete alternative arguments and make drafting, gates, critique, rewrites, pivoting and subject selection use the selected argument as one indivisible unit. Prefer audience relevance plus support over competitive novelty. Expected change: each candidate keeps one coherent situation → claim → proof → next-step chain, and a stalled draft changes that whole chain rather than its claim alone.

Validation for this iteration is implementation-only at the user's request: no unit tests and no billed campaign generation. Product quality is therefore not scored yet.

Implemented: structured `alternative_arguments`; normalization of their evidence and claim boundaries; candidate-specific writing, gates, critique, rewrites and subject optimization; persisted/reporting data now follows the winning proposition. Balanced and maximum presets now start from two propositions. Ruff, Python compilation and two direct smoke checks passed. Remaining uncertainty: only a regenerated campaign can show whether the Strategist reliably supplies two strong propositions and whether the resulting email clears the sellable-result bar.

## Iteration 2 — supplied regeneration review

**73/100, first formal score; best 73 (iteration 2).** The two candidates are genuinely different propositions, and the winner keeps its subject, Supabase/Auth situation, SMTP mechanism, limits and body aligned. The main defect is now the next step: all three readers want a Supabase setup guide before account creation, while the email repeats “Sign up for free” in the body and CTA. Evidence: supplied run completed 1/1 at simulated 6/10 after two rewrites; the winning asset names the setup path and preserves the separate Supabase limit, but remains below the system's own 7/10 floor. Verdict: improved and useful as a draft, not yet sellable as finished copy; next action is CTA/resource-fit preflight plus deterministic duplicate-CTA prevention.

## Iteration 3 — correction hypothesis

Cause: the structural checks treat the body and CTA as separate fields, so a body line can duplicate the rendered button. Separately, the critic returns only `ship/revise`, which makes a missing guide or unsupported operational answer look like a prose defect and buys another rewrite. Hypothesis: block CTA duplication deterministically, classify critique outcomes as copy-fix versus strategy/material failure, and pivot or stop instead of asking the writer to invent missing support. Expected change: one clean ask per email, fewer futile rewrites, and an explicit material gap when no supported next step can answer the reader.


### Iteration 3 — implementation and validation

Implemented the correction without running a billed campaign. The deterministic gate now blocks a standalone body line that repeats the separately rendered CTA. The critic now identifies whether the failure is editable copy, a weak argument, or missing material; the craft loop pivots to a complete unused argument when it can, otherwise it stops and exposes the unresolved gap in the campaign report instead of buying another futile rewrite.

Validation: 136 focused marketing tests passed, then the full backend suite passed **1,262 tests**; Ruff also passed. This iteration is **not rescored** because tests do not measure the delivered copy. The best verified result remains **73/100 (iteration 2)** until the unchanged Resend/Supabase case is regenerated and reviewed.


## Iteration 4 — supplied regeneration review

**67/100, down 6 from the best; best remains 73 (iteration 2).** The email is clear about Test Mode being API-only, removes the duplicate CTA, and the final report correctly says the 5/10 draft was not ready. Its central test still does not reduce the Supabase/SMTP uncertainty shared by all three readers, while the Raycast waitlist example does not bridge that gap. Evidence: completed unchanged-case run `c757de06-158b-4bf5-a609-ecd7479e05e0`, one rewrite, simulated 5/10. Verdict: understandable and cautious, but not paid-quality tailored copy.

## Iteration 5 — correction hypothesis

The trace shows the critic describing the blocking defect as requiring the argument to be rebuilt, yet the loop treated it as a copy edit. The response schema currently advertises `failure_mode=copy` as an optional default, so the model can supply a detailed strategic diagnosis without making the routing decision. Hypothesis: require an explicit, internally consistent failure classification in the model response, put that decision before line edits in the prompt, and persist it in execution events. Expected change: a proposition that cannot earn its CTA pivots to an unused complete argument, or records an unresolved material gap, before spending another writer/read cycle.


## Iteration 5 — real regeneration

**69/100, up 2 from iteration 4; best remains 73 (iteration 2).** The email clearly explains Resend and the critic now does the right operational thing: run `51208dfb-373a-4503-955b-ed7a986d8776` classified the shared obstacle as `missing_material`, named the absent Supabase/SMTP test proof, and stopped with zero rewrites. The delivered asset still implies unsupported integration inspection/validation and asks for account creation before establishing what the test proves. Evidence: simulated 6/10, 5 agent calls, 324,864 input / 25,140 output tokens, estimated $4.125. Verdict: safer and cheaper failure, still not paid-quality copy.

## Iteration 6 — correction hypothesis

The remaining failure is created before writing: a complete argument carries a CTA label but no explicit contract for the decision that action enables, the verified material supporting that payoff, or the boundary it cannot validate. Hypothesis: require the Strategist to attach a next-step decision, payoff, evidence ids and limitation to the primary and alternative arguments, normalize those ids, and show the contract to the writer and critic. Expected change: generic trials and API-only tests are rejected or honestly narrowed when the audience's actual decision concerns another interface or production path.


## Iteration 6 — real regeneration

**77/100, up 8 from iteration 5 and the new comparable best.** Run `71ca5d70-d337-4dd8-8926-92a44ce37004` produced a coherent, concise email with clean deterministic checks; its CTA now states the supported signup payoff and explicitly says what it cannot validate. All three readers still required the exact Resend-to-Supabase Auth route before account creation, so the critic correctly stopped with `missing_material`; estimated cost was $4.2756. Verdict: strong direction and honest boundaries, still not paid-quality without the integration resource.

## Iteration 7 — automatic material-recovery hypothesis

The first source-enrichment proposal was invalid as a product fix: manually attaching the pages merely moved the work from the user to the operator. The system already names the exact missing material, and official pages containing it exist, so that diagnosis must trigger a bounded recovery step inside the run. Hypothesis: locate official sources with web search, fetch the exact URLs in process, reject every quotation that is absent from the fetched page, add the verified evidence and source text to the run and stored brand knowledge, then re-plan and re-craft once. Expected change: the same untouched campaign resolves its Supabase/SMTP gap without a user or operator adding any source, while an unverified or still-missing fact remains an explicit gap rather than becoming copy.


## Iteration 7 — automatic search transport

Score: **62/100** (-15 versus iteration 6; best remains 77). The copy still exposed the missing setup decision honestly and the pipeline attempted recovery automatically, but the provider placed `--search` after `exec`, so the material-research role failed before finding a source. Run `5dffa4d1-8e07-45c2-b5dd-a082d67cd903` completed but did not validate the recovery hypothesis. The CLI flag order was corrected before the next run.

## Iteration 8 — sources recovered, then discarded by the old boundary

Score: **65/100** (+3; best remains 77). Run `0109e772-b643-4d88-bca1-4e2638232859` autonomously found and verified Resend SMTP, Supabase custom-SMTP/rate-limit and Resend test-event documentation, persisted them as `R1`–`R3`, and replanned. The stale relevance contract then removed those new ids, so the final generic signup email assigned and spent no evidence. Cause: the campaign claim boundary was a snapshot from before recovery.

## Iteration 9 — recovered proof reaches the email

Score: **78/100** (+13; new best, run `4473b345-5da5-465c-8152-312732d57607`). The final email is clear and concrete, spends `R3`, names the delivered/bounced/complaint test addresses, and passes every deterministic gate. The system also found and persisted `R4/R5` automatically when the first proposition exposed a quota gap. It is still below the paid-quality bar: the winning alternative leaks quota facts from the other proposition and ends at generic signup, while all three readers ask for the official setup/prerequisite page.

Cause and next hypothesis before editing: complete alternatives carry their own argument but can still inherit unrelated proof through the writer slice, and their CTA is not mechanically tied to the recovered fact that supports its payoff. Normalize an R-backed next step to the corresponding official source, exclude the primary proposition's evidence when an alternative is selected, and block a generic onboarding label when the plan points to documentation. Expected change: the winning test-address email stays on one argument and sends the reader to the exact documentation that resolves the click question.


## Iteration 10 — exact setup found, audience fit still fails

Score: **81/100** (+3; new best, run `34fcbfd1-622b-430a-b06b-5c9ba0451ed8`). The automatic search found the strongest missing source so far: Resend's own Supabase SMTP guide (`R6`), plus Supabase's separate 30-message/hour setting and exact Resend Free/Pro limits (`R7–R9`). The final email spends `R6–R8`, is technically concrete, and has a coherent review CTA label.

It is still below paid quality. One reader marked a substantial audience mismatch because the selected segment does not establish Supabase use; the argument presents another set of limits more clearly than a benefit; and the plan contains two URLs, so HTML falls back to the Resend homepage instead of the setup guide. The tournament then overrode the relevance finding in a side-by-side vote.

Cause and next hypothesis before editing: candidate relevance is measured but excluded from the tournament's eligibility prefix; recovered CTA normalization accepts a set containing the right URL even when it contains another; and recovered partner evidence is not converted into a conditional-audience constraint. Make relevance eligibility deterministic, collapse the CTA to one evidence source, condition unestablished integrations, show persisted R facts prominently, and reuse matching R facts before web search. Expected change: a relevant argument wins, says “if you use Supabase,” and links to exactly one inspectable guide without another search pass.

## Iteration 11 — quota interruption and revised diagnosis

Run `fe9a4bf1-c984-42f8-8ceb-46987714aeb7` failed at the writer after the Strategist completed because the subscription CLI reached its usage limit. It delivered no email, so quality is **not scored**; estimated cost was $1.1962. Quota is available again. The source of a remaining audience leak is now clear: the integration guard treated a model-derived audience segment as confirmation that each recipient uses the named partner. Hypothesis before editing: use only explicit campaign context to establish partner use, and require meaningful coverage of a diagnosed material gap before reusing existing facts. Expected change: conditional integration language and a precise official CTA survive the next unchanged-case run; unrelated old facts cannot suppress a needed search.

## Iteration 12 — audience and URL fixed; payoff still unclear

**78/100**, down 3 from the previous scored iteration; best remains **81/100** (iteration 10, `34fcbfd1-622b-430a-b06b-5c9ba0451ed8`). Run `a9cd31e4-6638-433b-a0b0-30ca91b27fc8` delivered one clean, source-supported email with a conditional “If you use Supabase” premise and a rendered button linking to the exact official guide. All three readers understood the offer and marked it relevant. But they gave it only 4/10 pull: it foregrounds the Auth limit that remains, without explaining which built-in sender limit the custom SMTP route changes or where to inspect the remaining setting. The critic labelled this `argument` despite saying the supplied evidence supports the distinction, so no copy revision was attempted. Estimated cost: $5.3791. Verdict: accurate draft, not yet paid-quality.

Cause and next hypothesis before editing: the brief and writer are allowed to name the residual limitation without first spelling out the supported benefit; the critic can then misroute an omitted bridge as an irreparable proposition even when the material already contains it. Require an explicit “what improves / what remains” contrast when both are evidenced, prioritize the benefit before the caveat, and classify a missing explanation as a copy fix when the same evidence can supply it. Expected change: the email answers the reader's causal question and uses the already verified documentation to make the next click worthwhile.

## Iteration 13 — wrong order of decisions

**75/100**, down 3; best remains **81/100** (iteration 10). Run `429c1972-efa6-4cc0-b3d4-7d9283f40d66` completed with a clean, source-backed, conditional email and a valid pricing button at estimated cost $3.5464. Its plan comparison is accurate, but three readers gave it 4/10 pull because pricing comes before the more useful check: whether this project has custom SMTP and which Auth limit currently applies. The critic named existing evidence `R2` that could answer that first decision, then classified the failure as `argument`; the pipeline stopped without re-planning. Not paid-quality.

Cause and hypothesis before editing: automatic recovery only runs for `missing_material`, while an `argument` diagnosis that cites an existing verified fact can be just as actionable upstream. Route a bounded argument replan through the cited ledger fact, retaining the critic's exact gap; use web search only for facts truly absent. Expected change: the system puts the read-only configuration check before provider pricing, with an official page as the CTA, without user or operator additions.

## Iteration 14 — automatic replan works, targeting remains too narrow

**79/100**, up 4; best remains **81/100** (iteration 10). Run `8cbeafb4-8e17-45e5-8e85-8e35af49a69a` automatically replanned from cited verified material and delivered a clean email with a conditional audience premise and a working official-guide button. It spent R6–R8, but the three readers gave it 5/10 pull: the selected audience is known to own email, not known to use Supabase, so the integration guide still lacks a near-term reason to open. The second pass bought 16 role calls and an estimated $13.8983. Verdict: useful draft, not paid-quality; the extra calls did not justify the lift.

Cause and hypothesis before editing: researched examples of individual users of a partner platform are being promoted into the primary launch proposition for a broader user-selected segment. Keep those examples as conditional supporting material, but prefer a product benefit applicable to the whole selected segment unless the user explicitly targets that integration. Expected change: the primary email earns its CTA from the known job rather than a guessed installed stack; partner setup can remain an alternative for a specifically targeted campaign.

## Iteration 15 — broad plan lost to a niche bake-off candidate

**77/100**, down 2; best remains **81/100** (iteration 10). Run `bd013afb-3f6d-4b9e-8fa0-24508c17783c` delivered one clean email with an official guide CTA at estimated cost $6.3245, but three readers again gave it 5/10 pull. The saved brief reveals the mechanism: its primary idea addressed transactional email for the selected backend engineer broadly; a Supabase-specific alternative won the candidate comparison even though the user never established Supabase use. The email consequently led with a conditional 429 scenario and a guide most recipients might not need. Not paid-quality.

Cause and hypothesis before editing: candidate selection uses reader pull but does not enforce whether a partner-specific proposition is eligible for the user-selected audience. Exclude an alternative whose premise depends on an unconfirmed installed partner before paying to draft and read it; retain it when the request explicitly targets that partner. Expected change: the broad primary idea reaches the final asset and the run uses fewer calls.

## Iteration 16 — candidate eligibility implemented; validation pending quota

**Not scored**: no email was generated after this correction. The generator now removes a partner-dependent alternative before the paid bake-off when the user-selected audience and request do not establish partner use; it retains the same alternative for an explicitly targeted campaign. This is generic logic based on the source and request, with no Resend/Supabase exception. Focused tests, Ruff and the full backend suite (**1,280 passed**) are clean. Best observed quality remains **81/100** (iteration 10). The Codex subscription reached **99% of its five-hour window** on 2026-09-21 at 13:29 UTC; the window resets at **17:41:30 UTC**. Next action: restart the backend to load the changed code, regenerate the unchanged case once, inspect the delivered asset and update this score. Do not infer a quality improvement from tests alone.

## Iteration 17 — broad audience fixed, unsupported click payoff

**72/100**, down 5 from the previous scored run; best remains **81/100** (iteration 10). Run `8ec56d83-2670-49fb-8a18-815da02446b1` completed at estimated cost $5.7886. The Supabase-specific alternative was correctly removed and the email is understandable and clean, but the broad primary promise asks the reader to sign up for a simulated API event without any `next_step_evidence_ids`; assigned `E1` was not spent. Three readers gave it 4/10 pull and could not tell what the test would prove for their email workflow. Verdict: not paid-quality.

Cause and hypothesis before editing: the Strategist can supply a concrete-sounding CTA value while assigning no evidence for it, and the pipeline records the omission but still buys drafting and reading. Correct the brief once before craft whenever a promised next-step payoff lacks a matching assigned proof id; if the model cannot support that payoff, require a narrower action. Expected change: an official, inspectable first step with evidence tied to the benefit, or an honest strategy gap before the weak signup email is written.
