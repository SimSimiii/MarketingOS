"""Persist the reviewed correction, preserving the failed baseline and raw assets."""
import json
from datetime import UTC, datetime
from pathlib import Path

root = Path(__file__).parent
assert not [p for p in (root / "commands").glob("*.json") if not (root / "responses" / p.name).exists()]
execution = "f3b1420d-d6a1-4010-b4fa-fcdc8b9fe6e4"
run_dir = root / "runs" / execution
result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
report = result["result"]["report"]
assert report["delivered"] == report["promised"] == len(result["assets"]) == 1
assert result["needs_review"] and result["outcome_status"] == "degraded"
assert report["emails"][0]["clean"] and report["emails"][0]["unresolved"]
render = json.loads((run_dir / "render-check.json").read_text(encoding="utf-8"))
assert all(c["scrollWidth"] == c["width"] for c in render["checks"])
ui = json.loads((run_dir / "ui-check.json").read_text(encoding="utf-8"))
assert not ui["errors"] and "Delivered 1 of 1 email" in ui["text"]
state_path = root / "state.json"
state = json.loads(state_path.read_text(encoding="utf-8"))
review = {
    "iteration": 2, "execution_id": execution, "score": 78, "comparable": True,
    "score_status": "Editorial review of actual delivered asset; not a conversion measurement",
    "grid": {"factual_support":24, "audience_offer_clarity":14, "specificity_argument":14,
             "subject_body_cta":10, "polish_rendering":9, "promises_repetition":7},
    "strengths": ["Offering explicit and all three assigned facts spent", "Clean text/HTML asset preserved with review warning; no invented pricing or numerical outcomes"],
    "remaining_defect": "Argument relevance and signup commitment remain weak; rendered CTA goes to homepage instead of planned /signup.",
    "evidence": [str(run_dir / name) for name in ["result.json","timeline.json","render-check.json","ui-check.json"]],
    "next_action": "Delivery veto fix is validated. Improve CTA resolution and audience argument separately before claiming send-ready copy.",
    "sellable_result": False,
}
state["quality_history"] = [h for h in state.get("quality_history", []) if h.get("execution_id") != execution] + [review]
scored = [h for h in state["quality_history"] if h.get("score") is not None and h.get("comparable")]
best = max(scored, key=lambda h:h["score"])
state.update(status="material_veto_fixed_verified", production_code_changed=True, sellable_result=False,
             quality_best={k:best[k] for k in ["score","iteration","execution_id"]},
             next_action=review["next_action"], correction_finished_at=datetime.now(UTC).isoformat())
state["mechanism_fix"] = {
    "validated":True, "backend_tests":1749, "frontend_tests":28, "ruff":"passed",
    "frontend_lint":"passed", "typecheck":"passed", "delivered":1, "needs_review":True,
    "model_calls":10, "duration_seconds":168.34, "input_tokens":250435,"output_tokens":18644,
    "baseline_model_calls":25,"baseline_duration_seconds":359.07,
    "report":"docs/reviews/savvycal-material-veto-fix-2026-10-19.md",
    "scope":"Fix of the requested delivery mechanism, not a claim of general marketing quality or server reload.",
}
state["call_metrics"]["scope"] = "Initial homepage-only baseline audit; excludes the correction run."
state["lifetime_completed_model_calls"] = 52
state_path.write_text(json.dumps(state,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"status":state["status"],"score":78,"delivered":1,"needs_review":True}))
