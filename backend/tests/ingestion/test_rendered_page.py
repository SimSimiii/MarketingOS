from types import SimpleNamespace

import httpx
import pytest

from app.core.public_http import fetch_page, fetch_render_resource
from app.ingestion.exceptions import LoaderError
from app.ingestion.loaders.rendered_page import RenderGateway, _values_loaded
from app.ingestion.loaders.site_crawler import SiteCrawler


class Route:
    def __init__(self, url, *, method="GET", kind="script"):
        self.request = SimpleNamespace(url=url, method=method, resource_type=kind)
        self.aborted = False
        self.fulfilled = None

    async def abort(self):
        self.aborted = True

    async def fulfill(self, **kwargs):
        self.fulfilled = kwargs


def test_disappearing_nulls_do_not_mean_the_price_values_have_loaded():
    original = "Published plans\n\n" + "null\n\n" * 12
    assert not _values_loaded(original, "Published plans without their values")
    assert _values_loaded(original, "Free 0 EUR, Startup 17 EUR, Webinar 47 EUR")


@pytest.mark.asyncio
@pytest.mark.parametrize("url,method,kind", [
    ("http://127.0.0.1/private", "GET", "fetch"),
    ("https://example.test/submit", "POST", "fetch"),
    ("https://example.test/login", "GET", "document"),
    ("https://example.test/picture.png", "GET", "image"),
])
async def test_render_gateway_never_connects_for_private_writes_navigation_or_images(url, method, kind):
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: pytest.fail("request escaped admission"))) as client:
        gateway = RenderGateway(client, "https://example.test/", "Public source")
        route = Route(url, method=method, kind=kind)
        await gateway.handle(route)
    assert route.aborted and route.fulfilled is None


@pytest.mark.asyncio
async def test_render_dependency_redirect_cannot_move_to_private_network():
    seen = []
    def handler(request):
        seen.append(str(request.url))
        return httpx.Response(302, headers={"location": "http://169.254.169.254/latest/meta-data"})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        route = Route("https://example.test/bootstrap.js")
        await RenderGateway(client, "https://example.test/", "Public source").handle(route)
    assert len(seen) == 1 and route.aborted


@pytest.mark.asyncio
@pytest.mark.parametrize("content_type", ["application/javascript", "application/x-javascript"])
async def test_resources_retain_reading_limits_and_do_not_expand_normal_document_types(content_type):
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(
        200, text="publicBootstrap()", headers={"content-type": content_type},
    ))) as client:
        with pytest.raises(LoaderError):
            await fetch_page(client, "https://example.test/bootstrap.js")
        assert (await fetch_render_resource(client, "https://example.test/bootstrap.js")).text == "publicBootstrap()"
        gateway = RenderGateway(client, "https://example.test/", "Public source")
        route = Route("https://example.test/bootstrap.js")
        await gateway.handle(route)
        assert route.fulfilled["body"] == b"publicBootstrap()"
        gateway.requests = 32
        blocked = Route("https://example.test/next.js")
        await gateway.handle(blocked)
        assert blocked.aborted


@pytest.mark.asyncio
async def test_crawler_renders_only_incomplete_sources_with_a_two_page_budget():
    rendered = []
    body = "<p>" + "Published plan definitions and constraints. " * 6 + "</p>" + "<p>null:</p>" * 12
    links = '<a href="/pricing-a">Pricing A</a><a href="/pricing-b">Pricing B</a>'
    async def renderer(url, raw):
        rendered.append(url)
        return raw.replace("null:", "Publicly rendered value")
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(200, text=body + links))) as client:
        pages = await SiteCrawler(client, max_pages=3, renderer=renderer).crawl("https://example.test/")
    assert len(rendered) == 2
    assert len([page for page in pages if page.metadata.get("rendered")]) == 2
    assert any("dynamic_values_missing" in page.metadata["content_issues"] for page in pages)
