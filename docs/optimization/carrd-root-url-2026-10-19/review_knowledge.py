"""Read-only quotation check against the captured brand's stored documents."""
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

repo = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(repo / "backend"))
from app.knowledge.corpus import fold

directory = Path(__file__).parent
snapshot = directory / "steps/20261019T014035853573Z-capture.json"
capture = json.loads(snapshot.read_text(encoding="utf-8"))
connection = sqlite3.connect((repo / "backend/marketingos.db").as_uri() + "?mode=ro", uri=True)
documents = {row[0]: row[1] for row in connection.execute(
    "select id, content from knowledgedocument where brand_id=?",
    (capture["brand"]["id"].replace("-", ""),),
)}
entries = capture["knowledge"]["artifacts"]["evidence"]["entries"]
mismatches = [entry["id"] for entry in entries if fold(entry["verbatim"]) not in fold(
    documents.get((entry.get("document_id") or "").replace("-", ""), "")
)]
result = {"capture": str(snapshot), "evidence_count": len(entries), "quotation_mismatches": mismatches}
(directory / "knowledge-review-corrected.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
manifest = {str(path.relative_to(repo)).replace("\\", "/"): hashlib.sha256(path.read_bytes()).hexdigest()
            for folder in [repo / "backend/app", repo / "backend/prompts"]
            for path in folder.rglob("*") if path.suffix in {".py", ".md"}}
(directory / "source-manifest-cta.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
print(json.dumps(result))
