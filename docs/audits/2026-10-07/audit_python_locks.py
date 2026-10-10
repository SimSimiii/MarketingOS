"""Read-only advisory check against PyPI's release JSON for the three locks.

No dependency installation or provider calls. Emits JSON including failed
lookups; an unavailable advisory lookup must not be reported as a clean package.
Run from the repository root with backend/.venv/Scripts/python.exe.
"""

import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[3]
LOCKS = ("requirements.txt", "requirements.lock", "requirements-worker.txt")


def inspect_release(item):
    (name, version), locks = item
    result = {"name": name, "version": version, "locks": sorted(locks)}
    url = f"https://pypi.org/pypi/{quote(name, safe='')}/{quote(version, safe='')}/json"
    try:
        request = Request(url, headers={"User-Agent": "MarketingOS-dependency-audit/1.0"})
        with urlopen(request, timeout=20) as response:
            payload = json.load(response)
        if "vulnerabilities" not in payload:
            return {**result, "status": "unverified", "reason": "Advisory field absent"}
        advisories = [{key: value for key, value in advisory.items()
                       if key in {"id", "aliases", "fixed_in", "link", "withdrawn"}}
                      for advisory in payload["vulnerabilities"] if not advisory.get("withdrawn")]
        return {**result, "status": "advisories" if advisories else "clear", "advisories": advisories}
    except (HTTPError, URLError, TimeoutError, ValueError) as error:
        return {**result, "status": "unverified", "reason": str(error)}


def audit():
    releases = {}
    for lock in LOCKS:
        for line in (ROOT / "backend" / lock).read_text(encoding="utf-8").splitlines():
            if match := re.match(r"^([A-Za-z0-9_.-]+)(?:\[[^\]]+\])?==([^\s\\]+)", line):
                releases.setdefault(match.groups(), set()).add(lock)
    with ThreadPoolExecutor(max_workers=6) as workers:
        results = list(workers.map(inspect_release, sorted(releases.items())))
    return {
        "source": "https://docs.pypi.org/api/json/#get-a-release",
        "scope": "Release advisories known to PyPI, not a complete supply-chain or runtime audit",
        "checked_releases": len(results),
        "clear": sum(result["status"] == "clear" for result in results),
        "flagged": [result for result in results if result["status"] == "advisories"],
        "unverified": [result for result in results if result["status"] == "unverified"],
    }


if __name__ == "__main__":
    result = audit()
    print(json.dumps(result, indent=2))
    sys.exit(1 if result["flagged"] or result["unverified"] else 0)
