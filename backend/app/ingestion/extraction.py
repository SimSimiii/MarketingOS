import asyncio
import json
import sys
from threading import BoundedSemaphore

from app.ingestion.exceptions import LoaderError

_workers = BoundedSemaphore(2)


async def extract_document(kind: str, source: str) -> dict:
    if not _workers.acquire(blocking=False):
        raise LoaderError("Document extraction is busy; try again shortly")
    try:
        return await _extract_document(kind, source)
    finally:
        _workers.release()


async def _extract_document(kind: str, source: str) -> dict:
    process = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "app.ingestion.document_worker", kind, source,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
    )
    try:
        async with asyncio.timeout(30):
            output, _ = await process.communicate()
        result = json.loads(output)
        if process.returncode or "error" in result:
            raise LoaderError(result.get("error", "Document extraction failed"))
        return result
    except (TimeoutError, ValueError) as exc:
        raise LoaderError("Document could not be extracted within its limits") from exc
    finally:
        if process.returncode is None:
            process.kill()
            await process.wait()
