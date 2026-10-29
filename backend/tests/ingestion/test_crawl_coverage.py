"""Coverage under one homepage-only crawl budget, without a live website."""

import pytest

from app.ingestion.loaders.html_extract import extract_content, extract_links
from app.ingestion.loaders.site_crawler import SiteCrawler
from tests.ingestion.test_site_crawler import FILLER, client


@pytest.mark.asyncio
async def test_linked_help_subdomains_and_their_guides_are_imported_without_guessing():
    pages = {
        "https://example.com/": FILLER + '<a href="https://support.example.com/">Help</a>',
        "https://support.example.com/": FILLER + '<a href="/guides/start">Setup</a>'
        '<a href="https://example.com/pricing">Pricing</a>',
        "https://support.example.com/guides/start": FILLER + "Actual installation instructions",
        "https://example.com/pricing": FILLER,
    }
    documents = await SiteCrawler(client=client(pages)).crawl("https://example.com/")
    assert {d.source for d in documents} == set(pages)
    guide = next(d for d in documents if d.source.endswith("/guides/start"))
    assert guide.metadata["discovered_from"] == "https://support.example.com/"
    assert guide.metadata["crawl_depth"] == 2


def test_documentation_scope_does_not_allow_lookalikes_or_arbitrary_subdomains():
    links = ''.join(f'<a href="{url}">Link</a>' for url in (
        "https://developers.example.com/", "https://docs.example.com/",
        "https://example.com.evil.com/", "https://docs.example.com.evil.com/",
        "https://customers.example.com/", "https://example.net/", "https://docs-example.com/",
        "https://evil.com@support.example.com/",
        "https://support.example.com:bad/", "https://[invalid-ipv6/",
    ))
    assert set(extract_links(links, "https://example.com/")) == {
        "https://developers.example.com/", "https://docs.example.com/",
    }


@pytest.mark.asyncio
async def test_pagination_and_tracking_duplicates_do_not_consume_the_crawl_budget():
    pages = {
        "https://example.com/": FILLER + '<a href="/customers">Customers</a>'
        '<a href="/pricing?utm_source=menu">Pricing</a><a href="/pricing?cta=footer">Price</a>'
        '<a href="/docs">Docs</a><a href="/features">Features</a>',
        "https://example.com/customers": FILLER + '<a href="/customers/page/2">Next</a>'
        '<a href="/customers?page=3">Next</a><a href="/customers/story">Story</a>',
        "https://example.com/pricing?utm_source=menu": FILLER,
        "https://example.com/pricing?cta=footer": FILLER,
        "https://example.com/docs": FILLER + '<a href="/docs/install">Install</a>',
        "https://example.com/docs/install": FILLER,
        "https://example.com/features": FILLER,
        "https://example.com/customers/story": FILLER,
    }
    documents = await SiteCrawler(client=client(pages), max_pages=7).crawl("https://example.com/")
    urls = [d.source for d in documents]
    assert sum("/pricing" in url for url in urls) == 1
    assert "https://example.com/docs/install" in urls
    assert "https://example.com/features" in urls
    assert not any("/page/" in url or "?page=" in url for url in urls)
    assert len(documents) <= 7


def test_sharing_prompts_do_not_inflate_or_pollute_the_reading_material():
    html = '<p>Actual product description.</p><a href="https://chatgpt.com/?prompt=' + "a" * 10000
    html += '">Ask ChatGPT about this article</a><a href="https://example.com/signup">Start free</a>'
    _, _, content = extract_content(html)
    assert len(content) < 200
    assert "Actual product description" in content
    assert "https://example.com/signup" in content
    assert "Ask ChatGPT" not in content
