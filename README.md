# MarketingOS

**Email campaigns without hiring a copywriter.** You point it at your website, upload a
PDF or a screenshot, and ask for what you need in your own words:

> *"Create a five-email onboarding campaign for my SaaS."*

MarketingOS reads your material into a set of facts it is allowed to claim, decides what
the campaign says and in what order, writes each email, has every draft read by someone
who knows nothing about your product, rewrites what did not land, and hands you finished
text you can copy and paste. Not drafts. Not a chatbot. Not a workflow builder.

The mission is narrow on purpose: email copy that beats what an experienced professional
would write. Other channels come later, and the parts that generalize — knowing the
business, deciding the strategy — are already channel-agnostic.

## Stack

- **Backend**: Python 3.12+ / FastAPI / SQLModel / SQLite / Alembic / Pydantic v2 — see
  [backend/README.md](backend/README.md)
- **Frontend**: Next.js (App Router) / TypeScript / Tailwind / shadcn/ui — see
  [frontend/README.md](frontend/README.md)
- **AI**: vendor-agnostic `AIProvider` interface; only Claude is implemented today

## Quick start

```bash
# Terminal 1 — backend
cd backend
python -m venv .venv && .venv/Scripts/activate
pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload   # http://localhost:8000

# Terminal 2 — frontend
cd frontend
npm install
cp .env.local.example .env.local
npm run dev                     # http://localhost:3000
```

Image ingestion also needs the `tesseract` binary on PATH for OCR; without it, screenshots
are still described by the vision provider but no text is extracted.

## Measuring quality

Two instruments, answering two different questions. Both live in
`backend/app/evaluation/` and both are run from `backend/`.

**Anything that calls a model spends real quota** — the CLI runs against your Claude
subscription, not an API key. The free commands below are the ones to reach for first, and
every billed command prints its cost estimate before it starts.

### Free

```bash
# Everything deterministic: gates, parsing, the loop's arithmetic, both harnesses.
.venv/Scripts/python.exe -m pytest tests/marketing tests/runtime tests/knowledge tests/ai -q

# The mutated emails the judge bench would use, printed for you to read.
# This is the check the bench itself rests on: a mutant has to be a plausible
# *worse* email, never a corrupted one, and only a human eye can tell.
.venv/Scripts/python.exe -m app.evaluation.judge_bench --dry-run

# Two previous benchmark rounds, side by side. Reads the JSON, calls nothing.
.venv/Scripts/python.exe -m app.evaluation.runner --compare eval/before eval/after
```

`tests/api` used to be left out here: it ran on an in-memory SQLite `StaticPool`, which hands
every session in the process the *same* connection — and these tests always have two live at
once, the request thread and the background campaign task. Two sessions interleaving
`commit()` and `rollback()` on one connection is one transaction, so whichever lost the race
came back as `Could not refresh instance`. It is a file-backed database now and it belongs in
the command above:

```bash
.venv/Scripts/python.exe -m pytest tests -q
```

### Billed — can the judges tell good from bad?

The craft loop is decided end to end by judgment: a cold reader scores every draft, a
preference judge decides which version ships. Nothing else in the system notes *those*, so
if they cannot separate a specific email from a vague one, every number downstream is a
number about nothing. The bench answers it without needing a single user, by pairing each
hand-written control email against a copy with one principle deliberately broken — the
original must win, by construction.

```bash
# The whole bench: 33 pairs, ~132 calls.
.venv/Scripts/python.exe -m app.evaluation.judge_bench --out eval/judges.txt

# Cheaper slices — one case (~44 calls), or one mutation.
.venv/Scripts/python.exe -m app.evaluation.judge_bench --case rich-single
.venv/Scripts/python.exe -m app.evaluation.judge_bench --mutation strip_the_proof --votes 2

# Also score both sides with the blind reader — one extra call per pair (~168).
.venv/Scripts/python.exe -m app.evaluation.judge_bench --with-reader
```

Read the **judgment-only** rate: the share of damage no regular expression could have
caught. The gate-visible rows bench the gates, and the invariance rows are the control arm
— an undamaged pair should come back near even, and a lopsided result there discounts
every detection scored above it.

### Billed — is the copy any good?

The golden set runs whole campaigns end to end and, where a case has one, puts the first
email in a blind duel against an email a person wrote from the same material. That control
is the only measurement in the project with a referent outside the system.

```bash
# A full round. Add --case <name> to run one.
.venv/Scripts/python.exe -m app.evaluation.runner --preset balanced --out eval/after

# Then compare it against a round taken before your change (free).
.venv/Scripts/python.exe -m app.evaluation.runner --compare eval/before eval/after
```

Read `win rate vs human` first — it is the only line that says whether the output is good
rather than whether it moved — then `cost/shipped email`, which is the one metric that gets
worse if either quality or spend does.

