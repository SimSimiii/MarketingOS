---
name: optimize
description: Autonomously find and implement optimizations in MarketingOS, in committed passes, until the Claude usage window runs out. Use when the user says "optimize <something>" (a feature, a module, performance, the frontend) or just "optimize the project" / "/optimize" for a global sweep looking for new features and new angles. Runs without asking questions; every pass is its own commit on a throwaway branch.
---

# Autonomous optimization run

The operator starts this when they have quota in the current five-hour window and no
intention of using Claude themselves. The job is to convert that quota into committed,
reversible, individually-verified improvements to MarketingOS, and to keep going until the
window is spent.

**Work without asking.** Never call AskUserQuestion during a run. Where a judgment call
arises, make it, and record the call and its reasoning in the ledger. The operator is not
at the keyboard; a question is a run that stalls for four hours.

## Phase 0 — baseline (never skip, never reorder)

Everything downstream depends on there being a pushed commit to fall back to.

```bash
python .claude/skills/optimize/quota.py
```

Report the budget in one line, then:

1. `git status --porcelain`. If anything is uncommitted, commit it all as
   `baseline: state before autonomous optimization run` — including work in progress. It
   is the operator's code and it is going into history, not the bin.
2. `git push origin master`. **If the push fails, stop the run and say why.** The whole
   safety model is that master is recoverable from the remote; without the push there is
   no baseline, only a local commit on a machine that is about to be edited for hours.
3. Tag it: `git tag optimize-baseline-<YYYYMMDD-HHMM> && git push origin --tags`.
4. Branch: `git checkout -b optimize/<YYYYMMDD-HHMM>`.

Master now sits at the pushed baseline and is never touched again during the run. Every
pass lands on the branch. The operator can merge it, cherry-pick from it, or delete it.

Read `.claude/skills/optimize/LEDGER.md` before doing anything else. It is what stops run
number four from re-proposing what run number two already rejected.

## Phase 1 — find angles

**Targeted** (`/optimize the craft loop`, `/optimize frontend performance`): scope the
search to that thing, but search it at every level — a config constant, a hot function, the
shape of the module, whether the thing should exist at all.

**Global** (`/optimize` alone): sweep for both optimizations and new features.

Read before proposing, every run:

- `README.md` "Architecture decisions" — each one was a measured failure. A proposal that
  contradicts one has to beat the measurement that produced it.
- `docs/external-review-brief.md` — the "deliberately rejected" list and the open problem.
- `LEDGER.md` — this workflow's own history.

### Where this codebase actually has room

Ranked by how well the axis has paid off here before.

1. **Replace judgment with code.** The project's central move, applied repeatedly:
   paragraph splitting, positioning set-arithmetic, the radar diff, `substantiation.py`.
   Any model call whose question has a *correct* answer is a candidate — it is free,
   deterministic, and cannot return an invalid result. Highest value per unit of effort.
2. **Quota per campaign run.** Tens of calls per run, each one billed to a subscription.
   Look for: artifacts inlined in full where retrieval would do, context repeated across
   calls that could be ordered for cache reuse, schema bloat (`_schema_text` already strips
   titles — what else is dead weight), a tier set higher than the work needs.
3. **Latency through parallelism.** The three read-only knowledge passes already run
   concurrently because they are independent questions about the same pages. Look for other
   independent calls still awaited in sequence — draft candidates, reader panels, subject
   variants.
4. **New deterministic gates.** The proven pattern for quality: free, blocking, phrased as
   the fix. Ask what a finished draft can still get wrong that a string comparison could see.
5. **Runtime and data.** N+1s in `repositories/` and `services/`, missing indexes, the
   corpus chunker, anything that walks the ledger per email.
6. **Frontend.** Server/client boundary errors, request waterfalls, work done in a client
   component that a server component already had.
7. **Dead weight.** Code no test reaches and no route calls.
8. **New features** (global runs only). The docs name open problems; start there.

### Constraints — a proposal that violates one is dead, do not spend a pass on it

