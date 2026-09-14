"""Bounded public-web requests with DNS pinned to the address actually checked."""
import asyncio
import ipaddress
import socket
from urllib.parse import urljoin

import httpx

from app.ingestion.exceptions import LoaderError

MAX_RESPONSE_BYTES = 2_000_000
MAX_REDIRECTS = 4


def public_host(url: str) -> str:
    try:
        parsed = httpx.URL(url)
        host = parsed.host.rstrip(".").lower()
        if parsed.scheme not in ("http", "https") or not host or parsed.userinfo:
            raise ValueError("Only public HTTP(S) URLs without credentials are allowed")
        if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
            raise ValueError("Local hostnames are not allowed")
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            if not address.is_global:
                raise ValueError("Private and reserved addresses are not allowed")
        return host
    except (ValueError, httpx.InvalidURL) as exc:
        raise LoaderError(str(exc)) from exc


async def resolve_public(host: str) -> list[str]:
    try:
        rows = await asyncio.get_running_loop().getaddrinfo(host, None, type=socket.SOCK_STREAM)
        addresses = sorted({str(row[4][0]) for row in rows})
        if not addresses or any(not ipaddress.ip_address(ip).is_global for ip in addresses):
            raise LoaderError("The URL resolves to a private or reserved address")
        return addresses
    except OSError as exc:
        raise LoaderError("The URL hostname could not be resolved") from exc


class PublicTransport(httpx.AsyncHTTPTransport):
    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        host = public_host(str(request.url))
        addresses = await resolve_public(host)
        # Connecting by IP prevents a second DNS answer from changing the
        # destination. Host and TLS SNI still identify the original website.
        pinned = httpx.Request(
            request.method, request.url.copy_with(host=addresses[0]),
            headers=request.headers, stream=request.stream,
            extensions={**request.extensions, "sni_hostname": host},
        )
        return await super().handle_async_request(pinned)


def public_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=PublicTransport(), trust_env=False, follow_redirects=False,
        timeout=15, headers={"Accept-Encoding": "identity"},
    )


async def fetch_page(client: httpx.AsyncClient, url: str) -> httpx.Response:
    """Limits also apply to injected transports; every redirect is rechecked."""
    try:
        async with asyncio.timeout(30):
            for _ in range(MAX_REDIRECTS + 1):
                public_host(url)
                async with client.stream("GET", url, follow_redirects=False,
                                         headers={"Accept-Encoding": "identity"}) as response:
                    if response.is_redirect:
                        location = response.headers.get("location")
                        if not location:
                            raise LoaderError("Redirect without a destination")
                        url = urljoin(url, location)
                        continue
                    response.raise_for_status()
                    content_type = response.headers.get("content-type", "").split(";")[0]
                    if content_type and content_type not in (
                        "text/html", "text/plain", "application/xhtml+xml", "text/markdown",
                    ):
                        raise LoaderError("The URL did not return a text document")
                    if response.headers.get("content-encoding", "identity") != "identity":
                        raise LoaderError("Compressed HTTP responses are not accepted")
                    if int(response.headers.get("content-length", "0")) > MAX_RESPONSE_BYTES:
                        raise LoaderError("Web page exceeds the size limit")
                    content = bytearray()
                    async for chunk in response.aiter_bytes(chunk_size=65536):
                        if len(content) + len(chunk) > MAX_RESPONSE_BYTES:
                            raise LoaderError("Web page exceeds the size limit")
                        content.extend(chunk)
                    return httpx.Response(response.status_code, headers=response.headers,
                                          content=bytes(content), request=response.request)
            raise LoaderError("Too many redirects")
    except (httpx.HTTPError, TimeoutError, ValueError) as exc:
        raise LoaderError(f"Failed to fetch the web page: {exc}") from exc
