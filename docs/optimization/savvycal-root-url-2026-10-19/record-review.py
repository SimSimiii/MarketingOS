"""Record editorial audit findings only when the API helper is idle."""
import json
from pathlib import Path

ROOT = Path(__file__).parent
pending = [p for p in (ROOT / "commands").glob("*.json")
           if not (ROOT / "responses" / p.name).exists()]
if pending:
    raise SystemExit(f"Helper command pending: {pending[0].name}")
reviews = json.loads((ROOT / "pending-reviews.json").read_text(encoding="utf-8"))
path = ROOT / "state.json"
state = json.loads(path.read_text(encoding="utf-8"))
current = state.setdefault("stage_reviews", [])
for review in reviews:
    current[:] = [r for r in current if r["stage"] != review["stage"]]
    current.append(review)
path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("Recorded", ", ".join(r["stage"] for r in reviews))
