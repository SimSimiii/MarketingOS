"""Read saved job counters only; never calls an API or a model."""
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent
state = json.loads((ROOT / "state.json").read_text(encoding="utf-8"))
terminal = []
for file in sorted((ROOT / "steps").glob("*-poll.json")):
    market = json.loads(file.read_text(encoding="utf-8")).get("market") or {}
    if market.get("state") == "done":
        terminal.append((file, market))

steps = []
missing = []
for key in ("scan-functional-rivals", "map-functional-catalogue", "scan-corrected-rationale-refs",
            "scan-verify-source-cache", "scan-rival-price-scope", "research-publication-grounding",
            "dossier-functional-reliability"):
    entry = state.get("steps", {}).get(key)
    if not entry:
        continue
    launch = Path(entry["snapshot"])
    if not launch.is_absolute():
        launch = ROOT.parents[3] / launch
    launched = json.loads(launch.read_text(encoding="utf-8"))
    match = next(((file, job) for file, job in terminal
                  if job.get("started_at") == launched.get("started_at")), None)
    if not match:
        missing.append({"step": key, "reason": "Terminal counters not captured (or operation still running)."})
        continue
    file, job = match
    elapsed = (datetime.fromisoformat(job["finished_at"].replace("Z", "+00:00"))
               - datetime.fromisoformat(job["started_at"].replace("Z", "+00:00"))).total_seconds()
    steps.append({"step": key, "calls": job["calls"], "reported_tokens": job["input_tokens"] + job["output_tokens"],
                  "cache_read_tokens": job.get("cache_read_tokens", 0), "seconds": round(elapsed, 2),
                  "snapshot": str(file.relative_to(ROOT))})

diagnostic = ROOT / "functional-rationale-diagnostic.json"
if diagnostic.exists():
    usage = json.loads(diagnostic.read_text(encoding="utf-8"))["usage"]
    steps.append({"step": "rationale_diagnostic", "calls": len(usage["calls"]),
                  "reported_tokens": sum(usage.get(key, 0) for key in
                       ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")),
                  "snapshot": diagnostic.name})

first_launch = ROOT.parents[3] / state['steps']['scan-functional-rivals']['snapshot']
started = datetime.fromisoformat(json.loads(first_launch.read_text(encoding='utf-8'))['started_at'].replace('Z', '+00:00'))
for entry in state.get('runs', []):
    if datetime.fromisoformat(entry['launched_at'].replace('Z', '+00:00')) < started:
        continue
    run = ROOT / 'runs' / entry['execution_id']
    if not (run / 'result.json').exists() or not (run / 'logs.json').exists():
        missing.append({'step': entry['execution_id'], 'reason': 'Campaign capture pending.'})
        continue
    result = json.loads((run / 'result.json').read_text(encoding='utf-8'))
    logs = json.loads((run / 'logs.json').read_text(encoding='utf-8'))
    steps.append({'step': 'email_' + entry['execution_id'],
                  'calls': sum(log.get('event_type') == 'model_call_finished' for log in logs),
                  'agent_groups': len(result.get('agent_executions', [])),
                  'reported_tokens': result['total_input_tokens'] + result['total_output_tokens'],
                  'cache_read_tokens': result.get('total_cache_read_tokens', 0),
                  'pipeline_status': (result.get('result') or {}).get('run_status'),
                  'needs_review': result.get('needs_review'), 'snapshot': str((run / 'result.json').relative_to(ROOT))})

report = {"completed_captured_steps": steps, "known_completed_calls": sum(step["calls"] for step in steps),
          "known_reported_tokens": sum(step["reported_tokens"] for step in steps), "missing_counters": missing,
          "scope": "Functional follow-up including diagnostics and both emails. Completed application model calls, not grouped role rows. Cached input included; not uncached tokens, invoice or conversions. One completed scan's process-local terminal counters were lost."}
(ROOT / "functional-usage-summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({key: report[key] for key in ("known_completed_calls", "known_reported_tokens", "missing_counters")}))
