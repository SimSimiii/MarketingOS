# LinkedIn and manual run refresh

## Using it

Open a brand and choose **LinkedIn**. Finding people is two steps, and they are
separate because they are separate questions.

**Propose criteria** answers "who is worth writing to" from what this brand
already knows: its compiled knowledge base, and - when one has been mapped - the
audience you pick, whose buyer role, observable signals and population are a
better description of the buyer than the company's own marketing. One call, no
web access, and nothing is searched for yet. The proposal comes back as roles,
industries, organisation size, geographies, exclusions and - split in two -
**what is visible on the profile** and **corroboration**. All editable, and you
can fill them in by hand and never buy the proposal at all.

That split is the difference between a search that returns leads and one that
returns nobody. A LinkedIn page shows a title, a company, a headcount and an
about section. Everything else an audience map knows about its buyer - a
repository, a changelog, a postmortem, a forum thread - is company-level
evidence the prospect finder fetches pages to check, and holding a profile
search to it asks it to prove per person something no profile carries. So
profile-visible criteria decide who comes back, and corroboration only
strengthens a lead: found, it lands in the candidate's reason; absent, it
changes nothing. The audience's own `where` - the forums and directories it
gathers in - is not sent to this step at all, because it describes a different
channel.

**Search LinkedIn** then looks for people matching those criteria. The typed
query is optional and additive: a search runs on the criteria, on a query, or on
both, but never on neither. Up to ten candidates are returned, with a reported
source URL and excerpt, and the criteria the search ran against are saved beside
them. Each candidate's reason says which criteria the public result matches and
names what is unverified. Results are public-search leads, not independently
verified identities, current jobs or purchase intent. There is no authenticated
LinkedIn connection, restricted-profile scraping or access to private account
information.

The search is bounded to three rounds and then answers with what it has: a web
search reads whole pages, which makes it the most expensive call in the product,
and a fourth angle that has to leave LinkedIn is evidence the criteria are wrong
rather than evidence the market is empty. Empty searches are valid results, and
the note says which criterion emptied the list - the one thing that tells you
which field to change.

**Write to them** hands the name and URL to the campaign form - and only those,
never the search result's own guess at their need or commercial relevance.
Writing is a campaign because planning is: see below.

## Writing one, as a campaign

A LinkedIn message is a deliverable of the campaign form, chosen the same way an
email sequence is: fill in **Write to one person on LinkedIn** (name, profile URL,
any facts about them you have checked yourself, format and language) and press
**LinkedIn Message**. Everything above it on that form still applies - the brand,
the audience segment, the sender, the goal, the preset and the model pins.

The run is the ordinary pipeline with a shorter craft phase: compile or reuse the
knowledge, apply campaign intelligence, read the proof posture, then one
Strategist call that plans this message against the chosen audience, then the
writer. It appears on Runs, records its steps in the same timeline as any run,
and its deliverable sits with the campaign's other work.

The writer has no web tools. Numbers, prices, quotations and URLs must pass the
existing evidence gate against the brand ledger or user-confirmed context. The
objective is not evidence, and neither is a search result's description of the
recipient. Placeholder and length failures cause one rewrite; an invalid final
draft is withheld and the run reports no deliverable. This is not the email
campaign's cold-reader panel: no comprehension, response-rate or conversion score
is claimed. The report says so rather than printing a zero - `reads_expected` is
false, each line's `read_reported` is false, and the run page shows "Checked, not
scored" where an email campaign shows a pull average.

Proposing criteria and searching each normally use one balanced-tier model call,
at most two structured-output attempts. A LinkedIn campaign's forecast is the
knowledge compile plus two to four calls - one Strategist, one writer, and the
correction turn each may buy - against the eleven-and-up an email sequence costs;
it is shown before the run is bought, like every other forecast. Transport
failures follow the existing ModelSession retry policy. Actual successful
call/token usage is saved on each job. No email pipeline calls change. Nothing is
sent to a LinkedIn user by this feature.

## Runs

The Runs board, campaign execution, market and compilation pages use **Refresh**.
There is no browser EventSource or periodic HTTP polling. Saved timeline events
still pass through the existing fold, so the same history appears after a reload.
Errors retain the last loaded snapshot and offer an explicit retry. LinkedIn jobs
appear on Runs and their brand workspace; the latest 50 jobs are shown per brand.

## API and storage

- `POST /api/market/{brand_id}/linkedin/criteria`: segment_name, hint, target.
  All optional. Requires compiled knowledge. Returns a persisted job with 202.
- `POST /api/market/{brand_id}/linkedin/search`: query (optional), criteria
  (optional), target (`people` or `companies`), limit (1–10). Refused with 422
  when neither a query nor usable criteria are supplied. Returns a job with 202.
- `POST /api/market/{brand_id}/linkedin/messages`: recipient_name, recipient_url,
  confirmed_context, objective, language, kind (`connection` or `message`). The
  standalone draft, kept and still tested; the campaign form is the path the UI
  offers, because only a campaign brings a Strategist and an audience with it.
- `POST /api/campaigns` accepts `channel` (recipient_name, recipient_url,
  confirmed_context, language, kind) to deliver one LinkedIn message instead of
  emails. Stored on `campaign.channel`; migration `b1d7c9f4a20e`, which also
  widens `generatedasset.asset_type` for the new `linkedin_message` type.
- `GET /api/market/{brand_id}/linkedin/runs`: latest 50 jobs and results.
- `GET /api/linkedin/runs`: latest 20 jobs visible to the current account.

All routes enforce brand ownership. Only HTTPS LinkedIn `/in/` and `/company/`
URLs are accepted as destinations, with tracking parameters removed. A database
unique constraint allows one active LinkedIn job per brand, including concurrent
HTTP requests. Results, errors and usage survive reloads; local server restart
marks unfinished jobs failed and releases their lock. Work is bounded to ten
minutes and failures can be retried by explicitly launching a new job.

Migrations: `e8c4f6a25d03`, then `b1d7c9f4a20e`, after `d7b3e5f14c92`. Run
Alembic upgrade head for a migration-managed database. The existing development
create_all startup creates the new table, but never the new *column*: a
development database that has run before needs the upgrade, or the first page
load fails on `no such column: campaign.channel`. Do not stamp an unversioned
database before checking its actual schema; see the repository's development
migration guidance.

For AWS, see [deployment.md](deployment.md). Removing streaming does not make the
in-process background runner durable or safe to execute after a Lambda response.
No infrastructure is deployed by this change.
