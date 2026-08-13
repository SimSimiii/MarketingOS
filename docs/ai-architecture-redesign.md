cl# MarketingOS — AI Architecture Redesign (Email Campaigns First)

*Prepared 2026-08-05. Based on a full inspection of `backend/app/` (director, all ten
specialists, prompts, runtime, ingestion, orchestration, provider, persistence) and both
READMEs. No code was modified.*

---

## 1. Executive Summary

The current system is a decision-based multi-agent architecture: an LLM Marketing Director
dispatches ten specialists until a reviewer approves the copy. It is well-engineered at the
code level — clean layering, typed everything, excellent observability — but it is
architected for the product MarketingOS says it is not (a general marketing agent platform),
and its intelligence is distributed to the wrong places.

The redesign rests on four findings:

1. **The LLM Director solves a routing problem that does not exist.** For email campaigns
   the correct sequence is fixed by data dependencies, and the director's own prompt already
   hardcodes it. An LLM interpreting an if-statement adds cost, latency, and a failure mode
   (invalid decisions) the codebase carries dedicated machinery to survive.

2. **The system cannot research, so its "research" is confabulation.** The provider runs
   with `allowed_tools=[]`; the website loader fetches a single page; the research,
   audience, and competitor agents are Haiku calls that emit lists of strings derived from
   the same 24KB of truncated text everyone else sees. Elite copy is made of specifics, and
   the architecture has no way to acquire them.

3. **The knowledge pipeline ends in a truncated paste.** Loaders, cleaners, and chunkers
   exist, but chunks are discarded on persist and "retrieval" is newest-first truncation at
   4,000 characters per document. Raw website markdown is re-read by every model call.
   Nothing is distilled, nothing persists across campaigns, nothing carries provenance.

4. **The best architecture in the repo is hiding inside one agent.** `EmailAgent`'s
   internal protocol — plan the sequence, draft one email per call, hand it to a blind
   reader who has never seen the brief, rewrite only when it didn't land, keep the better
   version — is the correct core loop for the entire product. It is currently a private
   implementation detail of one specialist.

**The proposal:** invert the architecture. Replace the LLM director with a code-orchestrated
three-phase pipeline (Knowledge Compilation → Campaign Strategy → Craft Loop), collapse the
four analysis agents into one deep Strategist, promote the email agent's draft/read/critique
loop to the system's core, and build a real knowledge layer: acquisition tools that gather
deep source material, and a compiler that distills it into structured, citable artifacts —
including an Evidence Ledger that makes hallucinated claims structurally impossible rather
than merely discouraged. Five reasoning roles instead of ten agents; every LLM call either
produces copy, judges copy, or distills knowledge — never routes.

---

## 2. Analysis of the Current Architecture

### What exists

- **Orchestration** — `MarketingDirector` (`app/marketing/director.py`): a loop of up to
  `max_steps` LLM calls, each producing a typed `DirectorDecision`
  (`run_agent | complete | abort`). Guards: per-agent run caps, wall-clock deadline, token
  budget, consecutive-invalid-decision limit. Completion is validated in code: deliverables
  must exist, mechanical gates must pass, and the reviewer must have approved (or exhausted
  its run budget).

