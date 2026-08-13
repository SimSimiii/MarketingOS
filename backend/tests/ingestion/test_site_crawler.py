"""Reading a whole site instead of one page.

"Add your website" means the home page, and the home page is the page most
carefully written to say nothing checkable. Everything a campaign can actually
prove lives one click away.
"""

import httpx
import pytest

from app.ingestion.exceptions import LoaderError
from app.ingestion.loaders.html_extract import extract_links, is_worth_reading, priority_of
from app.ingestion.loaders.site_crawler import SiteCrawler

FILLER = "<p>" + ("Something worth reading about the product. " * 12) + "</p>"

PAGES = {
    "https://example.com/": f"""
        <html><head><title>Home</title></head><body>
          <nav><a href="/login">Log in</a></nav>
          <h1>Notewright</h1>{FILLER}
          <a href="/pricing">Pricing</a>
          <a href="/customers">Customers</a>
          <a href="/careers">Careers</a>
          <a href="https://twitter.com/notewright">Twitter</a>
          <a href="/pricing#top">Pricing again</a>
        </body></html>
    """,
    "https://example.com/pricing": f"""
        <html><head><title>Pricing</title></head><body>
          <h1>Pricing</h1><p>Team is $29 per month.</p>{FILLER}
        </body></html>
    """,
    "https://example.com/customers": f"""
        <html><head><title>Customers</title></head><body>
          <h1>Customers</h1><p>Foldwork ships weekly with us.</p>{FILLER}
        </body></html>
    """,
}


def client(pages: dict[str, str] | None = None, fail: set[str] | None = None) -> httpx.AsyncClient:
    available = PAGES if pages is None else pages
    broken = fail or set()

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url in broken:
            return httpx.Response(500)
        body = available.get(url) or available.get(url.rstrip("/"))
        if body is None:
            return httpx.Response(404)
        return httpx.Response(200, text=body)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=True)


@pytest.mark.asyncio
async def test_the_pages_that_carry_the_evidence_are_fetched_too():
    documents = await SiteCrawler(client=client()).crawl("https://example.com/")
    sources = [document.source for document in documents]

    assert sources[0] == "https://example.com/"
    assert "https://example.com/pricing" in sources
    assert "https://example.com/customers" in sources
    assert any("$29 per month" in document.content for document in documents)


@pytest.mark.asyncio
async def test_pages_that_never_carry_marketing_evidence_are_skipped():
    documents = await SiteCrawler(client=client()).crawl("https://example.com/")
    sources = [document.source for document in documents]

    assert not any("careers" in source for source in sources)
    assert not any("login" in source for source in sources)


@pytest.mark.asyncio
async def test_the_crawl_never_leaves_the_site():
    """A footer link to a competitor would file someone else's claims as this
    company's evidence."""
    documents = await SiteCrawler(client=client()).crawl("https://example.com/")
    assert all("twitter.com" not in document.source for document in documents)


@pytest.mark.asyncio
async def test_the_budget_is_respected_and_spent_on_the_best_pages_first():
    documents = await SiteCrawler(client=client(), max_pages=2).crawl("https://example.com/")

    assert len(documents) == 2
    # Pricing outranks customers, so a budget of one extra page buys pricing.
    assert documents[1].source == "https://example.com/pricing"


@pytest.mark.asyncio
async def test_one_broken_page_does_not_cost_the_user_the_rest():
    documents = await SiteCrawler(
        client=client(fail={"https://example.com/customers"})
    ).crawl("https://example.com/")

    sources = [document.source for document in documents]
    assert "https://example.com/pricing" in sources
    assert "https://example.com/customers" not in sources


@pytest.mark.asyncio
async def test_a_starting_page_that_cannot_be_read_is_the_users_problem_to_hear_about():
    with pytest.raises(LoaderError):
        await SiteCrawler(client=client(pages={})).crawl("https://example.com/")


@pytest.mark.asyncio
async def test_an_empty_shell_page_is_not_a_document():
    thin = {"https://example.com/": "<html><body><p>Loading…</p></body></html>"}
    assert await SiteCrawler(client=client(pages=thin)).crawl("https://example.com/") == []


def test_a_url_is_only_followed_once_however_many_ways_it_is_linked():
    links = extract_links(PAGES["https://example.com/"], "https://example.com/")
    assert links.count("https://example.com/pricing") == 1


def test_pricing_and_proof_outrank_the_blog():
    assert priority_of("https://x.com/pricing") > priority_of("https://x.com/blog/hello")
    assert priority_of("https://x.com/customers") > priority_of("https://x.com/integrations")
    assert priority_of("https://x.com/") > priority_of("https://x.com/a/b/c/d")


def test_legal_and_account_pages_are_not_worth_reading():
    assert not is_worth_reading("https://x.com/privacy")
    assert not is_worth_reading("https://x.com/account/settings")
    assert not is_worth_reading("https://x.com/brochure.pdf")
    assert is_worth_reading("https://x.com/pricing")
