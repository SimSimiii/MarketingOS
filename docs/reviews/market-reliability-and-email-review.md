# Market reliability, email review and prospect search

Historical first implementation. The later Tally replay found additional failures;
see [the 17 October corrections and qualitative result](tally-reliability-followup-2026-10-17.md)
for the current status. The statement about no paid evaluation below describes
this first implementation only.

Implemented on the existing branch, 16 October 2026. Existing workspace changes were preserved.
No real campaign or paid model evaluation was launched. Examples below are synthetic.

## Confirmed causes and changes

| Confirmed cause | Implemented behavior |
| --- | --- |
| `same_claim` treated almost every same-category assertion as equivalent. Specificity could win a whole category. | Compare individual propositions and captured scope. Show equivalent, documented difference, potential difference or unknown, with explanations. A figure alone does not imply superiority. |
| Broad category matching selected the first territory for a relevance fact. | A fact inherits territory only from one equivalent own proposition. Ambiguity stays unknown. Competitive overlap does not invalidate a supported fact. |
| Evidence lacked interpretation context; quotation matches could be checked against pooled rival material. | Preserve subject, source nature, scope, conditions, time and limits. Bind rival quotations to their actual cited page. Model-supplied verification labels are overridden by code. |
| A found proof could be a model-reported quote or search snippet with a confidence percentage. | Fetch at most eight exact public URLs using the existing protected fetcher. Show quote verified, page unavailable, quote not found or not checked. Human approval remains required. |
| A documented feature did not count as checkable evidence in preflight. | Functional campaigns may proceed without a testimonial. Documentation establishes a capability, not a customer outcome. |
| The same money token could be reused with an incompatible period, plan, unit or condition. | Reject explicit supported-scope conflicts. Review unsupported novelty and generalized customer results as advisory findings, without inventing a factual verdict. |
| Researchability, a company example and actual audience access could be conflated. | Separate problem evidence, product compatibility, captured usage/purchase evidence, findability, a public reach venue and researchability. Summarize counterevidence and its consequence. |
| Relevance treated an unknown required capability as a negative recommendation. | Unknown support requests targeted product verification. Explicit unsupported requirements and known hard company exclusions retain their negative recommendation. |
| Strategy replaced unmatched pain/current-alternative text with the first research item. | Use a single researched problem only when selected product evidence links to it; otherwise leave pain absent and constrain the argument. Never manufacture an alternative from list order. Carry fallback/validation information into the user report. |

Already-present safeguards were retained: absent product information was already unknown in audience mapping; reader scores were already labelled uncalibrated simulations in the UI/report. Their fields remain backward-compatible and are not presented as measured click or conversion rates.

## New user workflows

**Brand → Email review**, `/brands/<id>/email-analysis/`: paste a subject and complete body, specify audience/objective and intended merge fields. Immediate checks cost no model call. An optional cold read gives comprehension, doubts, relevance feedback, suggestions and an explicitly simulated assessment. Findings distinguish passages needing verification, missing context and editorial advice. Missing source support never means the statement is false. The draft is preserved without automatic rewriting.

Checks and completed analyses are persisted with their inputs and knowledge version. Cold reads use the existing admission/quota mechanisms, one active analysis per brand, a five-minute local timeout and the existing asynchronous Lambda dispatch when configured. Failure preserves finished checks. Manual refresh retrieves progress. Tenant guards protect history and detail routes.

**Audience → Find prospects**: choose companies, professional people, or public venues for reaching a consumer audience; choose public web or LinkedIn and edit geography, language, role, industry, size, visible criteria, exclusions and limit. Results and actual search criteria are saved per audience. Public search leads remain unverified; the existing company-site/contact-verification workflow remains separately available. Consumer mode returns communities, media and other public reach venues rather than private contact lists.

Public search reuses the existing LinkedIn search job infrastructure and its deployment availability gate. It is not a signed-in LinkedIn/Sales Navigator integration. Cold reads and public profile searches remain unavailable in credit-billing mode until their billing is implemented; the interface explains this before submission. Free checks and the existing verified-company workflow remain available.

## Representative before/after

| Synthetic input | Before | After |
| --- | --- | --- |
| Free delivery above $40 versus a $29 software subscription | Both occupy `price`, so they look equivalent. | Different propositions; equivalence is unestablished. |
| $29/user/month versus $29/user/year | Same amount can appear supported. | Billing-period mismatch is flagged; no inferred price advantage. |
| Competitor publishes a capability; our captured material is silent | A broad exposed category could imply weakness. | Our capability remains unknown; comparison needs more information. |
| Documentation establishes repair-status tracking, no customer testimonial | Preflight can stop before writing. | A factual functional argument remains available without promising a time-saving outcome. |
| Buyer problem is repair-status visibility; selected evidence describes inbox integration | First researched pain can be inserted by list order. | No unsupported bridge is inserted; describe the documented function or choose linked evidence. |
| Required translation capability is not documented | Negative recommendation. | Discovery-only, with a targeted verification action. |
| “New feature” with no dated launch evidence; one customer's result generalized to every buyer | Quotation/number match alone can appear sufficient. | Explicit advisory review of novelty, attribution and scope. |

## Compatibility and storage

- Old evidence remains readable with unknown context. It is not silently certified or automatically recompiled at subscription cost.
- Legacy proof remains `not_checked` and weak until source verification/user review establishes more.
- Saved market profiles are reinterpreted without another model scan. Missing capture never proves missing capability.
- Relevance dossiers carry an interpretation version. Older interpretations remain readable but are stale and cannot silently license current claims. Rebuilding is explicit; current exact input sets are reused at no model cost.
- Additive migrations `a31f9e70c246` and `b42e8d16c390` create analysis history and proof-verification/context columns. Migration upgrade, downgrade and re-upgrade were checked on disposable databases. No existing application database was stamped or migrated during this work.

## Verification and cost

- Full scripted backend suite: **1,607 passed**, approximately **117 seconds**. Two dependency deprecation warnings remain.
- After the final market API adapter change: **52 targeted tests passed**, including proposition serialization, saved positioning, generated contracts, email analysis and proof flow.
- Frontend: **24 tests passed**, ESLint and TypeScript passed; static production export includes the new email-review page.
- Ruff on `app tests`, generated API-schema freshness and whitespace checks passed. No formatter was run.
- Focused cases cover contrasted synthetic software, retail, service and audience situations; no correction is keyed to a brand name.

No automatic model stage was added to campaigns. Email checks use zero calls; an optional cold read normally uses one response, with up to one JSON correction plus existing transport retries. Public prospect discovery reuses one optional search stage. Actual calls and tokens are recorded. Existing campaign forecast tests pass.

Proof verification adds at most eight HTTP fetches, with existing concurrency three and a 30-second per-URL bound: approximately **90 seconds additional worst-case network latency**, estimated rather than measured on production traffic. Context and longer quotations can increase prompt tokens; their real quota/time effect was not measured. Model latency for the new optional workflows was not measured.

## Remaining limits

Deterministic checks do not establish arbitrary semantic entailment. Proposition matching is deliberately conservative and can miss paraphrases. Multi-price sentences can remain ambiguous. Date/novelty and outcome generalization cues request review rather than proving a claim false. Public reach venues do not establish consent, actual contactability or purchase intent. The usefulness of the feedback, search coverage and resulting campaign performance still need real user feedback and real send data; passing scripted tests does not validate conversion predictions.