- **Specialists** — ten agents in `app/marketing/agents/`, executed through a generic
  `AgentRuntime` (`app/runtime/`): typed input/output Pydantic models, prompt templates in
  `prompts/`, JSON-only responses (except the email writer's labelled-field format). Four
  analysis agents (research, audience, competitor, strategy), five asset agents (email,
  blog, social, ads, landing page), one reviewer.

- **The email agent** — the outlier in sophistication: a planning call fixes the sequence
  (position, role, angle, proof, ask per email), each email is drafted in its own call, a
  *blind reader* (separate prompt, deliberately deprived of the brief, the product docs,
  and the intent) reports what happened when a cold reader met the draft, and a rewrite is
  kept only if it out-scores the original. A labelled-field envelope
  (`SUBJECT:/PREVIEW:/BODY:` …) replaces JSON for copy, parsed and structurally validated
  in `email_copy.py` (subject length, paragraph widths, body word counts).

- **Quality** — two layers: deterministic gates (`quality_gates.py`: placeholder patterns,
  banned stock phrases) that block completion for free, and an Opus `ReviewAgent` scoring
  conversion 0–10 against a threshold, with rejection feedback routed back into the
  writer's next prompt.

- **Knowledge** — `app/ingestion/`: loaders (single-page website → markdown, PDF, DOCX,
  markdown, JSON, text, images via Claude Vision + Tesseract OCR), normalizer, cleaner
  chain, heading/fixed-size chunkers, an in-memory `KnowledgeStore`. Persistence is a
  separate SQL `KnowledgeDocument` table storing full text; the in-memory store is a
  per-request "outbox". At campaign time, `CampaignOrchestrator._knowledge_summaries()`
  takes documents newest-first, truncates each at 4,000 chars, caps the total at 24,000,
  and injects the result into the director's and every specialist's prompt.

- **Infrastructure** — vendor-agnostic `AIProvider` (implemented via the Claude Code CLI,
  subscription-billed, **no tools enabled**), `ModelRouter` with per-agent defaults and
  overrides, `ExecutionPolicy` presets (fast/balanced/maximum), and a genuinely good
  observability spine: every notable moment goes through one funnel that both persists an
  `ExecutionLog` row and publishes to a resumable SSE stream.

### What is actually good (keep these)

- The email agent's inner protocol, especially the blind reader's *engineered ignorance*.
- The labelled-field copy format and its deterministic structural validation.
- Mechanical gates as a free pre-filter before LLM judgment.
- "The user's request is the contract" — the request rendered verbatim at the top of every
  prompt.
- The observability spine (persist + broadcast in one call; resumable timeline).
- The `AIProvider` seam, model routing per role, policy presets, budget/deadline guards.
- Campaign-scoped knowledge with a null-scoped shared library.

---

## 3. Weaknesses of the Current Design

### 3.1 The Director is an expensive interpreter of a fixed policy

The director's prompt (`prompts/director.md`) instructs it: run analysis first ("at minimum
strategy… for email, run audience too"), then write, then review, then rework on rejection,
then complete. That *is* the pipeline. The LLM's only genuine degrees of freedom are which
analysis agents to skip and when to retry — decisions a dozen lines of code make
deterministically, better, for free.

The cost is not just the extra Sonnet call per step (8–25 steps per run). It is that a
stochastic component sits where a deterministic one belongs, and the codebase visibly pays
for it: `_MAX_CONSECUTIVE_INVALID_DECISIONS`, `_DECISION_ATTEMPTS`, JSON repair turns,
`decision_errors` fed back into the next prompt, validation that the director didn't pick a
capped agent or complete without deliverables. That is scar tissue around a self-inflicted
wound.

Decisive detail: the director cannot even *instruct* a specialist. `build_input(state)` is
fixed per agent — the director's only levers are order and repetition. An orchestrator that
cannot parameterize its workers is not orchestrating; it is scheduling a DAG whose edges
are already hardcoded in the agents' `build_input` dependencies.

### 3.2 The analysis layer manufactures generic insight

`ResearchAgent`, `AudienceAgent`, `CompetitorAgent` are single Haiku calls over the same
truncated excerpts, emitting `list[str]`. They have no web search, no crawler, no data the
writer doesn't already have. The competitor agent "maps rivals" from the user's own
marketing material. The audience agent invents personas with no grounding and no marker
distinguishing knowledge from guess. Their outputs reach the writer flattened into
pipe-joined lines (`personas | join(" | ")`).

This layer exists because "a marketing team has researchers" — an org-chart metaphor, not
an information-flow argument. Worse, it *dilutes*: strategy is the synthesis of audience +
market + competition + product, and splitting that one act of judgment across four
sequential cheap calls, each seeing only fragments, produces four shallow artifacts instead
of one deep one. Haiku for "audience psychology" is a mispricing of where quality comes
from: audience insight is *the* hard judgment in copywriting.

### 3.3 The knowledge system does not deliver knowledge

- Chunks are computed, then thrown away (`KnowledgeService._persist` stores whole text).
- Retrieval = newest-first truncation. A pricing table on the second half of a long page
  never reaches any model, ever.
- No distillation: every model call re-reads raw site markdown; nothing is ever *learned*
  — a second campaign for the same product starts from zero.
- No provenance: the writer is told "never invent a statistic" but the system gives it no
  verifiable inventory of true statistics, and no check ties a claim in a draft back to a
  source. The anti-hallucination strategy is a prompt admonition.
- Two knowledge stores (in-memory pipeline outbox + SQL table) with different schemas and
  an interface (`KnowledgeStore.search`) nothing calls in the campaign path; likewise
  `KnowledgeAccess.query` is static and unused, and the runtime `Memory` blackboard is
  written but never read for any decision.

### 3.4 Quality machinery is duplicated and coarse

Two review loops half-overlap: the email agent's internal blind reader (per-email,
behavioral, excellent) and the outer `ReviewAgent` (whole-campaign JSON digest truncated at
12,000 chars, rubric-based, redundant with the gates for placeholder checks). Review
feedback flows back as a raw JSON string stuffed into `review_feedback`. The reviewer
scores a digest of *typed outputs*, not the rendered deliverables the user will copy.

### 3.5 The platform taxes the product

Five channels (email, blog, social, ads, landing) each carry an agent, a prompt, and
registry weight — but blog/social/ads/landing are single-call JSON writers with none of the
email agent's craft. They exist to justify the director's "decision-based" generality while
the stated mission is email-first excellence. Meanwhile the generic runtime (BaseAgent,
Memory, KnowledgeAccess, per-agent versions) is abstraction built for a marketplace of
agents that the product vision explicitly rejects.

### 3.6 Missing concepts

