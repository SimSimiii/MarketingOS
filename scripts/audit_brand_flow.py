"""Capture a brand-to-campaign audit through the public API, one step at a time.

Mutation commands are explicit and never repeated automatically. `poll` and
`capture` only read. Credentials come from MARKETINGOS_TOKEN and are never saved.
"""
import argparse
import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["create", "ingest", "compile", "derive", "scan", "map", "select-first", "research", "dossier", "campaign", "policy", "advice", "poll", "capture"])
    parser.add_argument("--case", type=Path, required=True, help="Existing case.json with name and website_url")
    parser.add_argument("--wait", type=int, default=45, help="Bounded poll duration, at most 55 seconds")
    parser.add_argument("--revision", default="", help="Explicit new attempt label after a recorded diagnosis; preserves the initial step")
    args = parser.parse_args()
    case = json.loads(args.case.read_text(encoding="utf-8"))
    directory = args.case.parent
    state_path = directory / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {"runs": [], "steps": {}}
    state.setdefault("steps", {})
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")

    def api(path, body=None, method=None):
        headers = {"Accept": "application/json"}
        if os.getenv("MARKETINGOS_TOKEN"):
            headers["Authorization"] = "Bearer " + os.environ["MARKETINGOS_TOKEN"]
        data = None if body is None else json.dumps(body).encode("utf-8")
        if data is not None:
            headers["Content-Type"] = "application/json"
        req = Request(case.get("api_base", "http://localhost:8000") + "/api" + path,
                      data=data, headers=headers, method=method or ("GET" if body is None else "POST"))
        try:
            with urlopen(req, timeout=180 if args.action == "ingest" else 30) as response:
                return json.load(response)
        except HTTPError as error:
            raise RuntimeError(f"HTTP {error.code}: {error.read().decode()[:1200]}") from error

    action = args.action
    step_key = action + ("-" + args.revision if args.revision else "")
    brand = case.get("brand_id")
    if step_key in state["steps"] and action not in {"poll", "capture", "advice"}:
        raise SystemExit("Step already recorded. Inspect its snapshot; do not launch a duplicate blindly.")
    if action == "create":
        value = api("/brands", {"name": case["name"], "website_url": case["website_url"]})
        case["brand_id"] = value["id"]
        save(args.case, case)
    elif not brand:
        raise SystemExit("Create the brand first.")
    elif action == "ingest":
        value = api("/knowledge", {"brand_id": brand, "url": case["website_url"]})
    elif action == "compile":
        value = api(f"/brands/{brand}/knowledge/compile",
                    {"model": case["compile_model"]} if case.get("compile_model") else {})
    elif action == "derive":
        value = api(f"/market/{brand}/capability-profile/derive", {})
    elif action == "select-first":
        audience_map = api(f"/market/{brand}/audience")
        segments = (audience_map.get("map") or {}).get("segments") or []
        if not segments:
            raise SystemExit("No mapped audience exists; complete the map job and inspect its status.")
        value = {"index": 0, "segment": segments[0]}
        case["audience_segment"] = segments[0]["name"]
        save(args.case, case)
    elif action == "campaign":
        if not case.get("campaign_request"):
            raise SystemExit("Record campaign_request in case.json before creating the campaign.")
        value = api("/campaigns", {
            "name": case.get("campaign_name", "One-email audit"),
            "request": case["campaign_request"], "brand_id": brand,
            "product_url": case["website_url"], "audience_segment": case["audience_segment"],
            "policy_preset": case.get("policy_preset", "balanced"),
            "strategy_mode": case.get("strategy_mode", "auto"),
            "intent": case.get("intent"),
            **({"model_overrides": case["model_overrides"]} if case.get("model_overrides") else {}),
            **{key: case[key] for key in ("sender_name", "sender_role") if case.get(key)},
        })
        case["campaign_id"] = value["id"]
        save(args.case, case)
    elif action == "policy":
        if "model_overrides" not in case:
            raise SystemExit("Record explicit model_overrides before updating the campaign.")
        value = api(f"/campaigns/{case['campaign_id']}/policy",
                    {"model_overrides": case["model_overrides"]}, method="PUT")
    elif action == "advice":
        campaign = case["campaign_id"]
        value = {"forecast": api(f"/campaigns/{campaign}/forecast"),
                 "advice": api(f"/campaigns/{campaign}/generation-advice")}
    elif action in {"scan", "map", "research", "dossier"}:
        paths = {"scan": "scan", "map": "audience/map", "research": "audience/research", "dossier": "audience/relevance"}
        body = {}
        if action == "scan":
            body = case.get("market_scan_options", {})
        if action == "map":
            body = case.get("audience_map_options", {})
        if action == "dossier":
            body = dict(case.get("dossier_options", {}))
        if action in {"research", "dossier"}:
            body["segment"] = case["audience_segment"]
            if model := case.get(action + "_model"):
                body["model"] = model
        value = api(f"/market/{brand}/{paths[action]}", body)
    elif action == "poll":
        deadline = time.monotonic() + min(max(args.wait, 0), 55)
        while True:
            value = {"compilation": api(f"/brands/{brand}/knowledge/compile"),
                     "market": api(f"/market/{brand}/job"),
                     "compilation_jobs": [j for j in api("/knowledge/jobs") if j["brand_id"] == brand]}
            running = value["compilation"]["state"] == "running" or (value["market"] or {}).get("state") in {"running", "pending", "queued"}
            if not running or time.monotonic() >= deadline:
                break
            time.sleep(min(5, max(0, deadline - time.monotonic())))
    else:
        value = {}
        endpoints = {"brand": f"/brands/{brand}", "documents": f"/knowledge?brand_id={brand}",
                     "knowledge": f"/brands/{brand}/knowledge", "market": f"/market/{brand}",
                     "rivals": f"/market/{brand}/rivals", "audiences": f"/market/{brand}/audience"}
        if case.get("audience_segment"):
            query = urlencode({"segment": case["audience_segment"]})
            endpoints.update(research=f"/market/{brand}/audience/research/latest?{query}",
                             relevance=f"/market/{brand}/audience/relevance/status?{query}")
        for key, path in endpoints.items():
            try:
                value[key] = api(path)
            except RuntimeError as error:
                value[key] = {"capture_error": str(error)}
    snapshot = directory / "steps" / f"{stamp}-{action}.json"
    save(snapshot, value)
    if action not in {"poll", "capture", "advice"}:
        state["steps"][step_key] = {"started_at": stamp, "snapshot": str(snapshot)}
    state["last_snapshot"] = str(snapshot)
    save(state_path, state)
    if action == "ingest":
        print(json.dumps({"documents": len(value), "pages": [{k: d.get(k) for k in ("id", "source_url", "word_count")} for d in value]}, indent=2))
    elif action == "poll":
        print(json.dumps({"compilation": value["compilation"], "market": {k: v for k, v in (value["market"] or {}).items() if k in {"kind", "state", "message", "calls", "error", "summary"}}, "compilation_jobs": [{k: j.get(k) for k in ("state", "calls", "input_tokens", "output_tokens")} for j in value["compilation_jobs"]]}, indent=2))
    elif action == "capture":
        print("Captured: " + ", ".join(value))
    else:
        print(json.dumps(value, indent=2))
    print("Snapshot: " + str(snapshot))


if __name__ == "__main__":
    main()
