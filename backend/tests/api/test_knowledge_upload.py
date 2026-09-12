"""The upload boundary: what a file is allowed to cost before it is refused."""

import pytest
from fastapi.testclient import TestClient

from app.api.routes.knowledge import MAX_UPLOAD_BYTES, _read_within_limit


def test_a_document_upload_is_ingested(client: TestClient):
    response = client.post(
        "/api/knowledge/upload",
        files={"file": ("notes.txt", b"Foldwork bills $29 a month.", "text/plain")},
    )
    assert response.status_code == 201, response.text
    assert "Foldwork bills" in response.json()[0]["content"]


def test_an_oversized_upload_is_refused(client: TestClient):
    oversized = b"x" * (MAX_UPLOAD_BYTES + 1)
    response = client.post(
        "/api/knowledge/upload",
        files={"file": ("huge.txt", oversized, "text/plain")},
    )
    assert response.status_code == 413
    assert "20 MB limit" in response.json()["detail"]


class _EndlessUpload:
    """An upload whose size is unknown, which is the case the limit is for:
    with a size the check is free, without one the only way to know is to
    read - and reading all of it is exactly what must not happen."""

    size = None

    def __init__(self) -> None:
        self.bytes_read = 0

    async def read(self, count: int = -1) -> bytes:
        self.bytes_read += count
        return b"x" * count


@pytest.mark.asyncio
async def test_an_unbounded_upload_stops_being_read_near_the_limit():
    """`await file.read()` allocates the whole body and *then* measures it, so
    the 413 arrives after the damage. The read has to stop instead."""
    upload = _EndlessUpload()

    with pytest.raises(Exception) as excinfo:
        await _read_within_limit(upload)

    assert getattr(excinfo.value, "status_code", None) == 413
    # Read past the limit far enough to know, and no further.
    assert upload.bytes_read <= MAX_UPLOAD_BYTES * 2
