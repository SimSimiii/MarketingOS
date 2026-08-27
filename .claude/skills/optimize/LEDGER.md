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

## 2026-08-27 15:00 — branch optimize/20260827-1500

### LANDED  subject alternatives are gated before they are scanned
Axis: replace judgment with code / quota. The subject bake-off was the one narrowing
step in the loop that paid before it screened: a line that repeated an earlier email's
subject or carried an unlicensed figure was scanned at full price, could win the field,
and was reverted afterwards — so the run kept its incumbent line even when a clean
alternative had scanned well above it. The free checks now screen the field first; the
incumbent is never screened, and a line is dropped only if it breaks something the draft
had not. `_check` is memoized across the screen and the swap.
Commit: 92d824a. Checks: ruff clean (1 pre-existing SIM102), 788 passed (785 + 3).
No change in spend — same writer call, same scan per reader, over a field that can only
shrink. Forecast untouched.