Then read `proof on the page`: the share of emails that actually spent the evidence they were
built on, checked in code against the material rather than by asking another model. It is the
one line here a drifting judge cannot move, and it measures whether the most expensive half of
the architecture — crawling, compiling, verifying quotes, assigning evidence per email — is
reaching the copy at all.

A self-contained brief for handing this system to an outside reviewer — architecture,
constraints, what has already been rejected, and the open problem — is in
[docs/external-review-brief.md](docs/external-review-brief.md).

## Architecture decisions

**The user's request is the contract.** `Campaign.request` holds what the user asked for,
in their own words, and it is rendered verbatim at the top of every prompt in the run.
The part of it that is arithmetic — "five emails" — is parsed in code before anything
runs and checked against what was delivered, because how many emails to write has a
correct answer and is not a matter of judgment.

**Nothing spends a model call deciding what happens next.** For a single channel the
order of work is fixed by data dependencies: you cannot write to a reader you have not
defined, from evidence you have not gathered. So the pipeline
(backend/app/marketing/pipeline.py) is a state machine, and every model call in a run
either distills knowledge, decides strategy, writes copy, or judges copy. Routing,
retries, thresholds and budgets are code — deterministic, free, and incapable of
returning an invalid answer.

That has a consequence worth cashing in: **what a run will cost is arithmetic, so it is
shown before it is bought.** The number of model calls follows from the preset and from the
email count parsed out of the request, and the campaign page prints the range — the low end
is the run where every email lands first time, the high end buys every rewrite it is allowed.
Beside it sits what a delivered email has actually cost across the user's own finished runs
on that preset, which is a measurement rather than a price list, and the two are deliberately
not multiplied together. The estimator is checked against real runs in
`backend/tests/marketing/test_forecast.py`: the suite executes the pipeline at every preset,
counts the calls it made, and asserts the forecast contained them. If the loop gains a step
and the arithmetic does not, that test fails.

**Copy is only as specific as what was gathered before it.** Adding "your website" means
crawling it, not fetching the home page, because the home page is the page most carefully
written to say nothing checkable. What comes back is compiled once into six small
artifacts — what the business is, what it sells, what can be proven, how it sounds, who
buys, and what is still missing — which are then inlined into prompts in full. They belong
to the business rather than the campaign, so a second campaign starts from everything the
first one learned.

Everything the user gave us is read, and read once. A document longer than one extraction
call used to be *truncated* to it, so anything past 14,000 characters never reached a model
on any code path — which is the "all or nothing" failure retrieval exists to remove, still
living in the one pass whose entire product is the facts the copy may claim, and biting
hardest on the long pricing table and the customers page with eight case studies. Long
documents are now read in several passes, bounded overall, and whatever a bound does cut off
is reported instead of vanishing. The three passes that only read the material — what the
business is, what can be proven, how it sounds — are three independent questions about the
same pages, so they are asked at once rather than one at a time; only the audience pass has
real inputs and waits for them.

**Claims are checked, not trusted.** Every fact the compiler records carries the verbatim
source text that supports it, and a deterministic gate reads every finished draft back:
every number, price, quotation and URL must be licensed by that inventory or by the user's
own material. "Never invent a statistic" stops being an instruction in a prompt and
becomes a property of the output. The compiler is held to the same rule — an entry whose
quote is not really in the source is discarded before it can poison anything downstream.

Both of those comparisons are typography-blind, and that was not cosmetic. Every published
page has been through a CMS that made its apostrophes curly and its ranges en dashes, and a
model asked to quote one back answers in plain ASCII about half the time. Under an exact
substring test those are different strings: a correctly quoted testimonial was silently
*dropped* by the compiler, and a correctly quoted testimonial in a draft was *blocked* by the
gate — over one character, on the one kind of evidence the preflight will stop a whole run
for the lack of.

The same inventory decides what the campaign can *argue*, before it is planned. A business
with no named customer, no quote and no attributed outcome cannot run an outcome-led
campaign, and no rewrite has ever added a proof the material did not contain — so the
Strategist is told which angles are actually open to it (mechanism, a checkable specific, an
invitation to test, the objection named precisely) rather than being left to plan one that
can only be hedged or invented. The user is told the one thing they could send that would
change the answer.

**And the same check points both ways.** The evidence gate stops the copy claiming more than
the material supports; nothing used to notice copy that supported *nothing*. An email could
pass every check, spend none of the facts the Strategist assigned it, and ship — and getting
those facts onto the page is what the crawl, the ledger, the quote verification and the
per-email evidence assignment are all *for*. That gap was measured rather than assumed: on the
judge bench, an email with its whole proof paragraph deleted (nothing invented, no gate
tripped) took half the votes against the original. The instrument that decides what ships
could not see the one thing the system exists to put there.

So whether the figure, the name or the quotation reached the page is now checked in code, for
nothing, on every draft — see `backend/app/marketing/substantiation.py`. It is advisory to the
writer, because a business with no proof is written from mechanism on purpose and blocking
would fail exactly the emails that were right to be written that way. It is *not* advisory to
the loop: a rewrite that carries strictly less of what the email was built on does not take the
title, whatever the readers vote, because losing the evidence is not a matter of taste. The
receipt says which emails argue from nothing, and `proof on the page` is a benchmark line that
no drifting judge can move.

