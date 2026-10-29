"""Read saved audit data without calls to either the API or a model."""
import json
import sys
from pathlib import Path

root = Path(__file__).parent
files = sorted((root / "steps").glob("*-capture.json"))
snapshot = json.loads(files[-1].read_text(encoding="utf-8"))
section = sys.argv[1] if len(sys.argv) > 1 else "knowledge"
data = snapshot.get(section)
if section == "knowledge" and data:
    print("KNOWLEDGE KEYS", list(data))
    artifacts = data.get("artifacts") or {}
    print("ARTIFACT KEYS", list(artifacts))
    for key, value in artifacts.items():
        if key not in {"ledger", "evidence_ledger"}:
            print(key, json.dumps(value, ensure_ascii=False)[:14000])
    ledger = artifacts.get("ledger") or artifacts.get("evidence_ledger") or {}
    print("LEDGER", json.dumps(ledger, ensure_ascii=False)[:14000])
else:
    print(json.dumps(data, ensure_ascii=False, indent=2))
