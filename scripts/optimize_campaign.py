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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["inspect", "run", "resume", "compare"])
    parser.add_argument("--case", type=Path, default=DEFAULT_CASE)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--max-runs", type=int, default=None,
                        help="Optional explicit total generation cap; unlimited by default")
    parser.add_argument("--timeout-seconds", type=int, default=2700)
    parser.add_argument("--poll-seconds", type=int, default=10)
    parser.add_argument("--before", help="First execution ID for compare")
    parser.add_argument("--after", help="Second execution ID for compare")
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
                "agent_calls": len(result.get("agent_executions") or []),
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
            save(directory / f"{name}.json", api(base, path, token))
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