**A role exists when its ignorance is load-bearing.** The Blind Reader is never shown the
request, the brief or the product docs, and that is the entire mechanism: ask a model that
has read the brief what an email is selling and it answers from the brief. What it must be
told is *who it is* — the segment the Strategist chose to write to, not whichever segment
the compiler happened to list first. Copy aimed at a founder with no engineer, graded by a
director with a platform team, fails on a premise the grader does not have, and every
rewrite after that answers the wrong person's doubts. The Conversion
Critic gets everything the reader does not, but a fresh context — which is why it can see
an email that reads beautifully and argues the wrong thing. Roles are not split by job
title; four "analysis agents" that each saw a fragment of the same material are one
Strategist now.

**Quality is a loop with a floor, not a gate at the end.** Each email starts as several
different openings, not one: they are screened by the free checks and one cold read, and
only the one a stranger responded to earns the critic and the rewrites. Refinement alone
cannot do that job — it walks a single draft toward the middle of the register it started
in, answering each reader's last objection by removing whatever made the copy specific,
which is how a rewrite comes back with the same subject line and a flatter body. Which
argument lands is not derivable from the brief, so it is decided by asking. From there the
winner is rewritten up to a bounded number of times, and a rewrite is kept only if it
actually scored better. Only the deterministic checks can block; taste never blocks, or a
run spends its budget arguing with a model about a sentence.

**A number nobody gave is not a score.** The floor is real: a campaign whose copy a cold
reader said they would not click is reported as degraded, with the positions named, because
a run that ends out of rewrites has not succeeded and saying otherwise teaches the user that
the headline number means nothing. A cold read that fails to come back is recorded as no
verdict rather than as a passing one — it neither blocks the draft nor averages into the
result.

**Deliverables are text, not JSON.** The writer emits an email the way an email is
written — a subject line, a greeting, paragraphs with blank lines between them — inside a
small labelled-field envelope that is parsed and structurally validated. A five-email
sequence becomes five separate deliverables the user copies one at a time.

Two of those structural rules are about layout and nothing else — a paragraph wider than 50
words, a body in fewer than three blocks — and failing one bought a whole deep-tier writer
call to move a blank line, at which point the model rewrote the words too and the draft had
to be read cold again. The only repair this project ever recorded was exactly that ("block 3
is 56 words in one paragraph"). Splitting at a sentence boundary *is* that repair, so it
happens in code now, for nothing, changing not one word. Bullets are never touched, a
paragraph already inside the width keeps its own soft line breaks, and a single sentence over
the limit is still sent back — shortening it means changing words, and that is the writer's
job.

**A run narrates itself.** A campaign takes minutes, most of them inside single model
calls, so every notable moment goes through one funnel that both persists an
`ExecutionLog` row and publishes the identical payload to the live SSE stream. Persisting
and broadcasting together is what makes the watching page and the replayed history agree
by construction. The unit shown is one role turn — writing email 2 a second time is its
own row, because the rework loop is what the user is paying for.

**Degrade, never deadlock.** Budgets, deadlines and cancellation are checked between
steps, never mid-call, so a stopped run leaves a consistent, fully persisted state. A run
that ran out of time after three of five emails hands over the three, says so, and
reports what it could not finish.

The provider counts as a guard too, and that is the newer half. Every call is a CLI
subprocess spawn; a spawn that loses a race fails before a single token is consumed, and one
unlucky spawn out of the tens a campaign makes used to end the run — past the craft loop,
past the pipeline (a `ProviderError` is not a `CampaignError`), into the orchestrator's crash
handler, which persists no report and no deliverables. So a call that never landed is resent
(cheap: a failed call consumed nothing) and announced when it is; a cold reader or a duel vote
that still cannot answer is recorded as no verdict, which the panel arithmetic already handles;
and a provider that has genuinely stopped answering stops the run the way a deadline does,
keeping every email already written. A failure that arrives with finished emails behind it is
`degraded`, never `failed` — a red badge over two good emails is what teaches a user to
distrust the badge on the runs that really did fail.

**Persistence is an adapter, not the orchestrator.** `CampaignOrchestrator`
(backend/app/orchestration/campaign_orchestrator.py) makes no decisions: it hands the
request and the business's knowledge to the pipeline, watches it through an observer, and
persists every role turn, deliverable and log line.

**AI provider is abstracted, only Claude exists.** `AIProvider` (backend/app/ai/base.py)
exposes `generate`/`stream`/`count_tokens` with vendor-agnostic types, and every call in
the system goes through one `ModelSession` — the single place that renders prompts from
disk, types vendor failures, counts tokens and announces progress. Roles ask for a model
*tier* (fast / balanced / deep), never a model name, so a new model generation moves one
mapping instead of every role.
