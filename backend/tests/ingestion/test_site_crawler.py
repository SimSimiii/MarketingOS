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


def test_pricing_priority_does_not_confuse_planner_products_with_billing():
    assert priority_of("https://x.com/fr/pricing") == 100
    assert priority_of("https://x.com/plans") == 100
    assert priority_of("https://x.com/bold-plans-63402") < 100
    assert priority_of("https://x.com/wedding/table-plans/") < 100


@pytest.mark.asyncio
async def test_small_budget_includes_linked_catalogues_before_repeated_skus():
    links = ''.join(f'<a href="/products/variant-{i}">Variant</a>' for i in range(20))
    pages = {"https://example.com/": FILLER + links + '<a href="/collections/backpacks">Backpacks</a>'}
    pages.update({f"https://example.com/products/variant-{i}": FILLER for i in range(20)})
    pages["https://example.com/collections/backpacks"] = FILLER
    async with client(pages) as http:
        documents = await SiteCrawler(http, max_pages=4).crawl("https://example.com/")
    assert len(documents) == 4
    assert any(document.source.endswith("/collections/backpacks") for document in documents)

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


@pytest.mark.asyncio
async def test_documentation_hub_is_followed_without_manual_guide_urls():
    pages = {
        "https://example.com/": f'{FILLER}<a href="/help">Help</a>',
        "https://example.com/help": f'{FILLER}<a href="/help/install">Install</a>',
        "https://example.com/help/install": f'{FILLER}<p>Add one script to your site.</p><a href="/help/install/more">More</a>',
        "https://example.com/help/install/more": FILLER,
    }
    documents = await SiteCrawler(client=client(pages)).crawl("https://example.com/")
    sources = {document.source for document in documents}
    assert "https://example.com/help/install" in sources
    assert "https://example.com/help/install/more" not in sources


@pytest.mark.asyncio
async def test_discovered_guides_precede_low_value_homepage_links_within_same_budget():
    pages = {"https://example.com/": FILLER + '<a href="/docs">Documentation</a>' +
             ''.join(f'<a href="/blog/post-{n}">Post</a>' for n in range(10)),
             "https://example.com/docs": FILLER + '<a href="/docs/setup">Setup</a>',
             "https://example.com/docs/setup": FILLER + '<p>Documented installation steps.</p>'}
    pages.update({f"https://example.com/blog/post-{n}": FILLER for n in range(10)})
    calls = []

    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(200, text=pages[str(request.url)])

    transport = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    documents = await SiteCrawler(client=transport, max_pages=6).crawl("https://example.com/")
    assert "https://example.com/docs/setup" in {document.source for document in documents}
    assert len(calls) <= 6


@pytest.mark.asyncio
async def test_redirected_document_uses_final_url_for_relative_guide_links():
    def handler(request):
        url = str(request.url)
        if url == "https://example.com/docs":
            return httpx.Response(302, headers={"location": "/help/"})
        if url == "https://example.com/":
            return httpx.Response(200, text=FILLER + '<a href="/docs">Docs</a>')
        if url == "https://example.com/help/":
            return httpx.Response(200, text=FILLER + '<a href="setup">Setup</a>')
        return httpx.Response(200, text=FILLER)

    transport = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    documents = await SiteCrawler(client=transport).crawl("https://example.com/")
    assert "https://example.com/help/setup" in {d.source for d in documents}


@pytest.mark.asyncio
async def test_child_redirect_does_not_import_another_companys_claims():
    def handler(request):
        if str(request.url) == "https://example.com/":
            return httpx.Response(200, text=FILLER + '<a href="/pricing">Price</a>')
        if str(request.url) == "https://example.com/pricing":
            return httpx.Response(302, headers={"location": "https://another-company.com/plans"})
        return httpx.Response(200, text=FILLER + '<p>Another company charges $999.</p>')

    transport = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    documents = await SiteCrawler(client=transport).crawl("https://example.com/")
    assert len(documents) == 1


@pytest.mark.asyncio
async def test_getting_started_guide_precedes_shorter_peripheral_help_page():
    pages = {
        "https://example.com/": FILLER + '<a href="/docs">Docs</a>',
        "https://example.com/docs": FILLER + '<a href="/docs/2fa">2FA</a><a href="/docs/getting-started">Start</a>',
        "https://example.com/docs/2fa": FILLER,
        "https://example.com/docs/getting-started": FILLER,
    }
    documents = await SiteCrawler(client=client(pages), max_pages=3).crawl("https://example.com/")
    assert "https://example.com/docs/getting-started" in {d.source for d in documents}


@pytest.mark.asyncio
@pytest.mark.parametrize("guide", [
    "https://support.example.com/how-do-i-get-started-with-tool-ab12",
    "https://example.com/docs/getting-started",
])
async def test_first_onboarding_guide_survives_crowded_marketing_frontier(guide):
    hub = "https://support.example.com/" if "support." in guide else "https://example.com/docs"
    pages = {
        "https://example.com/": FILLER + f'<a href="{hub}">Help</a>' +
            ''.join(f'<a href="/testimonials-{i}">Testimonials</a>' for i in range(20)),
        hub: FILLER + f'<a href="{guide}">Get started</a>',
        guide: FILLER + '<p>Create your first form, publish it, and import a testimonial.</p>',
        **{f"https://example.com/testimonials-{i}": FILLER for i in range(20)},
    }
    calls = []

    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(200, text=pages[str(request.url)])

    transport = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    documents = await SiteCrawler(client=transport, max_pages=6).crawl("https://example.com/")
    assert guide in {document.source for document in documents}
    assert len(calls) <= 6
