"""Capture an email at a real 375px CSS viewport using Edge DevTools."""

import asyncio
import base64
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.request import urlopen

import websockets


EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
PORT = 9223


async def capture(path: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="marketingos-mobile-", ignore_cleanup_errors=True) as profile:
        process = subprocess.Popen(
            [
                str(EDGE), "--headless=new", "--disable-gpu", "--no-first-run",
                "--remote-allow-origins=*", f"--remote-debugging-port={PORT}",
                f"--user-data-dir={profile}", "about:blank",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        try:
            for _ in range(100):
                try:
                    with urlopen(f"http://127.0.0.1:{PORT}/json/list", timeout=1) as response:
                        pages = json.load(response)
                    page = next(item for item in pages if item["type"] == "page")
                    break
                except (OSError, StopIteration):
                    time.sleep(0.1)
            else:
                raise RuntimeError("Edge DevTools did not start")

            async with websockets.connect(page["webSocketDebuggerUrl"], max_size=10_000_000) as ws:
                next_id = 0

                async def call(method: str, params: dict | None = None) -> dict:
                    nonlocal next_id
                    next_id += 1
                    await ws.send(json.dumps({"id": next_id, "method": method, "params": params or {}}))
                    while True:
                        message = json.loads(await ws.recv())
                        if message.get("id") == next_id:
                            if "error" in message:
                                raise RuntimeError(str(message["error"]))
                            return message.get("result", {})

                await call("Emulation.setDeviceMetricsOverride", {
                    "width": 375, "height": 900, "deviceScaleFactor": 1, "mobile": True,
                })
                await call("Page.navigate", {"url": path.resolve().as_uri()})
                await asyncio.sleep(1)
                metrics = await call("Runtime.evaluate", {
                    "expression": "JSON.stringify({innerWidth, clientWidth: document.documentElement.clientWidth, scrollWidth: document.documentElement.scrollWidth})",
                    "returnByValue": True,
                })
                dimensions = json.loads(metrics["result"]["value"])
                screenshot = await call("Page.captureScreenshot", {"format": "png"})
                path.with_name("email-mobile-true.png").write_bytes(base64.b64decode(screenshot["data"]))
                path.with_name("email-mobile-metrics.json").write_text(
                    json.dumps(dimensions, indent=2) + "\n", encoding="utf-8"
                )
                print(path, dimensions)
        finally:
            process.terminate()
            process.wait(timeout=5)


if __name__ == "__main__":
    asyncio.run(capture(Path(sys.argv[1])))
