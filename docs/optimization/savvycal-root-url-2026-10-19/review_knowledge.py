"""Independent, free inspection of the captured compilation."""
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
from app.knowledge.corpus import fold

root = Path(__file__).parent
capture = json.loads(sorted((root / "steps").glob("*-capture.json"))[-1].read_text())
artifacts = capture["knowledge"]["artifacts"]
documents = json.loads(next((root / "steps").glob("*-ingest.json")).read_text())
material = {d["id"]: d["content"] for d in documents}
entries = artifacts["evidence"]["entries"]
out = {
    "evidence_count": len(entries),
    "quotation_mismatches": [e["id"] for e in entries if e["document_id"] not in material
                             or fold(e["verbatim"]) not in fold(material[e["document_id"]])],
    "categories": dict(Counter(e["category"] for e in entries)),
    "monetary_facts": [e for e in entries if re.search(r"[$€£]\s*\d", e["claim"] + e["verbatim"])],
    "offer": artifacts["offer"], "gaps": artifacts["gaps"], "notes": artifacts["notes"],
}
(root / "knowledge-review.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({k:v for k,v in out.items() if k != "offer"}, ensure_ascii=False, indent=2))
