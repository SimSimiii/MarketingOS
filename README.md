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

**Copy is only as specific as what was gathered before it.** Adding "your website" means
crawling it, not fetching the home page, because the home page is the page most carefully
written to say nothing checkable. What comes back is compiled once into six small
artifacts — what the business is, what it sells, what can be proven, how it sounds, who
buys, and what is still missing — which are then inlined into prompts in full. They belong
to the business rather than the campaign, so a second campaign starts from everything the
first one learned.

**Claims are checked, not trusted.** Every fact the compiler records carries the verbatim
source text that supports it, and a deterministic gate reads every finished draft back:
every number, price, quotation and URL must be licensed by that inventory or by the user's
own material. "Never invent a statistic" stops being an instruction in a prompt and
becomes a property of the output. The compiler is held to the same rule — an entry whose
quote is not really in the source is discarded before it can poison anything downstream.

The same inventory decides what the campaign can *argue*, before it is planned. A business
with no named customer, no quote and no attributed outcome cannot run an outcome-led
campaign, and no rewrite has ever added a proof the material did not contain — so the
Strategist is told which angles are actually open to it (mechanism, a checkable specific, an
invitation to test, the objection named precisely) rather than being left to plan one that
can only be hedged or invented. The user is told the one thing they could send that would
change the answer.

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
