# National Trust — single-source membership case

## Iteration 1 — baseline, 2026-10-05
Question: can a membership email help a reader assess fit from one source, without filling missing site-specific detail with inventions?
Hypothesis: one official membership page supports a clear offer and review-options CTA; prices, geographic exceptions and savings must remain accurately qualified.
Conditions: balanced, default OpenAI, branded, one imported page, user-defined audience and no market dossier. Score the 25/20/20/15/10/10 grid against sources, assets and mobile rendering after completion. No customer sends.


## Iteration 1 result / correction hypothesis
Run da2a44ff failed: 0/1 delivered, estimated $4.4543, 6 recorded stages. Not scored: there is no deliverable. Source compilation completed (38 facts); a transport capacity refusal was retried. The final writer kept standalone copies of CTA and sign-off in BODY after a gate repair. Root cause: envelope prompt calls BODY the whole email, although the renderer appends CTA and sign-off separately.
Hypothesis for iteration 2: explicitly constrain BODY to argument paragraphs and remove only exact trailing copies of envelope fields at parsing, leaving the rendered CTA and sign-off intact. Preserve gates for nonidentical duplicate asks and source/length checks. This uses no extra model call and cannot fabricate a claim. Re-run the same input and review full actual assets before scoring.


## Iteration 2 result / iteration 3 hypothesis
Run 1f5832de failed with 0/1 delivered: not scored. Estimated $5.6467, 11 recorded stages. The terminal provider trace explicitly says the subscription usage limit was reached; this is not merely a capacity refusal. No quality verdict is possible. On resumption the account reports quota available. Reuse the same brief, sources and GPT-5.6 Sol allocation, with the tested audience-context correction loaded. No blind repeat while the external blocker remains. Review complete delivered assets and evidence before scoring.

## Iteration 3 — operator cancellation / iteration 4 hypothesis
Run d5dad417-f8aa-49ce-a7c8-a66bb5ab643a was cooperatively cancelled before any email delivery because launch preceded the verified server reload. Estimated $0.4846; not scored. A PowerShell empty JSON array was first mistaken for active work; no source or brief changed. Both cancellations are now terminal. Backend process 41740 has restarted successfully with the audience correction loaded. Iteration 4 preserves inputs and GPT model, reuses compiled knowledge, and tests full delivery under the recorded envelope.

Iteration 4 follow-up diagnosis: the terminal message correctly names the place-inclusion/visit-cost gap, but the report’s next-help field falls back to generic customer quotes after the blocked email is removed. Hypothesis: retain the exact unresolved material gaps as the report’s questions and primary recommendation before discarding blocked drafts. This is a deterministic report repair with no new model call. Extend the existing missing-material regression; do not buy another run just to verify text plumbing.

## Iteration 4 quality note — not scored
Run 01378db2-a929-42bb-8886-f2f5b6cd83bd: 0/1 delivered, needs_input pipeline / failed lifecycle, 9 recorded stages, estimated $6.2391. No complete deliverable, no score and no best scored iteration. The exact user audience reached all cold readers; eligibility and annual commitment stayed qualified. Official recovery did not establish local place participation, restrictions or visit costs, and the narrowed retry retained a material gap. No unsupported draft was delivered. This brief is not sellable on the single membership page; keep it as a negative case of insufficient source material. Next: obtain the relevant place evidence or change the objective, not another unchanged paid retry. The report now prioritizes this exact material need in questions/next-help (targeted regression passed); the immutable run snapshot predates that display correction.
