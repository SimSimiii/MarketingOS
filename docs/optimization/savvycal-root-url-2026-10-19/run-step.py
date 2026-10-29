"""Submit exactly one command to the current-code audit worker, then observe it."""
import argparse
import json
import time
from pathlib import Path

root = Path(__file__).parent
parser = argparse.ArgumentParser()
parser.add_argument("tool", choices=["audit", "optimizer", "stop"])
parser.add_argument("action", nargs="?", default="stop")
parser.add_argument("--wait", type=int, default=0)
parser.add_argument("--revision", default="")
args = parser.parse_args()
pending = [p for p in (root / "commands").glob("*.json") if not (root / "responses" / p.name).exists()]
if pending:
    raise SystemExit("Existing command pending; inspect its response, do not enqueue another: " + pending[0].name)
index = len(list((root / "commands").glob("*.json"))) + 1
filename = f"{index:03}-{args.tool}-{args.action}.json"
command = {"tool": args.tool, "action": args.action, "wait": args.wait, "revision": args.revision}
path = root / "commands" / filename
temp = path.with_suffix(".tmp")
temp.write_text(json.dumps(command), encoding="utf-8")
temp.replace(path)
response = root / "responses" / filename
deadline = time.monotonic() + 55
while not response.exists() and time.monotonic() < deadline:
    time.sleep(0.5)
if not response.exists():
    print(json.dumps({"pending": filename, "response": str(response)}))
else:
    result = json.loads(response.read_text())
    output = response.with_suffix(".txt")
    print(json.dumps({**result, "output_file": str(output)}, ensure_ascii=False))
    if output.exists() and args.action != "advice":
        print(output.read_text(encoding="utf-8")[:3500])
