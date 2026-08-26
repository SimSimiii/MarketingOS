# Brief for an external reviewer

A self-contained prompt for a strong reasoning model (Gemini Pro, o-series, or similar)
with web access. It carries enough architecture, constraints and measured data that the
reviewer can propose something real instead of generic advice.

Paste everything below the line. Add "Answer in French" at the end if you want.

---

You are a systems architect and a direct-response marketing sceptic. I want you to think
hard about a working system I have built, research anything you need, and propose ways to
make its output measurably better. I am explicitly asking for out-of-the-box thinking:
challenge the premises, not just the parameters. Disagreeing with the design is welcome as
long as the disagreement names a mechanism.

## What the system is

**MarketingOS** turns "write me a five-email onboarding campaign for my SaaS" into finished,
send-ready email copy. Not drafts, not a chatbot, not a workflow builder. The mission is
narrow on purpose: **email copy that beats what an experienced human copywriter would
write.** Python/FastAPI backend, Next.js frontend, solo developer, all LLM calls go to
Claude models through one abstraction layer.

## How it works

**1. Knowledge compilation (once per business, reused by every campaign).** Crawls the
user's site and reads uploaded documents into six artifacts: what the business is, what it
sells (an "offer sheet" listing the only actions a reader may be asked to take), an
**evidence ledger**, a voice profile learned from copy the company actually published, an
audience model (buyer segments with situation, job-to-be-done, trigger, sophistication,
plus their objections), and a report of what is missing.

Every entry in the evidence ledger carries the verbatim source sentence supporting it, and
**code verifies that quote really appears in the source** before the entry is kept. An
entry whose quote cannot be found is discarded. Same for voice exemplars.

**2. Strategy (one deep model call).** Produces a campaign brief and, per email, a brief
naming: the one idea it argues, 2-3 *alternative* claims that slot could have argued
instead, the belief shift it should cause, which evidence ids it may spend, the objection
it must answer, what it must deliberately **not** say, the tone, and the call to action.

**3. The craft loop (per email).** Several candidates are drafted in parallel — each
arguing a *different claim* on a *different opening move*, not the same claim reworded.
Then:

- **Deterministic gates** run free on every draft: unfilled placeholders, stock phrases,
  spam vocabulary, structural rules (subject length, paragraph width, body length), overlap
  with earlier emails in the sequence, and an **evidence gate** — every number, price,
  quotation and URL in the copy must be licensed by the ledger or the user's own material.
  "Never invent a statistic" is not an instruction in a prompt; it is a property of the
  output, checked on every draft. A blocking gate is a **deterministic veto**: a draft that
  trips one loses to any clean draft regardless of how well it reads.
- **A blind reader** reads the draft cold. It is never shown the request, the brief, the
  positioning or the product docs — that ignorance is the entire mechanism, because a model
  that has read the brief answers "what is this selling?" from the brief. It reports what it
  did with the email, plus two frequency estimates: how many of a hundred people like it
  would open, and how many would click. A code table maps clicks to a 0-10 score.
- **A conversion critic** sees everything the reader does not, but in a fresh context, so it
  can spot an email that reads beautifully and argues the wrong thing. Capped at three edits
  per rewrite pass.
- **A preference judge** decides which version is kept, as a forced choice between two
  concrete emails rather than a comparison of two scores. The ballot alternates which email
  wears which label to cancel position bias. **The incumbent wins ties.**
- When rewriting stops improving the copy, the loop **pivots to a different claim** from the
  brief's alternatives rather than buying a fourth phrasing of a bet already measured twice.

**4. Subject lines** are optimised last, separately: several alternatives are written, then
scored by a model shown them as a list in an inbox — no bodies — which is the decision a
real recipient actually makes. The incumbent line competes.

**5. A sequence pass** reads the finished set in order and judges escalation, promise
consistency, and whether each email stands alone.

## Design principles the codebase holds

- **Anything with a correct answer is code, never a prompt.** Routing, retries, thresholds,
  budgets, counts, arithmetic, quote verification.
- **A role exists only when its ignorance or independence is load-bearing**, never because
  an org chart has that job title.
- **Comparison, not absolute scoring.** Asking a model to rate copy 0-10 produces answers
  that saturate and drift; asking it to choose between two concrete things produces a number
  that moves.
- **Only deterministic checks may block.** Taste never blocks, or a run spends its budget
  arguing with a model about a sentence.

## Hard constraints — read these before proposing anything

1. **There are no users, no customers, and no real send data.** No open rates, no click
   rates, nothing. I will not build something that trains or calibrates on a single user
   (me). Any proposal whose first step is "collect telemetry from your users" is dead on
   arrival. Assume this stays true for the next six months.
2. **Every model call costs real quota** from a personal subscription. Cost is felt
   directly. A proposal that triples spend must say what it buys.