- Deep source acquisition (multi-page crawl, web search, competitor fetching).
- Structured, persistent, citable knowledge (profiles, voice, evidence).
- Voice learning from the user's existing emails (few-shot exemplars beat adjectives).
- A campaign brief the user can approve/edit before writing burns budget.
- Sequence-level quality checks (cross-email phrase/angle repetition is prompted against
  but never verified; a deterministic n-gram check is trivial and absent).
- Deliverability screening (spam-trigger vocabulary, image-less plain-text norms).
- Merge-field policy: "never a placeholder" also bans `{{first_name}}` — real ESP
  personalization is impossible by design. This should be a per-user vocabulary, not a ban.
- An evaluation harness. "Rivals elite copywriters" is a measurable claim; nothing
  measures it.

---

## 4. Design Philosophy

1. **Intelligence at the work, code at the seams.** Every LLM call must do one of three
   things: distill knowledge, decide strategy, or produce/judge copy. Routing, retries,
   thresholds, and sequencing are code. An LLM decision is only warranted where the output
   space is open-ended.

2. **Agent boundaries are information boundaries.** The reason to split two reasoning
   roles is that one must *not know* what the other knows (the blind reader), or must not
   share its context bias (the critic), or needs a different context budget (the
   compiler). Never split by job title. The current system splits by job title.

3. **Specificity is upstream of craft.** The ceiling on copy quality is set by the
   evidence available before writing begins. Acquisition and distillation are therefore
   first-class phases, not preprocessing.

4. **Claims must be checkable, not just discouraged.** Every factual claim in a draft must
   trace to an Evidence Ledger entry with provenance. Verification is a gate, not a hope.

5. **Artifacts over messages.** Phases communicate only through typed, persisted,
   versioned artifacts. No shared mutable memory, no agent-to-agent chatter. An artifact
   is inspectable, editable by the user, and replayable.

6. **Judge behavior, not compliance.** The blind reader's "would you click today?"
   outranks a rubric score. Keep rubric checks deterministic where possible and spend LLM
   judgment on simulated reception.

7. **Quality gates stay; degrade gracefully.** Budgets and caps bound every loop; when
   exhausted, ship the best draft with an honest report — never deadlock (the current
   system gets this right; keep it).

---

## 5. Proposed Architecture (Overview)

A fixed three-phase pipeline, orchestrated in code, each phase internally agentic:

```
                        ┌─────────────────────────────────────────────┐
 user sources ───────►  │ PHASE 0 · KNOWLEDGE COMPILATION             │
 (site, PDFs, images,   │ Acquisition tools → Source Corpus           │
  existing emails)      │ Knowledge Compiler → Knowledge Artifacts:   │
                        │   Business Profile · Offer Sheet ·          │
                        │   Evidence Ledger · Voice Profile ·         │
                        │   Audience Model · Gap Report               │
                        └───────────────────┬─────────────────────────┘
                                            │  (org-scoped, persistent,
                                            │   refreshed on new material)
 user request ──────►   ┌───────────────────▼─────────────────────────┐
 ("5-email onboarding   │ PHASE 1 · CAMPAIGN STRATEGY                 │
   campaign")           │ Strategist → Campaign Brief:                │
                        │   deliverable contract · reader definition ·│
                        │   sequence arc · per-email Email Briefs     │
                        │   [optional user checkpoint: approve/edit]  │
                        └───────────────────┬─────────────────────────┘
                                            │
                        ┌───────────────────▼─────────────────────────┐
                        │ PHASE 2 · CRAFT LOOP  (per email)           │
                        │  Writer → draft                             │
                        │  Deterministic gates (format, evidence,     │
                        │    spam, overlap)  — free, instant          │
                        │  Blind Reader → behavioral report           │
                        │  Conversion Critic → line-level edits       │
                        │  Writer → revision (≤2 cycles, keep best)   │
                        │ then: Sequence Pass (arc, variety, subjects)│
                        │ then: Contract Check → deliverables         │
                        └─────────────────────────────────────────────┘
```

Five reasoning roles: **Knowledge Compiler, Strategist, Email Writer, Blind Reader,
Conversion Critic.** Everything else is a tool or plain code.

---

## 6. Complete Component Descriptions

### 6.1 Knowledge Compiler *(agent)*

- **Why it exists:** the single highest-leverage change. Raw text is re-paid on every call
  and never gets smarter; distilled artifacts are paid once, persist, and improve every
  downstream prompt.
- **Mission:** turn the Source Corpus into the six Knowledge Artifacts (§10), every factual
  entry carrying provenance (source document id + supporting quote).
- **Inputs:** the Source Corpus (all ingested documents, chunked and retrievable); for
  refresh runs, the existing artifacts.
- **Outputs:** Business Profile, Offer Sheet, Evidence Ledger, Voice Profile, Audience
  Model, Gap Report.
- **Decides:** what is fact vs. inference (and labels it), which evidence is strong enough
  to enter the ledger, what is missing badly enough to ask the user for.
- **Cannot decide:** anything about a specific campaign; whether to proceed despite gaps
  (that is the user's/policy's call, surfaced via the Gap Report).
