import httpx
import pytest

from app.ingestion.loaders.brand_logo import usable_logo


@pytest.mark.asyncio
@pytest.mark.parametrize("status,mime,data,expected", [
    (404, "text/html", b"Not found", False),
    (200, "text/html", b"<h1>Logo</h1>", False),
    (200, "image/png", b"<html>Not really an image</html>", False),
    (200, "image/png", b"\x89PNG\r\n\x1a\n" + b"image", True),
])
async def test_only_a_reachable_image_can_be_adopted(status, mime, data, expected):
    def respond(request):
        return httpx.Response(status, content=data, headers={"content-type": mime})
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
        assert await usable_logo("https://example.com/logo.png", http) is expected


@pytest.mark.asyncio
async def test_logo_redirects_cannot_reach_private_addresses():
    calls = []

    def respond(request):
        calls.append(str(request.url))
        return httpx.Response(302, headers={"location": "http://127.0.0.1/private.png"})
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
        assert not await usable_logo("https://example.com/logo.png", http)
    assert calls == ["https://example.com/logo.png"]
