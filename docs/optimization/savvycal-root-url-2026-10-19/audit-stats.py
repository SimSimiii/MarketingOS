"""Read saved snapshots; never call an API or a model."""
import json
from datetime import datetime
from pathlib import Path

root = Path(__file__).parent
jobs = {}
for path in sorted((root / "steps").glob("*-poll.json")):
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    candidates = [("compilation", x) for x in snapshot.get("compilation_jobs", [])]
    market = snapshot.get("market")
    if market:
        candidates.append((market.get("kind", "market"), market))
    for kind, job in candidates:
        key = (kind, job.get("started_at"))
        jobs[key] = {"kind": kind, "snapshot": path.name, **job}

rows = []
for job in jobs.values():
    row = {k: job.get(k) for k in (
        "kind", "state", "started_at", "finished_at", "calls", "input_tokens",
        "output_tokens", "cache_read_tokens", "cost_usd", "summary", "snapshot")}
    if row["started_at"] and row["finished_at"]:
        row["duration_seconds"] = round((datetime.fromisoformat(row["finished_at"].replace("Z", "+00:00"))
                                         - datetime.fromisoformat(row["started_at"].replace("Z", "+00:00"))).total_seconds(), 2)
    rows.append(row)
result = {"jobs": rows, "completed_audit_calls": sum(r["calls"] or 0 for r in rows if r["state"] in {"done", "completed"}),
          "notes": "Adapter counts and cost estimates; not API charges. Compilation cost is unavailable in job snapshots. Campaign usage is separate."}
(root / "stage-metrics.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))
