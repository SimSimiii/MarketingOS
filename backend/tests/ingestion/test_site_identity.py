"""What a site declares about its owner's look, and what it only seems to.

The pages here are cut down from the real ones that shaped the rules:
Cabaia's Shopify product page (an SVG logo, a WebP photograph, a review
widget that calls the whole shop a Product) and Papier's home page (its
logo doubling as `og:image`, a cream `theme-color`).
"""

import json

import httpx
import pytest

from app.core.colour import contrast, darken_to, parse_colour
from app.ingestion.loaders.site_crawler import SiteCrawler
from app.ingestion.loaders.site_identity import (
    SiteIdentity,
    picture_on,
    read_identity,
    same_page,
    same_site,
)

FILLER = "<p>" + ("A sentence about the bag and what it carries. " * 12) + "</p>"


def page(head: str, *structured: dict, body: str = FILLER) -> str:
    scripts = "".join(
        f'<script type="application/ld+json">{json.dumps(item)}</script>' for item in structured
    )
    return f"<html><head>{head}{scripts}</head><body>{body}</body></html>"


SHOP = {"@type": "OnlineStore", "name": "Cabaia", "logo": "https://shop.example/cdn/Logo.png?v=1"}
DUFFLE = {
    "@type": "Product",
    "name": "Duffle Adventurer Reykjavik",
    "image": ["//shop.example/cdn/duffle.webp?width=1200"],
    "offers": {"@type": "Offer", "price": "120.00", "priceCurrency": "EUR"},
    "brand": {"@type": "Brand", "name": "Someone Else", "logo": "https://other.example/logo.png"},
}
#: What a review widget injects on every page, home page included.
SHOP_RATING = {"@type": "Product", "name": "Cabaia", "aggregateRating": {"ratingValue": "4.8"}}


def test_the_logo_is_the_one_the_site_declares_for_itself():
    identity = read_identity(page("", SHOP, DUFFLE), "https://shop.example/products/duffle")

    assert identity.logo_url == "https://shop.example/cdn/Logo.png?v=1"


def test_a_product_s_brand_logo_is_never_taken_for_the_shop_s():
    # A shop selling another company's goods declares that company's logo on
    # the Product. Taking it would put a stranger's mark atop every email.
    identity = read_identity(page("", DUFFLE), "https://shop.example/products/duffle")

    assert identity.logo_url == ""


def test_an_svg_logo_is_refused_and_the_owner_is_told_why():
    shop = {**SHOP, "logo": "https://shop.example/cdn/Logo.svg?v=1&width=128"}

    identity = read_identity(page("", shop), "https://shop.example/")

    assert identity.logo_url == ""
    assert any("SVG" in note for note in identity.notes)


def test_a_logo_inside_a_graph_is_found_and_a_relative_one_is_resolved():
    graph = {"@context": "https://schema.org", "@graph": [
        {"@type": "WebSite", "name": "Papier"},
        {"@type": "Organization", "logo": {"@type": "ImageObject", "url": "/images/logo.png"}},
    ]}

    identity = read_identity(page("", graph), "https://www.papier.example/")

    assert identity.logo_url == "https://www.papier.example/images/logo.png"


def test_broken_structured_data_costs_nothing_but_itself():
    html = page('<script type="application/ld+json">{"@type": "Organization",</script>', SHOP)

    assert read_identity(html, "https://shop.example/").logo_url.endswith("Logo.png?v=1")


def test_the_theme_colour_is_read_in_the_spellings_sites_use():
    for declared, expected in (
        ('<meta name="theme-color" content="#0069FF">', "#0069ff"),
        ('<meta name="theme-color" content="rgb(102, 9, 165)">', "#6609a5"),
        ('<meta name="msapplication-TileColor" content="#e33">', "#ee3333"),
    ):
        assert read_identity(page(declared), "https://x.example/").theme_color == expected


def test_a_cream_theme_colour_is_a_toolbar_not_a_brand():
    head = '<meta name="theme-color" content="rgb(250, 247, 240)">'

    identity = read_identity(page(head), "https://www.papier.example/")

    assert identity.theme_color == ""
    assert any("too pale" in note for note in identity.notes)


def test_the_dark_scheme_colour_is_skipped_for_the_light_one():
    head = (
        '<meta name="theme-color" media="(prefers-color-scheme: dark)" content="#000000">'
        '<meta name="theme-color" media="(prefers-color-scheme: light)" content="#c2410c">'
    )

    assert read_identity(page(head), "https://x.example/").theme_color == "#c2410c"


def test_a_product_page_gives_its_photograph_name_and_shape():
    head = (
        '<meta property="og:image" content="http://shop.example/cdn/duffle.jpg">'
        '<meta property="og:image:secure_url" content="https://shop.example/cdn/duffle.jpg">'
        '<meta property="og:image:width" content="1200">'
        '<meta property="og:image:height" content="1200">'
        '<meta property="og:price:amount" content="120,00">'
        '<meta property="og:title" content="Reykjavik - Sac de voyage | Cabaia">'
    )

    identity = read_identity(page(head, DUFFLE), "https://shop.example/products/duffle")

    assert identity.image_url == "https://shop.example/cdn/duffle.jpg"
    assert identity.image_alt == "Duffle Adventurer Reykjavik"
    assert (identity.image_width, identity.image_height) == (1200, 1200)


