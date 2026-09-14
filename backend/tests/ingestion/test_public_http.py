import httpx
import pytest

from app.core.public_http import PublicTransport, fetch_page
from app.ingestion.exceptions import LoaderError


@pytest.mark.asyncio
@pytest.mark.parametrize("url", ["http://127.0.0.1/a", "http://[::1]/", "http://169.254.169.254/",
                                 "file:///etc/passwd", "http://user:password@example.com/"])
async def test_private_destinations_never_reach_transport(url):
    def fail(request):
        pytest.fail("Unsafe URL reached the transport")
    async with httpx.AsyncClient(transport=httpx.MockTransport(fail)) as client:
        with pytest.raises(LoaderError):
            await fetch_page(client, url)


@pytest.mark.asyncio
async def test_redirects_are_rechecked_before_following_them():
    called = []
    def redirect(request):
        called.append(str(request.url))
        return httpx.Response(302, headers={"location": "http://127.0.0.1/secret"})
    async with httpx.AsyncClient(transport=httpx.MockTransport(redirect)) as client:
        with pytest.raises(LoaderError):
            await fetch_page(client, "https://example.com/")
    assert len(called) == 1


@pytest.mark.asyncio
async def test_dns_address_is_pinned_but_tls_identity_is_preserved(monkeypatch):
    seen = []
    async def resolve(host):
        seen.append(host)
        return ["1.1.1.1"]
    async def handle(self, request):
        assert request.url.host == "1.1.1.1"
        assert request.headers["host"] == "example.com"
        assert request.extensions["sni_hostname"] == "example.com"
        return httpx.Response(200, text="safe")
    monkeypatch.setattr("app.core.public_http.resolve_public", resolve)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", handle)
    async with PublicTransport() as transport:
        await transport.handle_async_request(httpx.Request("GET", "https://example.com/a"))
    assert seen == ["example.com"]


@pytest.mark.asyncio
async def test_oversized_and_compressed_responses_are_refused():
    for headers in ({"content-length": "99999999"}, {"content-encoding": "br"}):
        async with httpx.AsyncClient(transport=httpx.MockTransport(
            lambda request, headers=headers: httpx.Response(200, headers=headers)
        )) as client:
            with pytest.raises(LoaderError):
                await fetch_page(client, "https://example.com/")