- **No users, no send data, no telemetry.** Anything whose first step is collecting user
  data, or calibrating on the operator, is worthless. Assume this holds.
- **Do not re-propose the rejected list** in `docs/external-review-brief.md`: four shallow
  analysis agents, absolute 0-10 scores, a refine-only loop, a model deciding what runs
  next, emails as JSON.
- **A change that raises model spend per run must state what it buys**, in the commit
  message. Quota is the scarcest resource in the project.
- **Solo developer.** A change nobody can review in an evening is worse than no change.
- The forecast is a contract: **adding a model call to the pipeline means updating
  `forecast.py`**, or `tests/marketing/test_forecast.py` fails and correctly so.

## Phase 2 — the pass loop

One pass is **one idea, one commit**. Not a batch. A batch that fails verification cannot be
bisected, and a batch that hits the quota wall halfway leaves the tree in a state nobody
asked for.

For each pass:

1. **Pick** the highest value-to-effort candidate not already in the ledger.
2. **Implement it.** Match the surrounding code — this codebase comments the *why* and the
   measurement behind a decision, not the *what*. A comment that restates the line is noise
   here.
3. **Verify.** All of these, from `backend/`:

```bash
.venv/Scripts/python.exe -m ruff check app tests
```

```bash
.venv/Scripts/python.exe -m pytest tests -q
```

   Baselines: ruff reports exactly one pre-existing `SIM102` in `app/ai/openai_provider.py`;
   pytest reports **785 passed in ~50s**. If the frontend was touched, add `npm run lint`
   and `npx tsc --noEmit` from `frontend/`, both of which are clean.

   **The test count must not fall.** A pass that deletes tests to go green is a failed pass.
   Behaviour changes come with a test that would have failed before the change.

   Never verify by running a real campaign — `RoleScriptedProvider` in
   `tests/marketing/conftest.py` answers per role and costs nothing. Do not run
   `app.evaluation.judge_bench` or `app.evaluation.runner` without `--dry-run` or
   `--compare`; those spend the operator's quota on measurement rather than on work, and
   this loop is not authorised to make that trade unless the invocation said
   `--with-evals`.

4. **Commit or revert.** Green → commit and `git push origin HEAD`, so the wall can never
   cost more than the pass in flight. Red → one attempt to fix. Still red →
   `git checkout -- .` and log it as rejected with the reason. Do not carry a broken tree
   into the next pass.
5. **Append to the ledger** (format below). Do this even for a rejected pass — a rejection
   with a reason is the most valuable line in the file.
6. **Check the budget** and decide:

```bash
python .claude/skills/optimize/quota.py --json
```

   `remaining_estimate` above ~500k weighted → start another pass. Below that → stop
   cleanly rather than being cut off mid-edit. `remaining_estimate` is `null` until a 429
   has ever been recorded on this machine; in that case run on until the wall lands, which
   is what calibrates every later run.

## Phase 3 — stop

Whether the run ended on the budget or on a 429, finish with:

- The branch name, the number of passes landed and rejected.
- One line per landed change, in the order they were committed.
- Anything a human should look at before merging.
- How to undo everything: `git checkout master` — the branch holds every change and master
  never moved.

If the run died on a 429 mid-pass, say which pass was in flight and whether the tree is
clean. Then stop. Do not wait for the window to reset.

## The ledger

`.claude/skills/optimize/LEDGER.md`, newest first. Append, never rewrite. It is the memory
that makes "find *new* angles" possible across runs that cannot see each other.

```markdown
## 2026-08-27 14:02 — branch optimize/20260827-1402

### LANDED  subject-variant calls now run concurrently
Axis: latency/parallelism. Four independent writer calls were awaited in a loop.
Commit: a1b2c3d. Checks: ruff clean, 785 passed. Saves ~3 wall-clock minutes on a
maximum-preset run; no change in spend.

### REJECTED  cache the compiled artifacts in Redis
Reason: the artifact store is already fingerprint-keyed and never recompiles an
unchanged corpus. The cache would sit in front of something that is already a cache,
and add a service to a single-worker deployment. Not retried.
```
