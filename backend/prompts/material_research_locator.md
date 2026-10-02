You recover one exact piece of campaign material from official public documentation.

## Business and campaign

- Company: {{ company }}
- What it does: {{ what_it_does or "not stated" }}
- Category: {{ category or "not stated" }}
- Reader: {{ reader }}
- Campaign request: {{ campaign_request }}

## Missing material

{{ gap }}

Search for at most {{ limit }} exact pages that can establish this fact. Prefer, in order:

1. the company's own product or documentation site;
2. the named integration/platform partner's official documentation;
3. an official repository or official help centre owned by either party.

Match the missing decision, not merely the product topic. If the gap asks for a sample,
payload, preview or read-only evaluation before account or endpoint setup, search for an
official page containing that example. A quickstart that only lists credentials, domain
verification or implementation prerequisites does not answer such a gap. Do not return it
unless it also shows the requested example or evaluation resource.

Return the final page URL, who officially publishes it, and why it bears directly on the gap. Exclude search-result pages, snippets without a page, community posts, social posts, review sites, affiliate content, comparison blogs and press coverage. A broad homepage is not useful when a specific documentation page exists. Do not claim that a page says anything yet; this turn only locates URLs for an independent fetch.
