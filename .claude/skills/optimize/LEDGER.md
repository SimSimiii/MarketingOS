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

_No runs yet._
