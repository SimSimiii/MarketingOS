"""Current-code API audit session, without a TCP server or application lifespan.

Run from backend/. Existing audit helpers run unchanged in one thread; their
urlopen calls are carried to the actual app via HTTPX ASGITransport on this
process's persistent asyncio loop. Handlers, providers, validation and persistence
are real. No fixture, request override, init_db, reaper or lifespan is invoked.
Only one command at a time writes case state. Immutable command/response files
let the operator inspect every phase before authorising the next one.
"""
import asyncio
import importlib.util
import io
import json
import os
import sys
import traceback
from contextlib import redirect_stdout
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError

import httpx

sys.path.insert(0, str(Path.cwd()))
from app.main import app

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
CASE = ROOT / "case.json"


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, REPO / "scripts" / filename)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


async def main():
    audit = module("audit_helper", "audit_brand_flow.py")
    optimizer = module("optimizer_helper", "optimize_campaign.py")
    loop = asyncio.get_running_loop()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                 base_url="http://127.0.0.1:8000", timeout=180) as client:
        async def request(req):
            response = await client.request(req.get_method(), req.full_url,
                                            content=req.data, headers=dict(req.header_items()))
            if response.status_code >= 400:
                raise HTTPError(req.full_url, response.status_code, response.reason_phrase,
                                response.headers, io.BytesIO(response.content))
            return io.BytesIO(response.content)

        def urlopen(req, timeout=None):
            # The caller sleeps/polls in its own thread, keeping background
            # jobs and model subprocesses alive on the application's loop.
            return asyncio.run_coroutine_threadsafe(request(req), loop).result(timeout=timeout)

        audit.urlopen = optimizer.urlopen = urlopen
        response = await client.get("/api/health")
        response.raise_for_status()
        save(ROOT / "worker-ready.json", {"pid": os.getpid(), "started_at": datetime.now(UTC).isoformat(),
             "transport": "ASGITransport, no lifespan, no listener", "health": response.json()})
        print("Current-code API audit worker ready.", flush=True)
        (ROOT / "commands").mkdir(exist_ok=True)
        while True:
            pending = [p for p in sorted((ROOT / "commands").glob("*.json"))
                       if not (ROOT / "responses" / p.name).exists()]
            if not pending:
                await asyncio.sleep(0.5)
                continue
            path = pending[0]
            command = json.loads(path.read_text(encoding="utf-8"))
            if command["tool"] == "stop":
                save(ROOT / "responses" / path.name, {"ok": True, "stopped": True})
                break

            def execute():
                output = io.StringIO()
                old_args = sys.argv
                try:
                    with redirect_stdout(output):
                        tool = audit if command["tool"] == "audit" else optimizer
                        sys.argv = [str(tool.__file__), command["action"], "--case", str(CASE)]
                        if command["tool"] == "audit":
                            sys.argv += ["--wait", str(command.get("wait", 0))]
                            if command.get("revision"):
                                sys.argv += ["--revision", command["revision"]]
                        else:
                            sys.argv += ["--base-url", "http://127.0.0.1:8000"]
                        tool.main()
                    return {"ok": True}
                except BaseException as exc:
                    return {"ok": False, "error": str(exc), "traceback": traceback.format_exc()}
                finally:
                    sys.argv = old_args
                    (ROOT / "responses").mkdir(exist_ok=True)
                    (ROOT / "responses" / (path.stem + ".txt")).write_text(output.getvalue(), encoding="utf-8")

            result = await asyncio.to_thread(execute)
            result.update(command=command, completed_at=datetime.now(UTC).isoformat())
            save(ROOT / "responses" / path.name, result)
            print(json.dumps({"command": path.name, "ok": result["ok"],
                              "error": result.get("error")}), flush=True)


asyncio.run(main())
