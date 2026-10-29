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
import re
from collections import Counter
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx

from app.core.public_http import fetch_page, public_client
from app.ingestion.documents import RawDocument, SourceType
from app.ingestion.exceptions import LoaderError
from app.ingestion.loaders.html_extract import (
    extract_content,
    extract_link_candidates,
    is_worth_reading,
    priority_of,
    within_source_site,
)
from app.ingestion.loaders.public_content import content_issues, is_access_wall
from app.ingestion.loaders.rendered_page import render_public_html

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
_MAX_DEPTH = 2


class SiteCrawler:
    """Fetches a starting page and the most useful pages it links to."""

    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        max_pages: int = DEFAULT_MAX_PAGES,
        renderer: Callable[[str, str], Awaitable[str | None]] | None = None,
    ) -> None:
        self._client = client
        self._max_pages = max(1, max_pages)
        self._renderer = renderer or (render_public_html if client is None else None)

    async def crawl(self, start_url: str, *, focus: str = "") -> list[RawDocument]:
        """Every readable page found, starting page first.

        Raises LoaderError only when the starting page itself cannot be read -
        that is a URL the user got wrong, and they should hear about it.
        """
        if self._client is not None:
            return await self._crawl_with(self._client, start_url, focus=focus)
        async with public_client() as client:
            return await self._crawl_with(client, start_url, focus=focus)

    async def _crawl_with(self, client: httpx.AsyncClient, start_url: str, *, focus: str = "") -> list[RawDocument]:
        render_attempts = 0

        async def readable(page: httpx.Response) -> httpx.Response:
            nonlocal render_attempts
            title, _, body = extract_content(page.text)
            if is_access_wall(title, body):
                return page
            if (self._renderer is not None and render_attempts < 2
                    and content_issues(body)):
                render_attempts += 1
                rendered = await self._renderer(str(page.url), page.text)
                if rendered:
                    return httpx.Response(200, text=rendered, request=page.request,
                                          extensions={"rendered": True})
            return page

        try:
            response = await fetch_page(client, start_url)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise LoaderError(f"Failed to fetch '{start_url}': {exc}", url=start_url) from exc

        response = await readable(response)
        root_url = str(response.url)
        root = _to_document(root_url, response.text)
        documents = [root] if root else []
        if root:
            root.metadata.update(crawl_depth=0, requested_url=start_url,
                                 rendered=bool(response.extensions.get("rendered")))
        seen = {_canonical(start_url), _canonical(root_url)}
        stored = {_canonical(root_url)} if root else set()
        frontier: list[tuple[str, int, str, int]] = []
        unreadable: list[str] = []

        def discover(html: str, page_url: str, depth: int) -> None:
            if depth >= _MAX_DEPTH:
                return
            for url, priority in extract_link_candidates(html, page_url, site_root=root_url, focus=focus):
                key = _canonical(url)
                if key not in seen and _same_site(url, root_url):
                    seen.add(key)
                    frontier.append((url, depth + 1, page_url, priority))

        async def fetch(url: str) -> httpx.Response | None:
            try:
                page = await fetch_page(client, url)
                page.raise_for_status()
                final = str(page.url)
                if not _same_site(final, root_url) or not is_worth_reading(final):
                    logger.info("crawler: skipping redirect outside source scope: %s", url)
                    return None
                return await readable(page)
            except (httpx.HTTPError, LoaderError) as exc:
                logger.info("crawler: skipping %s (%s)", url, exc)
                return None

        discover(response.text, root_url, 0)
        attempted = 1
        families: Counter[str] = Counter()
        while frontier and attempted < self._max_pages:
            # Reconsider the frontier after each small batch. A help index can
            # reveal more useful pages than the homepage's remaining blog links.
            count = min(_CONCURRENCY, self._max_pages - attempted, len(frontier))
            batch = []
            for _ in range(count):
                frontier.sort(key=lambda item: (
                    -(item[3] + _crawl_priority(item[0]) - priority_of(item[0]) - 15 * families[_family(item[0])]),
                    item[1], len(item[0]), item[0],
                ))
                item = frontier.pop(0)
                batch.append(item)
                families[_family(item[0])] += 1
            attempted += len(batch)
            results = await asyncio.gather(*(fetch(url) for url, _, _, _ in batch))
            for (requested, depth, parent, priority), page in zip(batch, results, strict=True):
                if page is None:
                    unreadable.append(requested)
                    continue
                final = str(page.url)
                seen.add(_canonical(final))
                if _canonical(final) not in stored and (document := _to_document(final, page.text)):
                    document.metadata.update(crawl_depth=depth, requested_url=requested, discovered_from=parent,
                                             crawl_priority=priority + _crawl_priority(final) - priority_of(final),
                                             rendered=bool(page.extensions.get("rendered")))
                    documents.append(document)
                    stored.add(_canonical(final))
                elif _canonical(final) not in stored:
                    unreadable.append(final)
                discover(page.text, final, depth)
        # Highest-value pages first, so a downstream reading budget that runs
        # out runs out on the changelog rather than on the pricing page.
        documents[1:] = sorted(documents[1:], key=lambda item: -item.metadata.get("crawl_priority", priority_of(item.source)))
        if documents and unreadable:
            documents[0].metadata["crawl_unreadable_urls"] = list(dict.fromkeys(unreadable))
            documents[0].metadata.setdefault("content_issues", []).append("partial_crawl")
        return documents


def _to_document(url: str, html: str) -> RawDocument | None:
    title, description, markdown = extract_content(html)
    issues = content_issues(markdown)
    if is_access_wall(title, markdown) or len(markdown) < _MIN_CONTENT_CHARS or "navigation_only" in issues:
        return None
    return RawDocument(
        content=markdown,
        source=url,
        source_type=SourceType.WEBSITE,
        fetched_at=datetime.now(UTC),
        metadata={"title": title, "description": description, "crawled": True, "content_issues": issues},
    )


def _canonical(url: str) -> str:
    parsed = urlsplit(url)
    query = [(key, value) for key, value in parse_qsl(parsed.query, keep_blank_values=True)
             if not key.lower().startswith("utm_") and key.lower() not in {"cta", "ref", "fbclid", "gclid"}]
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower().removeprefix("www."),
                       parsed.path.rstrip("/"), urlencode(sorted(query)), ""))


def _same_site(url: str, root: str) -> bool:
    return within_source_site(url, root)


def _family(url: str) -> str:
    path = urlsplit(url).path.lower()
    host = (urlsplit(url).hostname or "").split(".")[0]
    if host in {"docs", "doc", "documentation", "help", "support", "developers", "developer"} or re.search(
        r"/(?:docs?|documentation|help|support|guides?)(?:/|$)", path,
    ):
        return "documentation"
    if re.search(r"/(?:pricing|plans?|prices?)(?:/|$)", path):
        return "pricing"
    if re.search(r"case[-_]stud|customers?|testimonials?|stories|success", path):
        return "proof"
    if re.search(r"/collections(?:/|$)", path):
        return "catalog"
    return "product"


def _crawl_priority(url: str) -> int:
    path = urlsplit(url).path.lower()
    score = priority_of(url)
    if _family(url) == "catalog":
        return max(score, 90)
    if _family(url) == "documentation" and re.search(
        r"(?:^|[/_-])(?:install(?:ation)?|setup|quickstart|getting-started|get-started|script|integration-guides)(?:[/_.-]|$)",
        path,
    ):
        # The hub already spent one documentation slot. Its diversity penalty
        # must not push the first actionable guide behind every marketing page.
        return max(score, 120)
    if _family(url) == "documentation":
        return max(score, 95)
    return score