- **Tools:** crawler, web search, fetch, retrieval over the corpus. This is the *only*
  role with acquisition tools.
- **Model:** mid-tier (Sonnet-class) with a strong-model pass for the Audience Model,
  which is judgment, not extraction.
- **Communicates with:** nothing directly — writes artifacts; the pipeline invokes it on
  ingestion and on-demand refresh.

### 6.2 Strategist *(agent)*

- **Why it exists:** strategy is one act of synthesis. Splitting it (current
  research/audience/competitor/strategy chain) produced four shallow lists; merging the
  analysis into one strong-model deliberation over rich artifacts produces the single
  document that determines campaign quality.
- **Mission:** convert (request + Knowledge Artifacts) into a Campaign Brief good enough
  that a competent writer cannot miss.
- **Inputs:** the user's request verbatim, all Knowledge Artifacts, campaign parameters
  (audience segment, offer, constraints), past Campaign Reports for this org (what scored
  well before).
- **Outputs:** Campaign Brief containing the deliverable contract (exact count/type — the
  typed parse of "3 emails"), reader definition, campaign promise, sequence arc, and one
  Email Brief per email (job, single idea, evidence ids it will use, objection it answers,
  emotional register, CTA, subject strategy).
- **Decides:** interpretation of ambiguous requests (recorded explicitly in the brief);
  angle selection; sequence structure; which evidence each email spends. Two emails must
  not be able to swap angles — that invariant (already in the email agent's planning
  prompt) lives here now.
- **Cannot decide:** to write copy; to claim facts absent from the ledger; to change the
  deliverable contract once the user approves the brief.
- **Tools:** retrieval over corpus + ledger. No acquisition (gaps go to the Gap Report).
- **Model:** strongest available.
- **Communicates with:** Craft Loop via the Campaign Brief; optionally the user (approval
  checkpoint — the brief is a Markdown-renderable artifact a user can edit).

### 6.3 Email Writer *(agent)*

- **Why it exists:** producing the deliverable is irreducibly generative.
- **Mission:** one email per invocation, from one Email Brief, in the Voice Profile,
  citing only ledger evidence — send-ready in the labelled-field format.
- **Inputs:** Email Brief; Campaign Brief (arc context); Voice Profile with exemplars;
  the full text of previously accepted emails in the sequence (verbatim, as today — a
  digest would let it repeat lines it cannot see); on revision: the Blind Reader report
  and the Critic's edit list.
- **Outputs:** an Email draft (labelled-field envelope, parsed to the `Email` model).
- **Decides:** every word; how to execute the brief's angle.
- **Cannot decide:** the angle, the CTA intent, the count, or any factual claim not in the
  ledger (each claim is emitted with the evidence id it uses — see §8, evidence gate).
- **Tools:** ledger lookup only.
- **Model:** strongest available. Keep today's rule: one email per call — an email is the
  unit of attention.

### 6.4 Blind Reader *(agent — preserved, sharpened)*

- **Why it exists:** the only honest measurement of cold reception is a judge that cannot
  fill gaps from context. Its value is *engineered ignorance* — this is the clearest
  example of an agent boundary drawn on information asymmetry, and it is why this role can
  never be merged into the writer or critic.
- **Mission:** read one rendered email as the target person; report behavior.
- **Inputs:** the rendered email and a persona line derived from the Audience Model.
  Nothing else — no request, no product docs, no brief. (Unchanged from today's
  `email_reader.md`, which is excellent.)
- **Outputs:** BlindRead report — opened?, stopped_at, what_it_sells (in their words),
  biggest_doubt, would_act, pull 0–10, lines to cut.
- **Decides / cannot decide:** reports only; never proposes copy; its verdict is advisory
  input to the loop's deterministic accept/revise rule.
- **Tools:** none. **Model:** mid-tier; optionally 2–3 persona variants under the
  `maximum` policy (skeptic, economic buyer, distracted opener) with pull averaged.

### 6.5 Conversion Critic *(agent)*

- **Why it exists:** the reader says *what happened*; someone must decide *what to change*.
  A critic with the brief and the ledger — but a fresh context, not the writer's — catches
  brief drift, unspent evidence, unanswered objections, and voice violations the writer is
  blind to. It replaces the outer `ReviewAgent`, whose rubric was half-duplicated by gates
  and whose whole-campaign digest was too coarse to act on.
- **Mission:** per-email, line-level diagnosis and a targeted edit list.
- **Inputs:** the rendered email, its Email Brief, the Evidence Ledger, Voice Profile,
  the Blind Reader report, gate results.
- **Outputs:** Critique — pass/revise verdict, ranked edits (quote the line, name the
  problem, state the fix intent — not rewritten copy; the writer writes).
- **Decides:** whether the draft executes its brief; what the revision must fix.
- **Cannot decide:** to change the brief or the angle; to rewrite; to ship (the loop's
  code applies the thresholds).
