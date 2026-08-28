# Optimization ledger

Every pass of the `/optimize` workflow appends here, newest first — landed and rejected
alike. A rejection with a stated reason is the most valuable kind of entry: it is the only
thing stopping the next autonomous run, which cannot see this one, from spending quota
re-deriving a dead end.

Do not rewrite entries. Do not tidy old ones. Append.

Format:

```markdown
## <date time> — branch <name>

### LANDED  <one-line summary>
Axis: <which of the eight in SKILL.md>. <What was wrong, in one or two lines.>
Commit: <sha>. Checks: <ruff / pytest result>. <What it buys.>

### REJECTED  <one-line summary>
Reason: <why it is a dead end, specifically enough that nobody retries it.>
```

Standing rejections that predate this workflow live in
`docs/external-review-brief.md` — four shallow analysis agents, absolute 0-10 model scores,
a refine-only loop, a model deciding what step runs next, and emails emitted as JSON. Those
are settled. Read them before proposing anything that resembles one.

---

## 2026-08-27 14:20 — branch optimize/20260827-1420

Global sweep. Baseline `optimize-baseline-20260827-1420` (b7dbb9e), pushed. Budget at
start: ~4.47M weighted, 207 min left in the window.

### LANDED  the bake-off no longer reads candidates a gate has already vetoed
Axis: 2, quota per run. `EmailVersion.measured` is `(clean, pull, carried, attributions)` —
the blocking gate outranks the score — so a blocked candidate could never win the bake-off,
and every one of them was still read cold at a whole panel each. `_judge_draft`'s docstring
already claimed this ordering; the gates ran first but nothing acted on them. Guarded by the
"unless they are all blocked" case, where the gates have ranked nothing and the read is the
only instrument left. Commit: 29082bf. Checks: ruff clean (1 pre-existing SIM102),
787 passed. Saves up to (candidates − 1) × readers per email — 9/email on the maximum
preset, 45 on a five-email campaign — and spends nothing new. Duels are provably
unchanged: `max` over `measured` already picked the best *clean* loser as runner-up.

### LANDED  a guard fetch no longer serializes the fan-out behind it
Axis: 6, frontend request waterfalls. Two server components awaited one request only to
guard on it, then started four or five more that never needed its result - all keyed by a
route id, not by the guarded record. The brand layout is the expensive one: it wraps four
routes, and on three of them the child page does not refetch the same set, so no concurrent
render was hiding the extra round trip behind Next's memoization. Commit: c0d5f28. Checks:
tsc clean, eslint clean, ruff clean (1 pre-existing SIM102), 787 passed. Removes one round
trip from TTFB on those routes and on the execution result page; same request count, no
model spend touched.

### REJECTED  flatten the same waterfall in brands/[brandId]/market/page.tsx
Reason: its `api.getMarket(brandId)` is uncaught *on purpose* - `MarketView` takes a
non-nullable `MarketRead`. The serial guard is what turns "no such brand" into a 404 before
that uncaught fetch turns it into a 500. Flattening it would either mask a real backend
failure as a 404 or require an error boundary that does not exist yet. The waterfall is
load-bearing. Not retried without an error-boundary pass first.

### REJECTED  dedupe the four fetches brands/[brandId] layout and page both make
Reason: not a duplication. Next 16 memoizes GET `fetch` calls with the same URL and options
across layouts and pages within one server render pass, and every call goes through one
`request()` helper with identical headers and `cache: "no-store"` - so the two components
already share one response each. Confirmed in `node_modules/next/dist/docs/01-app/
03-api-reference/04-functions/fetch.md`, not assumed. Nothing to fix.

### REJECTED (for now)  a gate asserting every path api-client.ts calls exists in the backend
Reason: right idea, wrong order. This is the one real gap on the frontend - `types.ts` (1009
lines) mirrors the Pydantic schemas by hand and nothing checks it, so a renamed route is a
silent runtime 404. But 5 of the 34 paths append a query string through an interpolation
(`/knowledge${suffix}`, `/campaigns${includeArchived ? "?..." : ""}`, `/executions/${id}/
logs${suffix}`), so extracting them statically needs a heuristic - and a gate that
false-positives would block a correct change, which this codebase does not allow of anything
that blocks. Two honest routes: (a) regularise `request()` to take path and query as separate
arguments first, making extraction exact, then add the gate - two passes, not one; or (b)
stub `fetch` and call every `api.*` function to record real URLs, which is exact but needs a
frontend test runner the repo does not have. Retry as (a), and only as (a).

