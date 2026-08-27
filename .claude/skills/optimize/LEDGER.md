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
