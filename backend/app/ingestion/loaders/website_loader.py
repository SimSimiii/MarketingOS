from datetime import UTC, datetime

import httpx

from app.ingestion.documents import RawDocument, SourceType
from app.ingestion.exceptions import LoaderError
from app.ingestion.loaders.base import Loader
from app.ingestion.loaders.html_extract import extract_content


class WebsiteLoader(Loader):
    """Downloads a page and converts its visible content to clean Markdown.

    Never summarizes and never calls an LLM - it's a structural transform
    only: strip navigation/scripts/styles, keep headings/links/lists.
    """

    source_type = SourceType.WEBSITE

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        # Injected client lets tests use httpx.MockTransport instead of the
        # network; defaults to a real client for actual use.
        self._client = client

    async def load(self, source: str) -> RawDocument:
        html = await self.fetch(source)
        title, description, markdown = extract_content(html)

        return RawDocument(
            content=markdown,
            source=source,
            source_type=self.source_type,
            fetched_at=datetime.now(UTC),
            metadata={"title": title, "description": description},
        )

    async def fetch(self, url: str) -> str:
        try:
            if self._client is not None:
                response = await self._client.get(url)
            else:
                async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
                    response = await client.get(url)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise LoaderError(f"Failed to fetch '{url}': {exc}", url=url) from exc
        return response.text
