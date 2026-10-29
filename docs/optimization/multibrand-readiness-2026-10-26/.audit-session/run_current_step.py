"""Submit one explicit audit action to each current-code ASGI worker."""
import argparse
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

batch = Path(__file__).resolve().parents[1]
repo = Path(__file__).resolve().parents[4]
skill = Path("C:/Users/oussa/.codex/skills/marketingos-brand-audit/scripts/audit_session.py")
parser = argparse.ArgumentParser()
parser.add_argument("action")
parser.add_argument("cases", nargs="+")
parser.add_argument("--revision", default="")
args = parser.parse_args()
if len(args.cases) > 2:
    raise SystemExit("Select at most two cases; inspect active jobs before admitting another")


def run(key):
    case = batch / key / "case.json"
    command = [str(repo / "backend/.venv/Scripts/python.exe"), "-X", "utf8", str(skill),
               "audit", args.action, "--case", str(case)]
    if args.revision:
        command += ["--revision", args.revision]
    if args.action == "poll":
        command += ["--wait", "45"]
    result = subprocess.run(command, cwd=repo, capture_output=True, text=True, encoding="utf-8")
    out = {"case": key, "action": args.action, "exit_code": result.returncode}
    if result.returncode:
        out["error"] = (result.stderr or result.stdout)[-1800:]
        return out
    response = json.loads(result.stdout.splitlines()[0])
    if not response.get("ok"):
        out.update(response)
        return out
    state = json.loads((case.parent / "state.json").read_text(encoding="utf-8"))
    path = Path(state["last_snapshot"])
    data = json.loads(path.read_text(encoding="utf-8"))
    out["snapshot"] = str(path.relative_to(repo))
    if args.action == "poll":
        out.update(compilation=data["compilation"], market={k: v for k, v in (data["market"] or {}).items()
                   if k in {"kind", "state", "message", "calls", "error"}},
                   compilation_jobs=[{k: j.get(k) for k in ["state", "calls", "started_at", "finished_at"]}
                                     for j in data["compilation_jobs"]])
    elif args.action == "capture":
        knowledge = data.get("knowledge") or {}
        audience = (data.get("audiences") or {}).get("map") or {}
        out.update(knowledge_version=knowledge.get("version"), facts=knowledge.get("evidence_count"),
                   segments=[s["name"] for s in audience.get("segments", [])],
                   research_version=(data.get("research") or {}).get("version"),
                   dossier_status=(data.get("relevance") or {}).get("status"))
    elif args.action == "select-first":
        segment = data["segment"]
        out.update(name=segment["name"], researchable=segment.get("researchable"),
                   assessment=segment.get("assessment"))
    elif args.action == "advice":
        advice = data["advice"]
        out.update(forecast=data["forecast"], advice={k: advice.get(k) for k in
                   ["readiness", "override_required", "can_generate", "reasons", "dossier_status", "user_message"]})
    else:
        out["result"] = {k: v for k, v in data.items()
                         if k in {"state", "message", "error", "version", "knowledge_version", "id", "kind"}}
    return out


with ThreadPoolExecutor(max_workers=2) as pool:
    for future in as_completed([pool.submit(run, key) for key in args.cases]):
        print(json.dumps(future.result(), ensure_ascii=False), flush=True)
