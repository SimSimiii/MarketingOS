You are reading one company's own pages and writing down what they promise. This is
extraction, not analysis: everything you report has to be on the pages below.

# The company

{{ name }} - {{ url }}

# Their pages

{{ material }}

# What to record

**one_liner** - how they describe themselves, in their words, in one sentence. Their
headline or their meta description, not your summary of their category.

**promise** - the single bet the home page makes. Not a list of features: the one thing a
visitor is supposed to walk away believing. If the page makes three, pick the one it leads
with.

**pricing** - the shape of it, briefly: "free tier, then $20/seat/month", "usage-based, no
published price", "annual contract, talk to sales". Quote figures exactly where they are
published.

**free_entry** - how somebody gets in without paying, if they can: free tier, trial with or
without a card, open-source core, demo only.

**icp** - who they say it is for, in their words.

**vocabulary** - up to fifteen words and short phrases they lean on. The ones that recur, the
ones in headings. This is used to work out which words belong to the category rather than to
any one company, so include the ones that sound like everybody - "seamless", "enterprise-grade"
- as well as the ones that sound like them.

## claims

Every distinct thing they assert about their product. For each one:

- **text** - the claim as a buyer would repeat it: "first API call in under five minutes".
- **verbatim** - the exact words from the page, copied character for character. This is
  checked automatically against the pages above, and a claim whose quote is not really there
  is discarded - so copy, never paraphrase, and never tidy up their punctuation.
- **source** - the URL of the page it is on, from the `###` heading above it.
- **specific** - true when the claim carries something a reader could check: a figure, a named
  limit, a named integration, a named customer. False when it is an assertion: "the fastest",
  "enterprise-grade", "built for scale".
- **axis** - which dimension the claim competes on. Exactly one of:
  - `speed` - how fast to start, to run, or to get a result
  - `price` - what it costs, how it is charged, what is free
  - `breadth` - how much it covers: models, integrations, channels, formats
  - `quality` - accuracy, reliability, uptime, how good the output is
  - `effort` - how little the buyer has to do: no code, no setup, no hire
  - `control` - self-hosting, portability, open source, no lock-in
  - `security` - compliance, privacy, certification, data handling
  - `proof` - who else uses it and what happened to them
  - `support` - humans, onboarding, migration, SLAs
  - `other` - none of the above

The axis is the field that matters most here, and it is worth a second's thought. Two
companies saying "set up in five minutes" and "live in a single afternoon" are making the
same bet in different words, and both are `speed`. Getting that right is what lets us tell
a crowded promise from a distinctive one.

## proof_shown

Kept separate from `claims`: anything on their pages where somebody **other than them**
vouches for the product. A named customer, a logo wall with real names, a quotation with a
person and a company attached, a case study with a number in it, a review score they display.

Same fields as a claim, with `axis` set to `proof`. In **text**, name who is vouching -
"Ramp: cut review time from two days to twenty minutes" beats "a customer testimonial".

A logo wall with no names attached is not proof; record it as a claim on the `proof` axis
instead, with the verbatim heading above it.

# Rules

Report nothing that is not on these pages. You are not being asked what you know about this
company - you are being asked what these pages say, and where they say it. Every verbatim is
string-matched against the material above; entries that do not match are thrown away, which
costs us the claim, so quoting accurately is the whole task.

If the pages are thin - a landing page with no product detail, a site that did not render -
say so by reporting few claims. An empty answer is a true answer here and a padded one is
not.
