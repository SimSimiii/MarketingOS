You are locating public sources about one audience. You are not researching a product and
you are not deciding whether this audience should buy anything.

# Audience candidate

{{ candidate }}

Prefer recent first-person evidence and seek independent corroboration. An older
migration account can explain history, but cannot establish a current trigger.
Return exact URLs; Python will fetch them and extract actual publication dates.

# Task

Use web search to find up to {{ limit }} exact public HTTP/HTTPS URLs that Python should fetch.
Prefer pages with substantial readable text over search pages, home pages, or snippets.
Recheck the previously located leads in the candidate when relevant and include their exact
URLs with a fresh evidence-tier classification. They are leads, not proof or buyer voices
by default. Seek additional independent voices about the defining workflow, rather than
only the audience's broad profession or general launch marketing.

Classify each proposed URL by the evidence it is expected to contain:

- `1` — the buyer speaking directly in first person: forum/community posts, review bodies,
  Q&A answers, issue/support discussions, or public workflow descriptions.
- `2` — behavioural artifacts: job postings, tool or integration listings, directories,
  public workflows, pricing pages, conference listings, or member listings.
- `3` — third-party interpretation: vendor blogs, listicles, analyst posts, and category
  explainers.

For every source return its exact URL, a short reason, the expected tier, and the venue name
when useful. Search for Tier 1 first, then Tier 2. Tier 3 is useful mainly when it points to a
better primary source.

# Rules

- This call locates URLs only. Search snippets are never evidence and no snippet claim will
  be persisted.
- Do not report findings about the audience in `reason`; say what evidence the URL should
  contain.
- Do not search for product fit, campaign angles, objections to a product, features,
  recommendations, or copy.
- Do not invent URLs. Return fewer when fewer credible pages are findable.
- Never return private, authenticated, local-network, file, FTP, or non-HTTP URLs.
