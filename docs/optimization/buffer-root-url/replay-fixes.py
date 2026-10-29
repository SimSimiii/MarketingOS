"""Replay saved audit data through current mechanisms; no HTTP, DB or model call."""
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path.cwd()))

from app.knowledge.artifacts import KnowledgeArtifacts
from app.market.capabilities import derive_capability_profile, normalize_capability_profile, ProductCapabilityProfile
from app.market.claims import ClaimSet
from app.market.positioning import build_current
from app.market.rivals import RivalProfile, review_rationale

root = Path(__file__).parent
source = root / "steps/20261018T174829950157Z-capture.json"
before = hashlib.sha256(source.read_bytes()).hexdigest()
raw = json.loads(source.read_text(encoding="utf-8"))
artifacts = KnowledgeArtifacts.model_validate(raw["knowledge"]["artifacts"])
old_profile = ProductCapabilityProfile.model_validate(json.loads((root / "capability-profile.json").read_text()))
profile = derive_capability_profile(artifacts.evidence, knowledge_id=uuid4(), knowledge_version=1,
                                    company_name=artifacts.business.company_name)
checked = normalize_capability_profile(old_profile, ledger=artifacts.evidence,
    knowledge_id=old_profile.knowledge_id, knowledge_version=1, company_name=artifacts.business.company_name)
rivals = []
for item in raw["market"]["profiles"]:
    data = dict(item)
    data["claims"] = ClaimSet.model_validate({"claims": data["claims"]})
    rivals.append(review_rationale(RivalProfile.model_validate(data)))
positioning = build_current(artifacts, rivals, we_have_proof=True)
by_id = {e.id: e for e in artifacts.evidence.entries}
ids = {e.evidence_id for c in profile.capabilities for e in c.evidence}
assert not ids.intersection({"E1", "E4", "E22"})
assert not any("Keep your three free channels" in text for text in artifacts.offer.guarantees)
assert not any(c.context.claim_scope == "customer_outcome" for row in positioning.readings
               if row.axis == "price" for c in row.ours)
assert before == hashlib.sha256(source.read_bytes()).hexdigest()
result = {
    "kind": "free deterministic replay, not a regenerated campaign or quality score",
    "source_snapshot_unchanged_sha256": before,
    "guarantees_before": raw["knowledge"]["artifacts"]["offer"]["guarantees"],
    "guarantees_after": artifacts.offer.guarantees,
    "notes": artifacts.notes,
    "capabilities_before": len(old_profile.capabilities), "capabilities_after": len(profile.capabilities),
    "capability_categories_after": dict(Counter(str(by_id[eid].category) for eid in ids)),
    "capability_scope_after": dict(Counter(by_id[eid].context.claim_scope for eid in ids)),
    "legacy_verified_after_read_validation": sum(c.state == "verified" for c in checked.capabilities),
    "positioning_before": len(raw["market"]["positioning"]["readings"]),
    "positioning_after": len(positioning.readings),
    "positioning_status_after": dict(Counter(row.comparison_status for row in positioning.readings)),
    "own_price_propositions": [c.text for row in positioning.readings if row.axis == "price" for c in row.ours],
    "rival_rationales": [{"name": r.name, "status": r.rationale_status, "why": r.why,
                           "note": r.note} for r in rivals],
    "capabilities": profile.model_dump(mode="json"), "positioning": positioning.model_dump(mode="json"),
}
(root / "correction-replay.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({k: v for k, v in result.items() if k not in {"capabilities", "positioning"}}, ensure_ascii=False, indent=2))
