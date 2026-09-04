You are extracting an evidence-backed description of an audience independently of any
product. You have no web access in this call. Everything you may use is inside the fetched
corpus below.

# Audience candidate

{{ candidate }}

# Fetched corpus

{{ corpus }}

# Source rules

- Tier 1 is the buyer speaking directly in first person.
- Tier 2 is behavioural evidence such as job postings, tool listings, directories, public
  workflows, pricing pages, conference listings, and member listings.
- Tier 3 is third-party interpretation.
- Buyer phrases may come only from Tier 1.
- A problem needs Tier 1 evidence. Tier 2 or 3 alone cannot establish one.
- Tier 2 may support incumbent behaviour, triggers, signals, discoverability, and buying
  context.
- A Tier 3-only observation must be explicitly `inferred`, must include `inference_basis`,
  and must not be presented as buyer language or a grounded problem.

# How to cite

Every evidence reference must contain a source id from a `<source>` element and a verbatim
quote copied from that same source. Do not cite a URL or source id that is absent from the
corpus. Do not clean up punctuation or combine words from separate passages. Python checks
each quote against that exact source and discards failures.

# What to produce

- `situation`: who this audience is and the situation or workflow they are in.
- `incumbent_behaviour`: what they do now, including workarounds and tools where sourced.
- `problems`: distinct audience problems. Supply a local id if useful; Python replaces it
  with stable P1, P2... ids, computes corroboration from distinct domains, and decides
  grounding. `cost` is optional. If a cost contains a number, attach `cost_evidence` whose
  verified quote contains that number.
- `buyer_phrases`: exact Tier 1 language. The phrase itself must occur inside the attached
  quote. Use only `names_the_problem`, `names_a_tool`, `complaint`, or `avoided`.
- `triggers`, `desired_outcomes`, `signals`, and `where`: sourced observations, or explicitly
  inferred observations under the Tier 3 rule above.
- `sophistication` and `sophistication_basis`: observed awareness using one of `unaware`,
  `problem_aware`, `solution_aware`, `product_aware`, or `most_aware`, with sourced basis.

# Hard boundary

Answer only: “What is true about this audience independently of our product?” Do not mention
or derive product fit, `why_them`, campaign angles, product objections, features, evidence,
problem-to-product mappings, campaign copy, or recommendations about what to sell or say.
There is no product brief in this prompt. Do not fill that absence from memory.

Never invent quantitative costs, frequencies, percentages, or market sizes. A number may
appear only when it is in a supporting quote from the fetched corpus. It is fine for any list
or field to be empty; an empty verified answer is better than a plausible unsupported one.
