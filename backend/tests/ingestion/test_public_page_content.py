import html
import json

import httpx
import pytest

from app.ingestion.loaders.html_extract import extract_content, extract_links
from app.ingestion.loaders.public_content import content_issues, is_access_wall
from app.ingestion.loaders.site_crawler import SiteCrawler


def test_explicit_access_screens_are_not_source_articles():
    assert is_access_wall("Forum - Prove your humanity", "Security instructions. " * 30)
    assert is_access_wall("Forum", "You've been blocked by network security. Log in to continue.")
    assert not is_access_wall("Why verification screens exist", "An article about security. " * 100 + "verify you are human")


@pytest.mark.asyncio
async def test_crawler_does_not_render_or_store_an_access_check():
    async def renderer(*_):
        pytest.fail("An access check must not be sent to the browser renderer")
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(
        200, text="<title>Forum - Prove your humanity</title><main>" + "Access check information. " * 30 + "</main>",
    ))) as client:
        assert await SiteCrawler(client, max_pages=1, renderer=renderer).crawl("https://example.test/") == []


def state_page(*, locked=False):
    data = {
        "title": "Budget cameras",
        "page_data": {"page": {"type": "RecommendationPage", "locked": locked,
            "recommendation": {
                "introduction": "<p>" + "Choose a camera for your budget and lens needs. " * 8 + "</p>",
                "product_recommendations": [{"title": "Compact option", "description":
                    '<p>Compare the <a href="/camera/reviews/compact">compact camera</a>; its fixed lens cannot be replaced.</p>',
                    "ratings": {"secret_test_value": 99}}],
                "conclusion": "<p>Prices and lens availability affect the choice.</p>",
            }}},
        "account": {"email": "private@example.test", "internal_note": "Do not extract me"},
    }
    return '<html><title>Budget cameras</title><body><div data-props="' + html.escape(json.dumps(data), quote=True) + '"></div></body></html>'


def test_public_hydration_keeps_narrative_links_and_limits_without_private_state():
    raw = state_page()
    content = extract_content(raw)[2]
    assert "cannot be replaced" in content
    assert content.index("Compact option") < content.index("Prices and lens availability")
    assert "private@example.test" not in content
    assert "secret_test_value" not in content and "99" not in content
    assert "https://example.test/camera/reviews/compact" in extract_links(raw, "https://example.test/")


def test_locked_article_state_is_not_an_alternative_to_access_control():
    assert "Compact option" not in extract_content(state_page(locked=True))[2]
    raw = '<script type="application/ld+json">' + json.dumps({
        "@type": "Article", "isAccessibleForFree": False, "articleBody": "Restricted content. " * 40,
    }) + "</script>"
    assert "Restricted content" not in extract_content(raw)[2]


def test_public_jsonld_and_malformed_state_do_not_execute_javascript():
    raw = '<script type="application/ld+json">' + json.dumps({
        "@type": "Article", "headline": "Setup", "articleBody": "A public installation guide. " * 20,
    }) + '</script><div data-props="not json"></div><script>arbitraryCode()</script>'
    content = extract_content(raw)[2]
    assert "public installation guide" in content
    assert "arbitraryCode" not in content


def test_missing_dynamic_values_are_distinct_from_literal_code_examples():
    table = "Plans\n\n" + "null:\n\n" * 12
    assert "dynamic_values_missing" in content_issues(table)
    assert not content_issues("```json\n" + table + "\n```")


@pytest.mark.asyncio
async def test_focused_crawl_spends_budget_on_relevant_links_before_other_category_pricing():
    seen = []
    def handler(request):
        seen.append(request.url.path)
        if request.url.path == "/":
            body = '<a href="/cars/prices">Car prices</a><a href="/electronics/tv">Television ratings</a>'
        else:
            body = "<p>" + "Substantive page content with published conditions. " * 10 + "</p>"
        return httpx.Response(200, text=body)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        pages = await SiteCrawler(client, max_pages=2).crawl("https://example.test/", focus="television comparison")
    assert "/electronics/tv" in seen and "/cars/prices" not in seen
    assert any(page.source.endswith("/electronics/tv") for page in pages)


def test_navigation_shell_is_recognized_as_partial_content():
    menu = "\n".join(f"[Category {i}](/category-{i})" for i in range(20))
    assert "navigation_only" in content_issues(menu)
