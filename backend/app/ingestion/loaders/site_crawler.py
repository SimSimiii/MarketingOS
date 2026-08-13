"""Reading a whole site instead of one page.

The single most expensive limitation of the old system was that "add your
website" meant one URL, and the one URL is the home page - the page most
carefully written to say nothing checkable. Prices live on /pricing, proof
lives on /customers, the company's actual voice lives on the blog. A campaign
grounded only in a hero section has nothing specific to say, and no amount of
prompt engineering downstream invents the number that was never fetched.

The crawl is small and ordered rather than exhaustive: a budget of a dozen
pages, spent highest-value first (see html_extract._PRIORITY_HINTS). Failures
are per-page and non-fatal - a 404 on /customers must not cost the user the
eleven pages that did load.
"""

import asyncio
import logging
from datetime import UTC, datetime

import httpx

from app.ingestion.documents import RawDocument, SourceType
from app.ingestion.exceptions import LoaderError
from app.ingestion.loaders.html_extract import extract_content, extract_links, priority_of

logger = logging.getLogger("marketingos.ingestion")

#: Enough to reach pricing, customers, product and a couple of posts on a
#: normal marketing site. Past this the returns fall off fast and the
#: compiler's reading budget becomes the binding constraint instead.
DEFAULT_MAX_PAGES = 12
#: Anything shorter than this is a redirect stub, a cookie wall or an empty
#: shell rendered client-side - never content.
_MIN_CONTENT_CHARS = 200
_REQUEST_TIMEOUT = 15.0
#: Politeness, and protection against a site that answers slowly under load.
_CONCURRENCY = 4


class SiteCrawler:
    """Fetches a starting page and the most useful pages it links to."""

    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        max_pages: int = DEFAULT_MAX_PAGES,
    ) -> None:
        self._client = client
        self._max_pages = max_pages

    async def crawl(self, start_url: str) -> list[RawDocument]:
        """Every readable page found, starting page first.

        Raises LoaderError only when the starting page itself cannot be read -
        that is a URL the user got wrong, and they should hear about it.
        """
        if self._client is not None:
            return await self._crawl_with(self._client, start_url)
        async with httpx.AsyncClient(follow_redirects=True, timeout=_REQUEST_TIMEOUT) as client:
            return await self._crawl_with(client, start_url)

    async def _crawl_with(self, client: httpx.AsyncClient, start_url: str) -> list[RawDocument]:
        try:
            response = await client.get(start_url)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise LoaderError(f"Failed to fetch '{start_url}': {exc}", url=start_url) from exc

        root_html = response.text
        documents = [document for document in [_to_document(start_url, root_html)] if document]
        seen = {_canonical(start_url)}

        queue = [
            url for url in extract_links(root_html, start_url) if _canonical(url) not in seen
        ][: self._max_pages - 1]
        for url in queue:
            seen.add(_canonical(url))

        semaphore = asyncio.Semaphore(_CONCURRENCY)

        async def fetch(url: str) -> RawDocument | None:
            async with semaphore:
                try:
                    page = await client.get(url)
                    page.raise_for_status()
                except httpx.HTTPError as exc:
                    logger.info("crawler: skipping %s (%s)", url, exc)
                    return None
                return _to_document(url, page.text)

        results = await asyncio.gather(*(fetch(url) for url in queue))
        documents.extend(document for document in results if document is not None)
        # Highest-value pages first, so a downstream reading budget that runs
        # out runs out on the changelog rather than on the pricing page.
        documents[1:] = sorted(documents[1:], key=lambda item: -priority_of(item.source))
        return documents


def _to_document(url: str, html: str) -> RawDocument | None:
    title, description, markdown = extract_content(html)
    if len(markdown) < _MIN_CONTENT_CHARS:
        return None
    return RawDocument(
        content=markdown,
        source=url,
        source_type=SourceType.WEBSITE,
        fetched_at=datetime.now(UTC),
        metadata={"title": title, "description": description, "crawled": True},
    )


def _canonical(url: str) -> str:
    return url.rstrip("/").lower()
