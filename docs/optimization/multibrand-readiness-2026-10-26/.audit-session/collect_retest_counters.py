"""Read durable receipts only; no network, models, or case-state mutation."""
import json
from datetime import datetime
from pathlib import Path

root = Path(__file__).resolve().parents[1]
jobs = {}
runs = []
for case in ("cabaia", "papier", "systeme", "rtings"):
    directory = root / case
    for path in sorted((directory / "steps").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            continue
        candidates = [("knowledge", job) for job in data.get("compilation_jobs", [])]
        if isinstance(data.get("market"), dict):
            candidates.append((data["market"].get("kind", "market"), data["market"]))
        if "kind" in data and "calls" in data:
            candidates.append((data["kind"], data))
        for kind, job in candidates:
            if not job.get("started_at") or "calls" not in job:
                continue
            key = (case, kind, job["started_at"])
            previous = jobs.get(key)
            terminal = job.get("state") not in {"running", "pending", "queued"}
            if previous and (previous["calls"] > job["calls"] or
                             previous["terminal_receipt"] and not terminal):
                continue
            jobs[key] = {"case": case, "kind": kind, "started_at": job["started_at"],
                         "state": job.get("state"), "calls": job["calls"],
                         "terminal_receipt": terminal, "snapshot": str(path.relative_to(root))}
    scores = {}
    for path in directory.glob("email-review-*.json"):
        review = json.loads(path.read_text(encoding="utf-8"))
        scores[review.get("execution_id")] = review.get("score")
    for path in sorted((directory / "runs").glob("*/result.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        logs_path = path.with_name("logs.json")
        logs = json.loads(logs_path.read_text(encoding="utf-8")) if logs_path.exists() else []
        duration = None
        if data.get("started_at") and data.get("completed_at"):
            duration = round((datetime.fromisoformat(data["completed_at"].replace("Z", "+00:00")) -
                              datetime.fromisoformat(data["started_at"].replace("Z", "+00:00"))).total_seconds(), 2)
        runs.append({"case": case, "execution_id": data["id"], "status": data["status"],
                     "outcome": data.get("outcome_status"), "needs_review": data.get("needs_review"),
                     "calls": sum(log.get("event_type") == "model_call_finished" for log in logs),
                     "seconds": duration, "score": scores.get(data["id"]),
                     "delivered": sum(asset.get("asset_type") == "email" for asset in data.get("assets", [])),
                     "result": str(path.relative_to(root))})
job_list = sorted(jobs.values(), key=lambda job: (job["case"], job["started_at"]))
summary = {"email_attempts": len(runs), "email_assets": sum(run["delivered"] for run in runs),
           "email_model_calls_finished": sum(run["calls"] for run in runs),
           "upstream_model_calls_observed_at_least": sum(job["calls"] for job in job_list),
           "upstream_without_terminal_receipt": [job for job in job_list if not job["terminal_receipt"]],
           "limits": "Interrupted in-process jobs may have finished more calls after their last snapshot; upstream total is a lower bound. Separate profile/isolation probes are excluded.",
           "upstream_jobs": job_list, "email_runs": runs}
(root / "retest-counters.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({key: value for key, value in summary.items() if key not in {
    "upstream_jobs", "email_runs", "upstream_without_terminal_receipt", "limits"}}))