3. **Solo developer.** Implementation effort is the scarcest resource after quota.
4. No fine-tuning budget; assume frontier models via API only.

## Things already tried and deliberately rejected — do not re-propose these

- Splitting research/audience/competitor/strategy across four "agents": produced four
  shallow artifacts. Merged into one act of synthesis with everything in front of it.
- Absolute 0-10 quality scores from a model: saturated so badly that a rewrite changing
  everything and one changing nothing came back level. Replaced by frequency estimates and
  pairwise choices.
- A refine-only loop: it walks a single draft toward the middle of its register, answering
  each objection by deleting whatever made the copy specific. Replaced by drafting several
  genuinely different arguments and letting a cold reader choose.
- A model deciding what step runs next: for one channel the order is fixed by data
  dependencies, so orchestration is a plain state machine.
- Emitting emails as JSON: whitespace is the copy, and it did not survive. Emails are
  emitted as text in a small labelled-field envelope.

## The measured problem I want help with

Everything above is decided by **simulated judgment**. Nothing in the system was ever
graded against reality, because there is no reality to grade against yet.

So I built a bench that grades the judges without needing users: take a hand-written
control email known to be good, break one principle in a way whose direction nobody would
dispute (replace the checkable number with an adjective, remove the proof paragraph, hedge
the claims, bury the ask, open on the company instead of the reader), and the pair is
**labelled by construction** — the original must win. Ties count as misses. There is a
control arm: an email duelled against *itself*, which should come back an even split.

First real run, on one control email, four votes per pair:

- The judge correctly preferred the original on 4 of 6 degradations that no regular
  expression could have caught.
- It **failed to notice that the entire proof paragraph had been deleted** (2-2).
- Control arm was clean: identical emails came back 2-2, so the judge is genuinely reading
  the copy rather than favouring a position.

That miss matters more than the number suggests: the whole architecture — quote
verification, the evidence ledger, the evidence gate, per-email evidence assignment —
exists to get proof onto the page, and the instrument that decides which draft ships cannot
see whether the proof is there. The system optimises for something adjacent to what it was
built to do.

**What has since been done about it, so you do not re-propose it.** The specific miss is now
answered in code rather than by a better judge. Whether an assigned fact reached the page is a
string comparison — its figure, the name it introduces, or a passage from its verbatim — so it
is checked free on every draft (`backend/app/marketing/substantiation.py`). Against the golden
control emails this catches both mutations that *remove* evidence (`strip_the_proof`,
`specifics_to_adjectives`) with a clean control arm, and deliberately catches none of the four
that only damage the argument (`hedge_the_claims`, `bury_the_ask`, `open_on_the_company`,
`clickbait_subject`) — those are still the judges' job and still unmeasured beyond one bench
round. It feeds three places: an advisory line to the writer, a tiebreak in the bake-off below
pull, and one hard rule — a rewrite carrying strictly less of what the email was built on does
not take the title however the ballot votes.

So the remaining question is narrower and harder than the one above. **The judges are still the
only instrument for everything that is not a missing string** — whether the argument is the
right one, whether the ask is reachable, whether the opening is about the reader. Code cannot
see any of that, one bench round is one bench round, and a measure that fires on the cheap half
may simply have moved where the optimisation pressure leaks out. Argue about *that*.

## What I want from you

Think from first principles. Research whatever helps — LLM-as-judge calibration,
metamorphic and property-based testing, psychometrics and item response theory, the direct
response marketing literature, information-theoretic views of evaluation, whatever you find
relevant. Say when you are drawing on something specific.

Give me a **ranked shortlist of 3-6 proposals**. For each one:

- **The mechanism.** Why it would make the *output* better, traced through the system.
  Not "this is best practice" — what specifically changes and why that changes the copy.
- **What it costs**: model calls, implementation effort, added complexity.
- **How I would know it worked.** What measurement, available to me *today with no users*,
  would move? If nothing would, say so plainly — that is important information.
- **What could go wrong**, and what assumption you could not verify.

Some starting provocations — treat them as directions, not a menu, and ignore any you find
uninteresting:

- Is "simulate a reader" the ceiling of what can be done without real data, or is there a
  fundamentally better grounding available offline?
- The system optimises for a click nobody ever measures. Is there a proxy for persuasive
  quality that is genuinely measurable offline and not merely another model's opinion?
- Where else in this design is a model being asked a question it is measurably bad at, that
  code or a different question could answer instead?
- What is the highest-value thing this architecture is *not* doing at all?
- If you think the real bottleneck is somewhere I have not looked — distribution, the
  knowledge compilation, the product framing itself — say that instead and argue it.

Be concrete and be willing to tell me something is a bad idea. Generic advice ("add
caching", "use RAG", "add more agents", "fine-tune a model") is worse than nothing here.