def test_a_jpeg_is_preferred_to_a_webp_outlook_cannot_show():
    head = '<meta property="og:image" content="https://shop.example/cdn/duffle.webp">'
    product = {**DUFFLE, "image": "https://shop.example/cdn/duffle.jpg"}

    identity = read_identity(page(head, product), "https://shop.example/products/duffle")

    assert identity.image_url == "https://shop.example/cdn/duffle.jpg"
    assert identity.image_width == 0, "the declared size was the WebP's, not this one's"


def test_with_only_a_webp_the_webp_is_used():
    identity = read_identity(page("", DUFFLE), "https://shop.example/products/duffle")

    assert identity.image_url == "https://shop.example/cdn/duffle.webp?width=1200"


def test_the_title_names_the_picture_when_there_is_no_product_name():
    head = (
        '<meta property="og:type" content="product">'
        '<meta property="og:image" content="https://cdn.example/57101.jpg">'
        '<meta property="og:title" content="Your Plans on Paper | Softback Spiral Planner">'
    )

    identity = read_identity(page(head), "https://www.papier.example/your-plans-on-paper-57101")

    assert identity.image_alt == "Your Plans on Paper"


def test_a_home_page_has_no_product_photograph_even_when_it_declares_an_image():
    # Papier's home page og:image is its logo.
    head = (
        '<meta property="og:image" content="https://cdn.example/logo.png">'
        '<meta property="og:type" content="product">'
    )

    assert read_identity(page(head, SHOP_RATING), "https://www.papier.example/").image_url == ""


def test_a_review_widget_does_not_make_a_page_a_product_page():
    head = '<meta property="og:image" content="https://shop.example/cdn/banner.jpg">'

    identity = read_identity(page(head, SHOP_RATING), "https://shop.example/collections/bags")

    assert identity.image_url == ""


def test_an_embedded_or_svg_picture_is_never_used():
    head = (
        '<meta property="og:type" content="product">'
        '<meta property="og:image" content="data:image/png;base64,iVBORw0KGgo=">'
        '<meta property="twitter:image" content="https://shop.example/cdn/duffle.svg">'
    )

    assert read_identity(page(head), "https://shop.example/products/duffle").image_url == ""


def test_identity_round_trips_through_document_metadata_without_its_notes():
    identity = SiteIdentity(logo_url="https://x.example/l.png", notes=("a note",))

    stored = identity.as_metadata()

    assert stored == {"logo_url": "https://x.example/l.png"}
    assert SiteIdentity.from_metadata(stored) == SiteIdentity(logo_url="https://x.example/l.png")
    assert SiteIdentity.from_metadata("not a dict") == SiteIdentity()


def test_a_page_is_the_same_page_whatever_the_scheme_slash_or_variant():
    assert same_page("https://www.shop.example/products/duffle/?variant=3",
                     "http://shop.example/products/duffle")
    assert not same_page("https://shop.example/products/duffle", "https://shop.example/products/tote")
    assert same_site("https://www.cabaia.fr/products/x", "https://cabaia.fr/")
    assert not same_site("https://press.example/cabaia", "https://cabaia.fr/")


def test_the_newest_recorded_picture_of_a_page_wins():
    pages = [
        ("https://shop.example/products/duffle", {"identity": {}}),
        ("https://shop.example/products/duffle", {"identity": {"image_url": "https://cdn/new.jpg"}}),
        ("https://shop.example/products/duffle", {"identity": {"image_url": "https://cdn/old.jpg"}}),
    ]

    found = picture_on("https://shop.example/products/duffle/", pages)

    assert found is not None and found.image_url == "https://cdn/new.jpg"
    assert picture_on("https://shop.example/products/tote", pages) is None


def test_colours_are_parsed_and_darkened_only_as_far_as_reading_needs():
    assert parse_colour("#ABC") == "#aabbcc"
    assert parse_colour("rgb(250 247 240 / 1)") == "#faf7f0"
    assert parse_colour("rgba(0, 0, 0, 0)") == "", "transparent is no colour"
    assert parse_colour("blue") == ""
    assert darken_to("#1a56db", 4.5) == "#1a56db", "already readable stays as it is"
    darker = darken_to("#ff6a00", 4.5)
    assert contrast(darker, "#ffffff") >= 4.5
    assert darker.startswith("#c"), "still an orange, not a brown"


@pytest.mark.asyncio
async def test_the_crawler_records_each_page_s_identity_while_it_still_has_the_html():
    home = page('<meta name="theme-color" content="#c2410c">', SHOP)
    product = page(
        '<meta property="og:type" content="product">'
        '<meta property="og:image" content="https://shop.example/cdn/duffle.jpg">',
        body=FILLER,
    )
    pages = {
        "https://shop.example/": home.replace(
            "</body>", '<a href="/products/duffle">The duffle</a></body>'
        ),
        "https://shop.example/products/duffle": product,
    }

    def handler(request: httpx.Request) -> httpx.Response:
        body = pages.get(str(request.url))
        return httpx.Response(200, text=body) if body else httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        documents = await SiteCrawler(http, max_pages=2).crawl("https://shop.example/")

    identities = {document.source: document.metadata["identity"] for document in documents}
    assert identities["https://shop.example/"] == {
        "logo_url": "https://shop.example/cdn/Logo.png?v=1",
        "theme_color": "#c2410c",
    }
    assert identities["https://shop.example/products/duffle"]["image_url"] == (
        "https://shop.example/cdn/duffle.jpg"
    )