### REJECTED  server-render the model catalog instead of fetching it from a client hook
Reason: the current design is better. `use-model-catalog.ts` already caches the in-flight
promise at module scope, so the whole app makes one request, a failure does not poison the
cache, and the picker degrades to the preset rather than taking down the screen it sits on.
Passing it from a server component would fetch the catalog on every page that merely renders
a dialog *trigger*, whether or not the picker is ever opened. Strictly worse. Not retried.

### REJECTED  memoize or incrementalise the SSE timeline fold
Reason: already memoized (`useMemo(() => reduceRun(events), [events])`), and the O(n^2) that
remains is nominal - a run emits a few hundred events, so re-folding costs milliseconds. The
per-second `now` tick does not re-enter the fold. Checked, clean, nothing to buy.

Frontend axes checked and found clean this run, so the next run need not re-derive them:
client/server boundary (every client-side `api.*` call but three is a mutation, which is the
documented architecture), and request fan-out (every page but the two fixed above already
uses one flat `Promise.all`).

## 2026-08-27 15:4x — branch optimize/20260827-1420 (continued, new window)

### LANDED  a gate licensing every frontend path against the backend's OpenAPI schema
Axis: 4, new deterministic gates, pointed at the frontend. `api-client.ts` hardcodes 48
paths and `types.ts` mirrors the schemas by hand; renaming a route 404s the UI where no
backend test can see it and no frontend check looks - there is no CI and no frontend test
runner. Commit: 6a7cd13. Checks: ruff clean (1 pre-existing SIM102), 797 passed (787 + 10
new), tsc clean, eslint clean. Free - `app.openapi()` spends no model call.

Supersedes the previous entry's "retry as (a), and only as (a)". That entry was wrong: it
assumed extracting the paths needed a heuristic, so it deferred behind a refactor of
`request()`. It does not. One exact rule covers every form in the client - **a path
parameter is always preceded by `/`, a query append never is** - so the literal
`?limit=${n}`, the ternary `${archived ? "?..." : ""}` and the prebuilt `${suffix}` all
normalise correctly with no guessing. Eight cases are pinned as a parametrised test so the
rule is checked, not trusted. The refactor was never needed.

Two things worth carrying forward. Extraction must cover **three** ways the client names a
path - template literals, plain strings, and URLs built straight from `API_URL` (the SSE
stream and the CSV export, which bypass the request helpers). Missing that third group made
ten endpoints look uncalled on the first attempt, and a gate with a blind spot is worse than
none. Hence the second test pinning the extracted count above 30: without it the whole check
passes vacuously the day a helper is renamed. The gate is also deliberately one-directional
- a backend route with no frontend caller is not a defect (`/api/health` is exactly that),
so asserting the reverse would fail on correct code.

Verified by injecting a real rename (`forecast` -> `forecasts`): the gate fails and names
the offending path. Reverted before commit. A gate nobody has watched fail is not known to
work.

### LANDED  saving a model pin no longer resets the campaign's preset
Axis: 5, correctness in a service. `update_policy` rebuilds the policy dict from what the
request carried and hand-restores what it did not - but only the tier was ever restored, so
any request without a preset lost it, along with any stored field overrides. The model
picker sends exactly that request: clicking "Save models" on a `maximum` campaign moved it
to `balanced`, so the run that followed was not the run that was configured - fewer drafts,
different judges, smaller budget, nothing on screen saying so. Commit: 1b74d90. Checks: ruff
clean, 800 passed (797 + 3 new). Live bug, not latent.

