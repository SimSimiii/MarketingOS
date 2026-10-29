"""Record the actual failed baseline; never edit model outputs or production DB."""
import json
from datetime import UTC, datetime
from pathlib import Path

root = Path(__file__).parent
pending = [p for p in (root / "commands").glob("*.json")
           if not (root / "responses" / p.name).exists()]
if pending:
    raise SystemExit(f"Helper still pending: {pending[0].name}")
execution = "43b2b74b-6e43-47a2-8dae-3772d0cfff2a"
run_dir = root / "runs" / execution
result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
ui = json.loads((run_dir / "failed-ui-check.json").read_text(encoding="utf-8"))
assert result["status"] == "failed" and not result["assets"]
assert result["result"]["report"]["delivered"] == 0
assert all(not c["errors"] and c["loadError"] is None and c["scrollWidth"] == c["width"] for c in ui["checks"])
events = json.loads((run_dir / "timeline.json").read_text(encoding="utf-8"))["events"]
drafts = [e for e in events if e["type"] == "draft"]
calls = [e for e in events if e["type"] == "model_call_finished"]
assert len(drafts) == 3 and len(calls) == 25
state_path = root / "state.json"
state = json.loads(state_path.read_text(encoding="utf-8"))
state.update(status="audit_completed_generation_failed", audit_finished_at=datetime.now(UTC).isoformat(),
             sellable_result=False, quality_best=None, production_code_changed=False,
             report="docs/reviews/savvycal-url-principale-2026-10-19.md",
             next_action="Diagnose and fix material-versus-persuasion blocking before another paid generation; preserve this baseline.")
reviews = [
    {"stage":"campaign_generation", "score":2, "calls":25, "duration_seconds":359.07,
     "facts":["Knowledge, audience research and current dossier loaded; no override", "Three drafts, one official material search and one replan", "Final draft passed automatic gates"],
     "limitations":["Critic missing_material label removes the draft; zero of one email delivered", "API failed; internal run_status needs_input", "No final HTML asset to inspect"]},
    {"stage":"execution_ui", "score":6,
     "facts":["Real frontend and proxy return 200 on desktop and mobile", "No JS errors or horizontal overflow", "Zero delivery clearly visible"],
     "limitations":["UI incorrectly says stopped before generating drafts", "Empty delivered-email average displayed as 0.0 rather than unavailable", "Long repeated date warnings"]}
]
for review in reviews:
    state["stage_reviews"] = [r for r in state["stage_reviews"] if r["stage"] != review["stage"]]
    state["stage_reviews"].append(review)
note = {"iteration":1, "execution_id":execution, "score":None, "score_status":"not scored: no delivered email",
        "comparable":True, "strengths":["Real evidence, research and narrow dossier reused", "Unverified participant claims not invented"],
        "remaining_defect":"A desired pre-signup demonstration is treated as a hard missing-material blocker despite passing draft gates.",
        "evidence":[str(run_dir / "result.json"),str(run_dir / "diagnostic-events.json"),str(run_dir / "failed-ui-check.json")],
        "next_action":state["next_action"], "sellable_result":False}
state["quality_history"] = [h for h in state.get("quality_history",[]) if h.get("execution_id") != execution] + [note]
state["call_metrics"] = {"audit_calls":17,"campaign_calls":25,"total_completed_model_calls":42,
                         "campaign_agent_groups":10,"input_tokens":1584103,"output_tokens":292661,
                         "notes":"Adapter counts including cache and internal CLI turns, not unique text or API billing."}
state["ui_verification"] = {"widths":[1440,390],"javascript_errors":[],"horizontal_overflow":False}
state_path.write_text(json.dumps(state,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"status":state["status"],"delivered":0,"model_calls":42,"email_score":None}))
