"""Check a declared logo before adopting it; no model or alternate URL search."""

import asyncio

import httpx

from app.core.public_http import fetch_image, public_client
from app.ingestion.exceptions import LoaderError


async def usable_logo(url: str, client: httpx.AsyncClient | None = None) -> bool:
    async def check(http: httpx.AsyncClient) -> bool:
        response = await fetch_image(http, url)
        data = response.content
        return (data.startswith((b"\x89PNG\r\n\x1a\n", b"\xff\xd8\xff", b"GIF87a", b"GIF89a"))
                or (data.startswith(b"RIFF") and data[8:12] == b"WEBP"))

    try:
        async with asyncio.timeout(5):
            if client is not None:
                return await check(client)
            async with public_client() as http:
                return await check(http)
    except (LoaderError, httpx.HTTPError, TimeoutError):
        return False