Found by reading the *frontend*: the UI could not send `email_tier` on a policy update at
all, and chasing why led into the rebuild. Worth generalising - the existing comment named
the hazard exactly ("anything stored in it that this form does not carry has to be put back
by hand") and a test pinned the tier direction, but the preset direction had no caller until
the picker grew a save of its own, so the asymmetry was invisible from the only side anyone
looked at. When a comment says "must be restored by hand", check every direction it applies
to, not the one the test covers.

Each of the three regression tests was confirmed to fail on the old code with
`KeyError: 'preset'` by reverting the fix and re-running. Not assumed.

### LANDED  the email tier can be changed after a run, not only at creation
Axis: 6, frontend. The backend has accepted `email_tier` on a policy update all along and
its comment says why; the frontend type omitted the field, so reaching a capability built
for exactly this meant deleting the campaign and making another. Commit: 7caa313. Checks:
tsc clean, eslint clean, ruff clean, 800 passed. Needed 1b74d90 first - before that fix a
tier-only request would have destroyed the preset the same way a model pin did.

No new test: there is no frontend test runner, and the API path the control uses is pinned
by `test_changing_the_look_does_not_reset_the_preset`.

### REJECTED  a gate comparing types.ts field-by-field against the OpenAPI component schemas
Reason: measured, not guessed, and it does not hold up. Matching a Pydantic schema to a TS
interface by name (exact, else strip the `Read` suffix) leaves 16 of 52 object schemas
unmatched, and - worse - produces a confident *false positive*: backend
`AudienceSegmentRead` (who/where/why_them/angle) and `knowledge/artifacts.Segment`
(situation/job_to_be_done/trigger) are unrelated models, and the frontend's `AudienceSegment`
mirrors the second while the name matches the first. The gate reports 13 fields of drift on
correct code. Making it sound needs a hand-maintained name map, which reintroduces exactly
the drift it exists to catch. Only the two genuine differences it surfaced were worth
anything, and both were found by reading the output rather than by the check blocking.
Do not build this on name matching. If it is retried, the match has to come from the route
that returns the type, not from its name.

### LANDED  five api-client methods nothing calls
Axis: 7, dead weight. `getExecutionStatus`, `getKnowledgeDocument`, `deleteBrand`,
`listRivals`, `listProspects` had no caller in src/. Four are superseded by the richer
endpoint the app actually uses. Commit: 5b05146. Checks: tsc clean, eslint clean, ruff clean,
800 passed. Since 6a7cd13 an unused method is no longer free - the contract gate would fail
the build over drift in an endpoint nothing calls - so the gate's surface drops 48 -> 45
paths, which is the frontend's real dependency set.

Method note: the first scan reported **nine**, and four were false positives.
`market/page.tsx` calls `api` then `.getAudience(...)` on the next line, so a regex anchored
on `api\.` misses it. Any dead-code scan here needs `api\s*\.\s*` and a per-name grep before
anything is deleted. This nearly deleted live code.

### GAP (not acted on)  the backend serves DELETE /api/brands/{id} and no screen exposes it
Same class as the `email_tier` gap, but deliberately left for a human: deleting a brand
cascades to its knowledge, its market and its campaigns, so what the control warns about
before it fires is a product decision, not a refactor. The client method was removed with the
others rather than kept as the only record of it - this line is the record.

### CHECKED CLEAN  backend request fields the frontend cannot express
Ran every write endpoint's request-body schema against every identifier in src/: after
7caa313 there are none. That check is what confirmed `email_tier` was the only such gap, and
it is cheap to re-run - 13 endpoints, one script, no model call. Worth repeating after a
schema change.

### CHECKED CLEAN  unused exported types in types.ts
All 74 are referenced. No dead weight there.

### LANDED  the campaign goal, which no form had ever collected
Axis: 6, frontend - but the consequence is strategic. `render_context()` puts the user's
framing in front of the strategist and every line is optional; the dialog sent all fourteen
other `CampaignCreateRequest` fields and omitted `goals`, so "What the user wants out of it:
..." never once appeared in a context the product generated. Commit: 43ab010. Checks: tsc
clean, eslint clean, ruff clean, 804 passed (800 + 4 new). No extra spend - one more line in
a prompt already being sent.

The part worth remembering: **the evaluation harness sets it.** `golden.py` gives every case
a goal and `runner.py` passes `goals=case.goals`, so the bench was grading a strategist
receiving an input the shipped product could not supply. Eval and production differed by a
line of context. When auditing what the UI cannot reach, check the eval harness too - it is
the other caller, and where the two disagree the bench is measuring the wrong system.

An optional field no form fills looks exactly like one the user left blank, which is why it
survived. Nothing anywhere looked wrong.

### CORRECTION  the pass-7 "no unreachable request fields" result was wrong
It searched all of `frontend/src` **including `types.ts`**, which mirrors every backend
field by hand - so a field declared there and used nowhere read as "used". Any
reachability check over this frontend must exclude `types.ts`, or it cannot fail. Re-run
correctly it found three: `goals` (fixed above), `KnowledgeSourceCreate.max_pages` and
`ProspectSearchRequest.with_contacts`.

### GAPS (not acted on)  two request fields and four response fields the UI cannot reach
Request: `KnowledgeSourceCreate.max_pages` (crawl depth) and
`ProspectSearchRequest.with_contacts`. Neither reaches a prompt, so neither changes the copy
- lower value than `goals` was, and both are defaults someone chose deliberately.

Response, computed by the backend and dropped by the UI: `PositioningRead.we_have_proof`,
`RivalProfileRead.one_liner`, `AudienceSegmentRead.pains`, and the per-run token counts
(`total_input_tokens`, `total_output_tokens`, `total_cache_read_tokens` on three schemas,
plus the per-agent cache split on `AgentExecutionRead`). The token ones are the interesting
set: the run view shows a USD estimate, but the subscription bills a five-hour window
denominated in tokens with cache reads at 0.1x, so what is on screen is not the currency
that runs out. Showing them is a product decision about what the operator wants to watch,
not a refactor - left for a human.

### REJECTED  make the eval runner pass sender_name/sender_role like the product does
Reason: **do not do this.** Following the `goals` find, the runner builds `CampaignRequest`
with five fields where the orchestrator passes eight - missing `product_url`, `sender_name`
and `sender_role` - which looks like the same bug. It is not. The control emails in
`golden.py` sign off `SIGNOFF: - the Notewright team` and `- the Portway team`, so *neither*
arm has a personal sender and the duel is fair by construction. Passing one to the generated
arm only would hand it a lever `request.py` calls "real conversion" that the human control
cannot use, and every duel after it would be measuring that handicap instead of the copy.
`product_url` is deliberate too: eval cases supply their material inline as `documents`, so
nothing crawls.

Worth keeping though: `GoldenCase` has no sender field at all, so the bench cannot measure
whether the sender lever works - `request.py` asserts it converts and nothing here tests
that. Closing the gap means giving both arms a sender, which means rewriting the control
emails, and the comment on `control_email` says a control that drifts makes every comparison
against it meaningless. So it is a known unmeasured claim, not a defect. Retire it only as a
deliberate re-baselining of the controls, never as a fix to the runner.

### NOT VERIFIED IN A BROWSER  the two new controls
The goal input (43ab010) and the tier select (7caa313) pass tsc and eslint and both follow
the markup of siblings in the same form, but no run of this workflow has rendered them. There
is no frontend test runner, and standing a dev server up against a seeded campaign costs more
than the change did. Worth one look before merging.

## 2026-08-28 02:36 — branch optimize/20260828-0236

Global sweep. Baseline `optimize-baseline-20260828-0236`, master still at b7dbb9e and
pushed. Budget at start: ~9.72M weighted, 299 min left in the window. Verified baseline
before touching anything: ruff 1 pre-existing SIM102, **804 passed**.

Branched from `optimize/20260827-1420` rather than from master, deliberately. Master never
moves either way, so `git checkout master` is still the undo; branching from master instead
would have forked a second unmerged line over the same files as the previous run's fifteen
commits, and left the operator to merge two branches that both rewrote `craft.py`.

### LANDED  a verified pass from a previous run that had been stranded off-branch
Axis: none of the eight — this is a process failure, not a code one. `git branch -r` shows
two prior run branches, and the *earlier*-numbered one (`optimize/20260827-1420`) does not
descend from the later (`optimize/20260827-1500`). The 1500 branch forked from `2f9425a`,
before the 1420 run's baseline commit existed, so its one landed pass — 92d824a, screening
subject alternatives through the free checks before they are read — was reachable from
nothing anyone would merge. Fifteen commits of later work sat on a branch that did not
contain it. Cherry-picked as 6656fc5 (`-x`, so the original sha is in the message).
Auto-merged into `craft.py` with no conflict against 29082bf, which touched `_bake_off`
while this touches `_polish_subject`. Checks: ruff clean (1 pre-existing SIM102),
**807 passed** (804 + 3). No change in spend — the screen runs before the scan, over a
field that can only get smaller.

Worth carrying forward as a rule for this workflow: **Phase 0 must check `git branch -r`
for other `optimize/*` branches before creating one.** Two runs that both branch from
master produce work that can only be reconciled by hand, and a landed, verified,
pushed pass is invisible to every run after it. This run branches from the previous run's
tip for exactly that reason. The remaining orphan on 1500 is `72594fe`, a ledger entry
only — its content is the paragraph above.

### LANDED  the forecast reads the run history once, in one query
Axis: 5, runtime and data. Two faults in one panel, both on a page that renders on every
visit to a campaign. `forecast_run` called `_comparable_runs` twice - through
`_observed_cost` and again for `len(...)` - to print two views of one set; and each call was
an N+1, asking `list_by_campaign` once per campaign on the same preset, two rows below the
`latest_by_campaign` whose docstring names that exact pattern as the thing to avoid. Four
campaigns meant eight queries. Commit: bc4cec6. Checks: ruff clean (1 pre-existing SIM102),
**808 passed** (807 + 1). No model spend either way - the forecast calls nothing.

Pinned by counting statements against `campaignexecution` while one forecast is served for
one of four campaigns, asserting exactly one. Confirmed it reports 8 on the pre-change code
by reverting the two app files and re-running - the test fails, so it is known to work
rather than assumed to.

Method note for the next run: every predicate that decides which runs count stayed in the
service. `base.py` says repositories "never contain business logic", and "a run that died on
its first call cost a penny" is business logic - so the new `list_by_campaigns` is the exact
plural of `list_by_campaign` and nothing more.

### LANDED  a run's narration is written without being read back
Axis: 5, runtime and data, on the hottest path in the system. `ExecutionEventEmitter.emit`
persisted through `BaseRepository.create`, which add/commit/**refresh**es so a caller can
have the stored row - and this caller keeps neither the row nor the return value. Measured
rather than guessed: a balanced run through the scripted provider writes **171** log lines,
so 171 SELECTs re-reading rows nobody looks at, between model calls, on the same SQLite file
the live page is being served from concurrently. Commit: 0c976eb. Checks: ruff clean (1
pre-existing SIM102), **809 passed** (808 + 1). No model spend either way.

`create` untouched - every other caller does want the refresh. The new `append` is the
write-only door beside it. The commit *per line* was deliberately left alone: batching would
put rows behind the events that announced them, and "persist and broadcast in one call" is
the property that makes the live page and the replayed history agree by construction.

Confirmed the test fails on `create` by swapping the call back and re-running.

### LANDED  eight backend definitions nothing reaches, one of them a trap
Axis: 7, dead weight - the frontend got this sweep two runs ago, the backend never had.
Commit: 21814a0. Checks: ruff clean (1 pre-existing SIM102), **809 passed** - the same 809,
because nothing here changes behaviour.

The one that justifies the pass is `ai/models.py:estimate_cost_usd`. It is not merely
unused: it prices cached input as fresh, which is the error `usage_cost_usd` exists to
correct, and cached input is most of what a campaign spends at a tenth of the rate. A dead
function whose name is *shorter and more obvious* than the correct one is a trap for the
next caller. The rest: `our_claims` (a re-export for a caller that never arrived),
`snapshot_from`, `EmailSequence`, `NormalizationError`, `ChunkingError`,
`KnowledgeCompilationError`, `MemoryUpdated` (left from the deleted memory blackboard), and
all of `runtime/logging.py`.

Method, so the next run does not redo it: parse every module under `app/` with `ast`, take
top-level `def`/`class` names, count `\bname\b` across app + tests + prompts + alembic. 46
of 656 came back with one occurrence. **36 of those are route handlers** - reached by their
decorator, never by name - so any such sweep here must exclude `app/api/routes/` or it is
80% noise. Then read the remaining ten individually; two survived reading.

### KEPT DELIBERATELY  `same_claim` / `SAME_CLAIM_OVERLAP` in market/claims.py
Uncalled, and staying. `positioning._SAME_WORDING` justifies its own 0.7 by explicit
contrast with that 0.34 ("higher, because this decides whether to *drop* a claim rather than
whether to show two side by side"), so deleting the pair trades twelve dead lines for a live
calibration comment that no longer means anything.

Worth a future pass, but not this one: `positioning.claims_from_knowledge` inlines
`other.axis is claim.axis and overlap(...) >= _SAME_WORDING`, which is `same_claim` with a
different threshold and applied to every axis rather than only `OTHER`. Two near-identical
rules in two modules. Consolidating them **changes positioning behaviour**, so it is a
behavioural pass with its own tests, not a cleanup.

### LANDED  a fact one email spends is not assigned to the next
Axis: 1, replace judgment with code - the project's central move, applied to a rule the
prompt already stated. `prompts/strategist.md` said "an id that is the backbone of one email
should not be the backbone of another" and nothing checked, so a brief could hand the same
proof to every slot. Commit: f3bbf41. Checks: ruff clean (1 pre-existing SIM102),
**810 passed** (809 + 1). Free - no model call, forecast untouched.

The reason this one is worth having: **no gate in the loop can see the failure.** Five
emails arguing from one testimonial share no phrase, so `overlap_gate` passes each; the
evidence gate is happy because every claim is licensed; `substantiation` is happy because
each email spent what it was assigned. Every check says yes and the sequence still reads as
one email sent five times. Repetition of *proof* had no instrument at all - repetition of
*phrasing* has had one since the beginning.

Guarded rather than absolute, and the guard is the interesting half: a business with two
proofs and a five-email sequence is the ordinary case, so an email whose every id is already
spent keeps them. Nothing assigned is strictly worse than something repeated - it leaves a
slot briefed to argue from proof with none. Only a partial overlap is trimmed.

The prompt line was rewritten in the same commit to state what the code now guarantees.
Leaving it asking for something weaker than the code enforces is how a strategist ends up
planning against a rule it is silently corrected on.

Confirmed the test fails on the pre-change code by reverting `strategist.py` and re-running.
