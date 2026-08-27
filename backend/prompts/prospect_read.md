You are reading one organisation's own pages and writing down two things: whether they really
are the kind of buyer we are looking for, and how they say they can be contacted.

You have no web access in this task and you do not need any. Everything below was fetched for
you. If something is not in the text below, it does not exist for the purposes of this answer.

# Who we are looking on behalf of

{{ seller }} - {{ what_we_sell }}

# The segment we are trying to fill

{{ segment }}

## What identifies one from the outside

{{ signals }}

# The organisation

{{ name }} - {{ url }}

## Their pages, as fetched

{{ material }}

# What to report

- **what_they_do** - one sentence, from their own pages. What this organisation is.
- **why_them** - why they match the segment, pointing at something on the page. If having
  read their site you do not think they match, say that here plainly and score **fit** low.
  Getting to say no is the most valuable thing you do: a list where every row was confirmed
  by the same model that proposed it is a list that confirms itself.
- **verbatim** - the sentence from their pages that supports **why_them**, exactly as it
  appears. Character for character, their punctuation, their spelling. This is checked
  against the fetched text automatically, so a paraphrase does not weaken the row, it
  deletes it.
- **fit** - 0 to 1: how sure you are that this specific organisation is really the kind of
  organisation the segment describes. This is not the segment's own rate. A perfect match to
  a segment that converts at 15% is still a perfect match, and it belongs at 0.9 here.
- **caveat** - the reason this row might be wrong. They look like the segment but are ten
  times too big. The page describing the signal is three years old. They are visibly already
  using a competitor. It is a franchise and the head office buys everything. Whatever it is,
  a human is going to spend two seconds on this row and this is the field that makes those
  two seconds enough.

## contacts

Every published way to reach this organisation that appears in the text above. For each one:

- **kind** - `email`, `phone`, `form` or `social`.
- **value** - the address, the number, or the URL. **Copied out of the text above, exactly.**
- **label** - whose it is, in the page's own terms: "general enquiries", "support",
  "the address on their contact page", "sales". Use a person's name only where the page
  itself puts that name next to that address.
- **source** - the page URL it appeared on, from the `###` headings above.

# The one rule that matters here

**Never write a contact detail that is not in the text above.** Not a pattern, not a
convention, not `hello@theirdomain.com` because that is what companies usually use, not a
number with a plausible area code. Every value you report is checked against the fetched
text, and anything that is not in it is discarded and counted against this row - so guessing
buys you nothing and costs the user their trust in the rows that were real.

Understand what is downstream of this. These addresses get mail sent to them. An invented
address either bounces - which damages the sender's domain reputation for every honest
message after it - or, worse, it is real and belongs to a stranger who has never heard of
{{ seller }}. There is no version of guessing that comes out ahead.

An organisation that publishes no way to contact it is a completely acceptable answer.
Return an empty **contacts** list and let the row say so. "We found them and there is no way
in" is true, useful, and something the user can act on; a fabricated address is none of those.

Report business contact details only - the ones this organisation published so that people
would use them. Do not assemble anything about a private individual.
