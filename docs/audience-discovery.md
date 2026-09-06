# Audience discovery

The audience button discovers candidates, fetches exact public URLs, then assesses the
whole candidate list using only that bounded corpus and the product capability profile.
Several core audiences are allowed. Novelty is not a requirement, and guessed response
rates no longer filter or rank segments or appear in campaign strategy context.

## Cost and boundaries

There are two logical model stages at the cartographer's configured tier (deep by default),
instead of the previous single stage. The additional assessment buys a closed-corpus
comparison of need, findability, counterevidence and product compatibility. Existing
ModelSession transport retries and JSON correction attempts can add actual calls.
The second stage is skipped when no candidates or readable sources are available.
This is a market job: campaign call forecasts do not change.

At most ten URLs are attempted through FixedURLFetcher, reusing its URL safety, redirect,
response-size and timeout rules. Assessment sees at most 6,000 characters per source and
48,000 in total. Identical normalized page bodies are counted once. Exploration can reuse
matching fetched pages for seven days; refresh fetches them again. Bounded source contents
are persisted in the existing JSON map payload and never included in the public read model.

Every retained quotation must occur on the exact fetched page it names. Retrieval dates
are assigned by the server. The interpretation is still model judgment: string matching
cannot establish that a quote logically proves a claim or that somebody intends to buy.
Reported queries are labelled as model-reported, not as an audited tool trace.

Priority is deterministic: explicit unsupported product requirements mean incompatible;
unmapped or unknown requirements cannot establish compatibility. Explore first requires
a supported compatibility judgment, need quotations from two distinct hosts, and a
verified access/example quotation, with no recorded counterevidence or duplicate warning.
These are conservative research-priority rules, not calibrated sales predictions. Related
hosts and paraphrased syndication can still represent the same underlying source.

## User workflow and persistence

Country/region, language, exclusions and customer/partner objective are optional. A scope
change starts a separate latest map. Exploration preserves previous audience names;
rescan replaces the displayed map with the latest results. Saved research and prospect
decisions are not deleted. Exploration adds only new audiences. Repeated normalized names
or exact structured identities are collapsed, including when reading older saved maps.
Exact structured identities use organization, workflow and need. User and buyer roles, trigger and current alternative are separate.
Model-suspected duplicates remain visible with a warning rather than being silently deleted.

All additions live in versioned JSON payloads; no database migration is needed. Legacy
maps remain readable and show an invitation to refresh. The legacy fit field remains for
payload compatibility but has no role in audience selection. Named prospect qualification
and deeper audience research retain their existing separate trust boundaries.

## Verification

`tests/market/test_audience_discovery.py` uses frozen synthetic page fixtures and scripted
responses, including a French audience and a product-specific capability outside the old
AI-agent catalogue. It exercises wrong-page quotes, invented quotes, copied pages,
counterevidence, unknown/unsupported capabilities, fetch failure, model failure, cache
reuse, old payloads and scope handling. API and campaign-context tests cover downstream use.

These tests establish mechanics, not real-world discovery quality. Before claiming a
measured improvement, compare saved old/new maps on the same source snapshots for several
products: a specialist service, multiple legitimate core buyers, sparse public evidence,
a French market and a non-software product. Review the top three candidates blind for
relevance, missed incompatibilities, redundant buying situations and quote entailment.
Live evaluation is deliberately not part of the test suite and spends subscription quota.
