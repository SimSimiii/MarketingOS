"""Capture real, reproducible campaign runs through MarketingOS's public API."""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASE = ROOT / "docs" / "optimization" / "orqagent" / "case.json"
TERMINAL = {"completed", "degraded", "failed", "cancelled"}


def api(base, path, token=None, method="GET", data=None):
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = None if data is None else json.dumps(data).encode("utf-8")
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = Request(base.rstrip("/") + "/api" + path, data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=30) as response:
            return json.load(response)
    except HTTPError as exc:
        raise RuntimeError(f"{method} {path}: HTTP {exc.code}: {exc.read().decode()[:500]}") from exc


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def snapshot(base, token, directory, campaign_id, execution_id):
    endpoints = {
        "campaign": f"/campaigns/{campaign_id}",
        "forecast": f"/campaigns/{campaign_id}/forecast",
        "result": f"/executions/{execution_id}/result",
        "logs": f"/executions/{execution_id}/logs?include_debug=true",
        "timeline": f"/executions/{execution_id}/timeline",
    }
    for name, path in endpoints.items():
        try:
            save(directory / f"{name}.json", api(base, path, token))
        except (RuntimeError, URLError) as exc:
            save(directory / f"{name}.error.json", {"error": str(exc)})


def run_summary(directory, entry):
    """Return a factual handoff from saved files without making API or model calls."""
    execution_id = entry["execution_id"]
    run_dir = directory / "runs" / execution_id
    result_path = run_dir / "result.json"
    summary = {
        "execution_id": execution_id,
        "status": entry.get("status"),
        "result_dir": str(run_dir) if run_dir.exists() else None,
        "pending_capture": not bool(entry.get("result_dir")),
    }
    if not result_path.exists():
        summary["result_available"] = False
        error_path = run_dir / "result.error.json"
        if error_path.exists():
            summary["capture_error"] = json.loads(error_path.read_text(encoding="utf-8")).get("error")
        return summary

    result = json.loads(result_path.read_text(encoding="utf-8"))
    report = (result.get("result") or {}).get("report") or {}
    summary.update({
        "result_available": True,
        "status": result.get("status", summary["status"]),
        "error_message": result.get("error_message"),
        "outcome_status": result.get("outcome_status") or (result.get("result") or {}).get("run_status"),
        "needs_review": result.get("needs_review"),
        "review_reasons": result.get("review_reasons") or [],
        "estimated_cost_usd": result.get("estimated_cost_usd"),
        "agent_calls": None,
        "model_calls": None,
        "agent_groups": len(result.get("agent_executions") or []),
        "total_input_tokens": result.get("total_input_tokens"),
        "total_output_tokens": result.get("total_output_tokens"),
        "delivered": report.get("delivered"),
        "promised": report.get("promised"),
        "contract_violations": report.get("contract_violations") or [],
        "limiting_gaps": report.get("limiting_gaps") or [],
        "what_would_help_most": report.get("what_would_help_most"),
        "assets": [
            {"title": asset.get("title"), "result_path": str(result_path)}
            for asset in result.get("assets") or []
        ],
        "emails": [
            {
                "position": email.get("position"),
                "subject": email.get("subject"),
                "pull": email.get("pull"),
                "clean": email.get("clean"),
                "understood": email.get("understood"),
                "relevant": email.get("relevant"),
                "evidence_assigned": email.get("evidence_assigned") or [],
                "evidence_spent": email.get("evidence_spent") or [],
                "unresolved": email.get("unresolved") or [],
                "reader_doubts": [
                    verdict["biggest_doubt"] for verdict in email.get("reader_verdicts") or []
                    if verdict.get("biggest_doubt")
                ],
            }
            for email in report.get("emails") or []
        ],
    })
    logs_path = run_dir / "logs.json"
    if logs_path.exists():
        logs = json.loads(logs_path.read_text(encoding="utf-8"))
        finished = sum(log.get("event_type") == "model_call_finished" for log in logs)
        summary["model_calls"] = finished if finished or not summary["agent_groups"] else None
        summary["agent_calls"] = summary["model_calls"]
        summary["error_logs"] = [
            {"step": log.get("step"), "message": log.get("message")}
            for log in logs if log.get("level") == "error"
        ][-5:]
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["inspect", "run", "resume", "compare", "summary"])
    parser.add_argument("--case", type=Path, default=DEFAULT_CASE)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--max-runs", type=int, default=None,
                        help="Optional explicit total generation cap; unlimited by default")
    parser.add_argument("--timeout-seconds", type=int, default=2700)
    parser.add_argument("--poll-seconds", type=int, default=10)
    parser.add_argument("--before", help="First execution ID for compare")
    parser.add_argument("--after", help="Second execution ID for compare")
    parser.add_argument("--execution-id", help="Run to summarize; defaults to the latest recorded run")
    args = parser.parse_args()
    args.case = args.case.resolve()
    if (args.max_runs is not None and args.max_runs < 1) or args.timeout_seconds < 30 or args.poll_seconds < 1:
        parser.error("limits must be positive; timeout must be at least 30 seconds")
    case = json.loads(args.case.read_text(encoding="utf-8"))
    base = args.base_url
    token = os.environ.get("MARKETINGOS_TOKEN")
    brand_id = case["brand_id"]
    campaign_id = case["campaign_id"]
    directory = args.case.parent
    state_path = directory / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {"runs": []}
    # Older/manual case state may predate durable run capture. Preserve every
    # quality field it contains and add only the runner's missing collection.
    state.setdefault("runs", [])

    if args.action == "summary":
        matches = [run for run in state["runs"] if run["execution_id"] == args.execution_id] if args.execution_id else state["runs"][-1:]
        if len(matches) != 1:
            raise RuntimeError("Expected one recorded run to summarize")
        print(json.dumps(run_summary(directory, matches[0]), indent=2, ensure_ascii=False))
        return 0

    if args.action == "compare":
        if not args.before or not args.after:
            parser.error("compare requires --before and --after execution IDs")
        def summary(execution_id):
            path = directory / "runs" / execution_id / "result.json"
            result = json.loads(path.read_text(encoding="utf-8"))
            report = (result.get("result") or {}).get("report") or {}
            return {
                "execution_id": execution_id,
                "status": result["status"],
                "error_message": result.get("error_message"),
                "started_at": result.get("started_at"),
                "completed_at": result.get("completed_at"),
                "estimated_cost_usd": result.get("estimated_cost_usd"),
                "total_input_tokens": result.get("total_input_tokens"),
                "total_output_tokens": result.get("total_output_tokens"),
                "agent_calls": run_summary(directory, {"execution_id": execution_id})["model_calls"],
                "agent_groups": len(result.get("agent_executions") or []),
                "report": report,
                "assets": [
                    {"title": asset["title"], "content": asset["content"],
                     "content_html_length": len(asset.get("content_html") or "")}
                    for asset in result.get("assets") or []
                ],
            }
        comparison = {"before": summary(args.before), "after": summary(args.after)}
        output = directory / f"compare-{args.before[:8]}-{args.after[:8]}.json"
        save(output, comparison)
        print(f"Saved {output}")
        return 0

    if args.action == "inspect":
        for name, path in {
            "brand": f"/brands/{brand_id}",
            "knowledge": f"/brands/{brand_id}/knowledge",
            "audience": f"/market/{brand_id}/audience",
            "campaign": f"/campaigns/{campaign_id}",
            "forecast": f"/campaigns/{campaign_id}/forecast",
        }.items():
            try:
                save(directory / f"{name}.json", api(base, path, token))
            except RuntimeError as exc:
                if name not in {"knowledge", "audience"} or "HTTP 404:" not in str(exc):
                    raise
                save(directory / f"{name}.error.json", {"error": str(exc)})
                print(f"Context unavailable ({name}): {exc}")
        print(f"Saved context in {directory}")
        return 0

    campaign = api(base, f"/campaigns/{campaign_id}", token)
    if campaign["brand_id"].replace("-", "") != brand_id.replace("-", ""):
        raise RuntimeError("case campaign belongs to another brand")
    if args.action == "run":
        if any(not run.get("result_dir") for run in state["runs"]):
            raise RuntimeError("A recorded run is in progress; use resume")
        if args.max_runs is not None and len(state["runs"]) >= args.max_runs:
            raise RuntimeError("Generation limit reached; raise --max-runs deliberately for a new cycle")
        started = api(base, f"/campaigns/{campaign_id}/start", token, "POST", {})
        entry = {
            "execution_id": started["id"],
            "campaign_id": campaign_id,
            "status": "running",
            "launched_at": datetime.now(timezone.utc).isoformat(),
            "code_revision": os.environ.get("OPTIMIZATION_REVISION", "working-tree"),
        }
        state["runs"].append(entry)
        save(state_path, state)
        print(f"Started {entry['execution_id']}", flush=True)
    else:
        pending = [run for run in state["runs"] if not run.get("result_dir")]
        if len(pending) != 1:
            raise RuntimeError("Expected exactly one recorded running execution")
        entry = pending[0]

    execution_id = entry["execution_id"]
    deadline = time.monotonic() + args.timeout_seconds
    while True:
        status = api(base, f"/executions/{execution_id}/status", token)
        entry["status"] = status["status"]
        entry["outcome_status"] = status.get("outcome_status")
        entry["needs_review"] = status.get("needs_review", False)
        entry["review_reasons"] = status.get("review_reasons") or []
        entry["last_checked_at"] = datetime.now(timezone.utc).isoformat()
        save(state_path, state)
        if status["status"] in TERMINAL:
            break
        if time.monotonic() >= deadline:
            api(base, f"/executions/{execution_id}/cancel", token, "POST", {})
            entry["timeout_cancel_requested"] = True
            save(state_path, state)
            print("Timeout: cancellation requested; run resume to collect terminal result", file=sys.stderr)
            return 2
        time.sleep(args.poll_seconds)
    run_dir = directory / "runs" / execution_id
    snapshot(base, token, run_dir, campaign_id, execution_id)
    entry["result_dir"] = str(run_dir.relative_to(ROOT))
    entry["estimated_cost_usd"] = status.get("estimated_cost_usd")
    entry["completed_at"] = status.get("completed_at")
    save(state_path, state)
    print(json.dumps(entry, indent=2), flush=True)
    return 0 if status["status"] in {"completed", "degraded"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
