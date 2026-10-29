"""Run one explicitly selected public-API audit step per case; no decisions/retries."""
import argparse
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

batch = Path(__file__).resolve().parents[1]
repo = Path(__file__).resolve().parents[4]
parser = argparse.ArgumentParser()
parser.add_argument("action")
parser.add_argument("cases", nargs="+")
parser.add_argument("--revision", default="")
args = parser.parse_args()


def run(key):
    case = batch / key / "case.json"
    command = [str(repo / "backend/.venv/Scripts/python.exe"), "-X", "utf8",
               str(repo / "scripts/audit_brand_flow.py"), args.action, "--case", str(case)]
    if args.action == "poll":
        command += ["--wait", "45"]
    if args.revision:
        command += ["--revision", args.revision]
    result = subprocess.run(command, cwd=repo, capture_output=True, text=True, encoding="utf-8")
    out = {"case": key, "action": args.action, "exit_code": result.returncode}
    if result.returncode:
        out["error"] = (result.stderr or result.stdout)[-2000:]
        return out
    state = json.loads((case.parent / "state.json").read_text(encoding="utf-8"))
    snapshot = Path(state["last_snapshot"])
    data = json.loads(snapshot.read_text(encoding="utf-8"))
    out["snapshot"] = str(snapshot.relative_to(repo))
    if args.action == "ingest":
        out.update(documents=len(data), words=sum(d.get("word_count", 0) for d in data),
                   pages=[{"url": d.get("source_url"), "words": d.get("word_count")} for d in data])
    elif args.action == "poll":
        out.update(compilation=data["compilation"],
                   market={k:v for k,v in (data["market"] or {}).items() if k in {"kind","state","message","calls","error","started_at","finished_at"}},
                   compilation_jobs=[{k:j.get(k) for k in ["state","calls","started_at","finished_at"]} for j in data["compilation_jobs"]])
    elif args.action == "capture":
        knowledge=data.get("knowledge") or {}; audience=data.get("audiences") or {}
        out.update(knowledge_version=knowledge.get("version"), facts=knowledge.get("evidence_count"),
                   audiences=len((audience.get("map") or {}).get("segments", [])),
                   research_version=(data.get("research") or {}).get("version"),
                   dossier_status=(data.get("relevance") or {}).get("status"))
    elif args.action == "select-first":
        out["selected"] = data["segment"]["name"]
        out["assessment"] = data["segment"].get("assessment")
    elif args.action == "advice":
        out.update(forecast=data["forecast"], advice={k:v for k,v in data["advice"].items()
                   if k in {"can_generate","override_required","readiness","reasons","user_message"}})
    else:
        out["result"] = {k:v for k,v in data.items() if k in {"id","kind","state","message","error","version","knowledge_version"}}
    return out


with ThreadPoolExecutor(max_workers=2) as pool:
    futures = [pool.submit(run, key) for key in args.cases]
    for future in as_completed(futures):
        print(json.dumps(future.result(), ensure_ascii=False), flush=True)
