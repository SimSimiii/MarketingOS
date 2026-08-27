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