- **Tools:** ledger lookup. **Model:** strongest available — judging conversion is the
  hardest call in the system (today's codebase already prices review at Opus; keep that
  instinct).

### 6.6 Pipeline Orchestrator *(code — replaces MarketingDirector)*

Deterministic state machine: phase sequencing, the per-email loop (draft → gates → read →
critique → revise, max 2 revision cycles, keep the version with the best
gates-pass + pull + critic verdict), the sequence pass, budget/deadline/cancellation
guards (kept as-is from today's `_check_guards`), graceful degradation ("best draft"
shipping with an honest Campaign Report), event emission, persistence. Zero LLM calls.
`CampaignOrchestrator`'s persistence-adapter/observer pattern and the SSE spine carry over
nearly unchanged.

### 6.7 Sequence Pass *(code + one LLM check)*

After all emails pass individually: deterministic cross-email n-gram overlap and
opening-move fingerprints (bans reused phrases/structures mechanically — currently only
prompted for, never verified); subject-line variety check; then one strong-model pass
reading the sequence in order against the arc ("does 3 escalate 2; is the promise
consistent; does each stand alone"). Failures produce targeted per-email revision briefs
routed back into the craft loop.

---

## 7. Agent Hierarchy

Deliberately flat — there is no hierarchy, because there is no delegation authority to
arrange. The pipeline invokes roles; roles never invoke each other.

| Role | Phase | Model | Sees | Blind to |
|---|---|---|---|---|
| Knowledge Compiler | 0 | mid (+strong for Audience Model) | corpus, web (tools) | the campaign |
| Strategist | 1 | strongest | request, all artifacts, past reports | raw corpus (retrieval only) |
| Email Writer | 2 | strongest | briefs, voice, ledger, prior emails | reader/critic identities |
| Blind Reader | 2 | mid | one rendered email + persona | *everything else — by design* |
| Conversion Critic | 2 | strongest | email, brief, ledger, reader report | the writer's drafts-in-progress |

The "blind to" column is the architecture. Each role exists because its ignorance or its
separate context is load-bearing; any role whose column were empty should be a tool or be
merged — which is exactly why research/audience/competitor/strategy collapse into one.

---

## 8. Tool Architecture

### What is a Tool vs. an Agent

- **Tool:** an executable capability with typed inputs/outputs and no goals. It never
  chooses what to do next, never owns quality, and is reusable across roles. If it can be
  unit-tested with assertions, it is a tool.
- **Agent:** a reasoning role that owns a judgment loop over an artifact, justified by a
  distinct information boundary (see §7).
- **Never agents:** routing/sequencing (code), format validation (code), retrieval
  (tool), persistence (code), ingestion transforms (tools — the current
  loader/cleaner/chunker pipeline is correctly tool-shaped already).
- **Never tools:** anything whose output quality is a matter of taste or persuasion.

### The tool catalog

**Acquisition (Compiler only):**
- `crawl_site(url, budget)` — the current single-page `WebsiteLoader` upgraded to follow
  same-domain links with priority heuristics (pricing, about, customers, docs, blog).
  This is the single cheapest big win for input depth.
- `web_search(query)` / `fetch_page(url)` — market language, competitor pages, reviews.
  Practical note: the Claude Agent SDK the provider already drives has WebSearch/WebFetch
  built in; the Compiler can run as an SDK agent with those tools enabled, while all other
  roles keep `allowed_tools=[]`. The tool boundary is enforced by provider configuration
  per role, not by prompt.
- `parse_pdf` / `parse_docx` / `analyze_image` (vision+OCR) — existing loaders, kept as-is.

**Retrieval (Compiler, Strategist, Writer, Critic):**
- `search_corpus(query, k)` — over stored chunks (stop discarding them). Lexical first;
  the async store interface already anticipates pgvector — plug embeddings in behind the
  same seam later.
- `get_evidence(id)` / `find_evidence(claim_text)` — ledger lookups.

**Verification (code, invoked by the orchestrator — no model in the loop):**
- `lint_email(email)` — today's `email_copy.structural_issues` + `quality_gates`, kept.
- `check_evidence(email, ledger)` — extract numbers, prices, named entities,
  superlatives from the draft; every one must match a ledger entry or the draft bounces
  back with the exact unsupported claim named. This converts "never invent a statistic"
  from an instruction into an invariant.
- `spam_screen(email)` — trigger vocabulary, ALL-CAPS/punctuation abuse, link-text
  hygiene.
- `overlap_check(email, prior_emails)` — n-gram and opening-move collision detection.
- `merge_field_check(email, allowed_tags)` — placeholders remain banned *except* the
  user-configured ESP merge vocabulary (fixes the "no `{{first_name}}` ever" gap).

Tools are attached per role at construction (as the runtime already does with dependency
injection), not advertised globally — the current instinct ("do not attach every tool to
every agent") is right and is preserved.

---

## 9. Knowledge Architecture

Two layers with different lifetimes, joined by provenance:

**Layer 1 — Source Corpus** (raw, campaign-agnostic, org-scoped): every ingested document,
cleaned and chunked (chunks *stored*), with source URL/file identity and fetch date. Never
injected wholesale into prompts; reached only via retrieval. Retained forever so artifacts
can always cite and humans can always audit.

**Layer 2 — Knowledge Artifacts** (distilled, structured, versioned, org-scoped): the six
artifacts of §10, small enough to inline into prompts *in full* — which resolves the
current truncation problem not by smarter truncation but by making the thing injected
already-distilled. Every factual entry links `(document_id, quote)` into Layer 1.

**Scoping:** artifacts belong to the *organization/product*, not the campaign (the current
`campaign_id`-scoped knowledge means a second campaign for the same product restarts from
zero). Campaigns reference the artifact versions they ran against — which also gives
reproducibility. The existing null-scoped "library" idea generalizes into this cleanly.

**Evolution:**
- *Ingest-time:* new material → corpus → incremental Compiler pass → artifact diffs
  (versioned, user-visible).
- *Campaign-time:* artifacts are read-only. A campaign never silently mutates org
  knowledge.
- *Post-campaign:* the Campaign Report (final pull scores, critic verdicts, which angles
  survived revision, user edits to drafts if captured) is stored and fed to future
  Strategist runs — the learning loop the current system lacks entirely.
- *Staleness:* artifacts carry `compiled_at` and source fetch dates; refresh is on-demand
  (later: scheduled re-crawl).

**Deferred by choice:** no knowledge graph and no embeddings on day one. Six typed
artifacts + lexical retrieval over one org's corpus covers the email use case; a graph
earns its complexity only when cross-entity reasoning at scale (many products, many
competitors, long histories) demonstrably outgrows flat artifacts. The store interface is
where pgvector plugs in without touching callers — that existing seam is correct.

---

## 10. Artifact Architecture

All artifacts are typed Pydantic models, persisted, versioned, and human-readable
(renderable to Markdown for user review/edit).

**Knowledge artifacts (org-scoped, from Phase 0):**

1. **Business Profile** — what the company does, for whom, business model, category,
   maturity signals. *Confidence-labeled: every statement `grounded` (with citation) or
   `inferred`.*
2. **Offer Sheet** — products/plans, prices, guarantees, trials, onboarding motion,
   available CTAs (the URLs/actions that actually exist). Writers may only ask readers to
   do things on this sheet.
3. **Evidence Ledger** — the load-bearing artifact. Typed entries: `metric`,
   `testimonial`, `customer_name`, `integration`, `feature_fact`, `guarantee`, `award`,
   each with quote + source + strength. The only place claims may come from; the
   `check_evidence` gate enforces it.
4. **Voice Profile** — derived from the user's existing emails/site copy when provided:
   diction register, cadence, greeting/sign-off conventions, 3–5 verbatim exemplar
   passages (few-shot beats description), banned-phrase additions. When no copy exists:
   an explicit chosen default, recorded in the artifact — never an implicit house style.
5. **Audience Model** — segments with jobs-to-be-done, pains *in the buyer's own words*
   (mined from testimonials/reviews where possible, cited), objections ranked by
   frequency/severity, sophistication level. Grounded/inferred labels throughout — the
   honesty the current persona generator lacks.
6. **Gap Report** — what the Compiler could not establish (no pricing found, no
   testimonials, no existing copy to learn voice from), each with impact ("emails cannot
   name a price") and an optional question for the user. Feeds an ask-the-user checkpoint
   or explicit proceed-with-inference.

**Campaign artifacts (campaign-scoped):**

7. **Campaign Brief** (Phase 1) — deliverable contract (type, exact count), stated
   interpretation of the request, reader definition (one person, not a segment), campaign
   promise, sequence arc, subject strategy, and the Email Briefs.
8. **Email Brief** (one per email) — position, job in the arc, the single idea it owns,
   evidence ids it spends, objection it answers, emotional register, CTA, what it must not
   reuse. The unit of hand-off to the Writer *and* the unit of revision after the sequence
   pass.
9. **Email Draft(s)** — the parsed `Email` model with full version history (kept from the
   current `revisions` idea), each version tagged with its gate results, BlindRead, and
   Critique.
10. **BlindRead Report / Critique** — as in §6.4/§6.5; persisted per version, surfaced in
    the UI timeline (the current SSE narration extends naturally to these).
11. **Campaign Report** — final artifact: deliverables, scores, revision counts, budget
    spent, gaps that constrained quality, angles that worked. The user's receipt and the
    Strategist's future memory.

Deliverables remain rendered plain text (`render_email`) — "deliverables are text, not
JSON" is right and stays.

---

## 11. Communication Model

- **Phases → artifacts.** The only inter-phase interface is persisted typed artifacts. No
  agent reads another agent's *prompt* or *conversation*; no shared mutable blackboard.
  The runtime `Memory` abstraction is deleted, not replaced — the artifact store is the
  memory.
- **Within the craft loop,** the orchestrator passes values explicitly: draft → gates →
  reader report + critique → revision input. Everything the writer sees on a revision turn
  is enumerable and logged.
- **User ↔ system:** two optional checkpoints (Gap Report questions after Phase 0; brief
  approval after Phase 1), controlled by policy: `autonomous` (never wait — current
  behavior), `checkpoint` (pause at both). Checkpoints edit *artifacts*, which is why
  artifacts must be human-readable.
- **Observability:** the emit-once/persist-and-broadcast spine is kept verbatim; phase
  transitions, gate results, reader verdicts, and critic edits become first-class events.
  A run still narrates itself.

---

## 12. End-to-End Reasoning Flow

*"Create a five-email onboarding campaign for my SaaS."* — user has connected their
website and uploaded two PDFs and three past newsletters.

**Phase 0 (at ingestion time, already done before the request):** the crawler pulled ~15
pages (home, pricing, docs, customers, changelog); PDFs parsed; newsletters ingested. The
Compiler produced: Business Profile (grounded); Offer Sheet (3 plans with prices, 14-day
trial, CTA inventory: `start trial`, `book demo`, `docs quickstart`); Evidence Ledger (23
entries — "syncs 25 models across 9 providers", two named testimonials, SOC2, "1,500 free
credits, no card"); Voice Profile learned from the newsletters (short declaratives,
first-name sign-off, no exclamation marks; 4 exemplar passages); Audience Model (two
segments; objections led by "we already have an in-house script" — cited from a
testimonial's before-state); Gap Report: *no onboarding-specific activation metric found;
no case-study numbers.* Policy is `checkpoint`, so the user was asked one question — "what
should a new user have done by day 7 to stick?" — and their answer ("connected a data
source and run one report") entered the ledger as user-attested evidence.

**Phase 1 (~1 minute):** the Strategist reads request + artifacts. Contract: 5 emails,
type = onboarding/activation (not sales — the reader already signed up; this
interpretation is recorded in the brief). Reader: "the developer who started a trial
yesterday, has not connected a data source, evaluating during work hours." Arc: aha-path —
(1) get to first report in 10 minutes, spends the quickstart evidence; (2) the objection
email — "keeping your in-house script?" — spends the testimonial's before/after; (3)
depth: 25-models fact, one feature, one use case; (4) social proof + team invite CTA; (5)
trial-end, honest summary of what they did/didn't do, single upgrade ask. Each Email Brief
names its evidence ids, register, and CTA from the Offer Sheet. No two briefs share an
angle or a proof. User approves the brief untouched.

**Phase 2 (per email, ~3–4 model calls each):** Email 1: Writer drafts from brief +
voice exemplars. Gates: instant pass, except `check_evidence` flags "set up in 8 minutes"
— ledger says 10; bounced to the writer with the exact line; fixed without any model
judging taste. Blind Reader (persona: the trial developer): opened yes, stopped at a
throat-clearing line in paragraph 2, what_it_sells accurate, pull 6, would_act "maybe."
Critic (sees brief + ledger + report): three ranked edits — cut the quoted line, move the
quickstart link above the fold, the CTA asks two things ("connect and invite") where the
brief says one. Writer revises against both reports; gates pass; second read: pull 8,
would_act yes → accepted (2 revision cycles max; best version kept either way — the
current keep-the-better-draft rule, preserved). Emails 2–5 proceed the same way, each
writer turn carrying prior accepted emails verbatim.

**Sequence pass:** overlap check flags email 4 opening with the same "You've probably
noticed…" move as email 2 — deterministic catch, targeted revision brief for email 4's
opener only. Strong-model arc read: escalation confirmed, email 5's tone matches voice.
**Contract check (code):** 5 emails, all fields present, all gates green.

**Delivery:** five rendered, send-ready emails plus the Campaign Report (scores, evidence
spent, the day-7 activation answer that shaped email 1, and a note that case-study numbers
would have strengthened email 4 — feeding the next Gap Report). Total: ~25–30 model calls,
every one either distilling, strategizing, writing, reading, or judging — none routing.

**How reasoning improved over time in this flow:** raw pages → cited facts (compilation);
facts → spent-once evidence assignments (strategy); brief → draft → behavioral evidence of
failure → targeted repair (craft); campaign → report → better next strategy (learning).
Each phase strictly raises the information density of what the next phase reads.

---

## 13. Alternative Architectures Considered

1. **Keep the LLM Director, improve its prompt/tools.** Rejected: for a single channel the
   decision space collapses to a fixed DAG; the director cannot parameterize specialists,
   so its only lever is order; and its stochastic failure modes cost real machinery. Its
   legitimate judgment (interpreting the request) moves into the Strategist's typed
   contract, where it belongs. Reconsider a routing layer only when multi-channel requests
   ("emails + landing page + ads") return — and even then it is a thin request-parser
   choosing among channel pipelines, not a step-by-step loop.

2. **One mega-prompt, one call.** Strong single models can one-shot a decent sequence.
   Rejected: no verification (evidence, structure, overlap all unchecked), no engineered
   ignorance (a model cannot blind-read its own draft in-context), quality unmeasurable,
   and long-sequence coherence degrades — the codebase already learned this ("three emails
   sharing a single response is how all three end up saying the same thing").

3. **Deep multi-agent society (debating strategists, panels of critics, negotiating
   writers).** Rejected on the design philosophy: added roles must earn their place via an
   information boundary. Reader-panel variance (multiple personas) is the one ensemble
   with a clear mechanism, kept as a `maximum`-policy option.

4. **Knowledge graph + embedding-first memory.** Rejected for now: one org's corpus is
   small; typed artifacts inline fully into prompts; provenance links give the graph-like
   traceability that matters. The store seam allows pgvector later without caller changes.

5. **Fine-tuned / RL-optimized writer.** Out of scope at this stage: no send-performance
   data exists to train on. The Campaign Report + evaluation harness build exactly the
   dataset that would justify this later.

---

## 14. Trade-offs

- **Latency & cost concentrate in Phase 2.** ~4–6 strong-model calls per email is the
  price of verification; "quality over speed" is the stated priority, and the policy
  presets (kept) let `fast` skip the critic and single-cycle the loop.
- **Determinism vs. adaptivity.** A fixed pipeline handles "make me 5 emails" perfectly
  and odd requests ("rewrite this email", "subject lines only") less naturally. Mitigation:
  the Strategist's contract includes a small closed set of campaign shapes
  (`sequence | single | rewrite | variants`); the pipeline branches on the shape in code.
  This covers the realistic request space without reintroducing an open-ended router.
- **Compilation adds an upfront step and can bake in errors.** An artifact wrong at
  compile time propagates. Mitigations: provenance on every entry, user-visible artifacts,
  the grounded/inferred split, cheap refresh.
- **Checkpoints trade autonomy for quality.** Asking one Gap Report question improves
  every email but breaks "fire and forget." Policy-controlled; default remains autonomous.
- **Killing the generic runtime narrows the platform.** BaseAgent/Memory/KnowledgeAccess
  generality is deleted in favor of five concrete roles. Extensibility survives at a
  better joint: a *channel pack* = {strategy extension, writer + format contract, channel
  gates, channel reader persona}. LinkedIn/blog/ads plug into the same knowledge and
  strategy layers; they reuse phases 0–1 wholesale, which is precisely the part of this
  design that generalizes.
- **Evidence gating can over-block** (a paraphrased fact failing exact matching).
  `check_evidence` needs a tolerance tier: hard-fail on numbers/prices/names, soft-flag
  paraphrases for the Critic to adjudicate.

---

## 15. Final Recommendations

**Remove**
1. `MarketingDirector` as an LLM loop (keep its guards/degradation logic in the code
   orchestrator).
2. `ResearchAgent`, `AudienceAgent`, `CompetitorAgent`, `StrategyAgent` → one Strategist
   over compiled artifacts.
3. `ReviewAgent` → per-email Conversion Critic + kept mechanical gates + sequence pass.
4. Blog/social/ads/landing agents and prompts (return later as channel packs).
5. Runtime `Memory`, unused `KnowledgeAccess`, the dual knowledge store, per-agent
   `version` strings — the generic-platform scaffolding.

**Keep**
6. The email agent's plan/draft/blind-read/rewrite protocol — promoted to the system core.
7. Labelled-field format + `email_copy` validation; `quality_gates`; request-verbatim-
   at-top-of-prompt; SSE observability spine; policy presets; model routing; the
   `AIProvider` seam; budget/deadline/cancellation guards; best-draft graceful
   degradation.

**Build (in order of leverage)**
8. **Evidence Ledger + `check_evidence` gate** — converts anti-hallucination from prompt
   text to invariant; biggest quality-per-effort win.
9. **Knowledge Compiler + artifact store** (org-scoped, versioned, provenance-linked);
   stop discarding chunks; corpus retrieval.
10. **Multi-page crawler** and Compiler-only web tools (the SDK's WebSearch/WebFetch are
    already available behind the existing provider — enable them for this one role).
11. **Strategist + Campaign/Email Brief artifacts** with the typed deliverable contract.
12. **Code orchestrator** wiring the three phases; port guards and persistence observer.
13. **Voice Profile learning** from user-provided emails (few-shot exemplars).
14. **Sequence pass** (deterministic overlap + arc read), spam screen, merge-field
    vocabulary.
15. **Evaluation harness**: a fixed set of brief+corpus fixtures, blind-reader pull as the
    tracked metric, LLM-judge pairwise comparisons against strong human baselines, run on
    every prompt change. Without this, "rivals elite copywriters" is unfalsifiable — and
    the scripted-provider testing approach already in use is exactly the right substrate
    for it.

The through-line: today the system spends its intelligence deciding *what to do next*,
while the writer works from truncated raw text and unverifiable lists. The redesign spends
zero intelligence on routing and all of it on knowing more, deciding once, writing well,
and judging honestly — which is where elite email copy actually comes from.
