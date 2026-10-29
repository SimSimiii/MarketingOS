from datetime import UTC, datetime

import httpx

from app.core.public_http import fetch_page, public_client
from app.ingestion.documents import RawDocument, SourceType
from app.ingestion.exceptions import LoaderError
from app.ingestion.loaders.base import Loader
from app.ingestion.loaders.html_extract import extract_content
from app.ingestion.loaders.public_content import content_issues, is_access_wall
from app.ingestion.loaders.rendered_page import render_public_html


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

    async def load(self, source: str, *, is_path: bool = False) -> RawDocument:
        html = await self.fetch(source)
        title, description, markdown = extract_content(html)

        return RawDocument(
            content=markdown,
            source=source,
            source_type=self.source_type,
            fetched_at=datetime.now(UTC),
            metadata={"title": title, "description": description, "content_issues": content_issues(markdown)},
        )

    async def fetch(self, url: str) -> str:
        try:
            if self._client is not None:
                response = await fetch_page(self._client, url)
            else:
                async with public_client() as client:
                    response = await fetch_page(client, url)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise LoaderError(f"Failed to fetch '{url}': {exc}", url=url) from exc
        title, _, content = extract_content(response.text)
        if is_access_wall(title, content):
            raise LoaderError("The public page requires access verification; its content was not read", url=url)
        if self._client is None and content_issues(content):
            rendered = await render_public_html(str(response.url), response.text)
            if rendered:
                return rendered
        return response.text
