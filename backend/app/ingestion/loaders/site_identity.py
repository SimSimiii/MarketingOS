"""What a site declares about how its owner looks: the logo, the colour, and
the picture of the thing a page sells.

Read only from what a site publishes on purpose for machines - JSON-LD, Open
Graph, `theme-color` - and never guessed from its CSS or from whichever image
happens to sit in its header. A guess here does not fail loudly. It puts a
partner's logo, or a white logo drawn for a dark header, at the top of every
email the brand sends.

The logo is the one the site's Organization declares in JSON-LD, which Google
requires to look right on a plain white background - the background it will
have in an email. Never an SVG: Gmail and Outlook do not display one, so an
SVG logo is a blank space in most inboxes and the brand's name set in bold is
the better header.

The picture is a product page's own Open Graph image, and only a product
page's. A home page's `og:image` is as often the logo or a share card as a
photograph (Papier's is its logo), and an email cannot vouch for a picture
nobody chose for it.

No network and no model: this reads HTML the crawler already fetched.
"""

import json
import re
from collections.abc import Iterable, Iterator
from dataclasses import asdict, dataclass
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from app.core.colour import MIN_SURFACE_CONTRAST, WHITE, contrast, parse_colour

_HEAD_END_RE = re.compile(r"</head\s*>", re.IGNORECASE)
_JSON_LD_RE = re.compile(
    r"<script[^>]*application/ld\+json[^>]*>(.*?)</script\s*>", re.IGNORECASE | re.DOTALL
)
#: A page with no `</head>` is malformed; its declarations, if any, are at the
#: top, and parsing two megabytes of body to find them is not worth it.
_HEAD_FALLBACK_CHARS = 200_000
#: Formats every inbox that shows images at all can show. WebP is taken only
#: when nothing else is declared: Outlook on Windows does not display it,
#: and it shows the alt text there instead.
_RASTER_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif")
#: The JSON-LD types a site uses to describe itself - the only ones whose
#: `logo` is the site's own. A Product's `brand` can be somebody else's: a shop
#: selling another company's goods declares that company's logo there.
_SELF_TYPES = frozenset({
    "organization", "corporation", "onlinestore", "onlinebusiness", "store",
    "localbusiness", "brand", "newsmediaorganization",
})
_MAX_ALT_CHARS = 120


@dataclass(frozen=True)
class SiteIdentity:
    """What one page declared. Empty strings and zeros for what it did not."""

    logo_url: str = ""
    #: `#rrggbb`, and never one too pale to show on white.
    theme_color: str = ""
    #: Set only on a product page - see the module docstring.
    image_url: str = ""
    image_alt: str = ""
    #: As declared by `og:image:width` and `og:image:height`, when they were.
    image_width: int = 0
    image_height: int = 0
    #: Why something the page did declare was not used, in words a person
    #: can act on. Never stored: it is for the moment of detection.
    notes: tuple[str, ...] = ()

    def as_metadata(self) -> dict:
        """The non-empty fields, for a document's metadata."""
        fields = asdict(self)
        fields.pop("notes")
        return {key: value for key, value in fields.items() if value}

    @classmethod
    def from_metadata(cls, value: object) -> "SiteIdentity":
        if not isinstance(value, dict):
            return cls()
        known = {key: value[key] for key in cls.__dataclass_fields__ if key in value and key != "notes"}
        try:
            return cls(**known)
        except TypeError:
            return cls()


def read_identity(html: str, page_url: str) -> SiteIdentity:
    """Everything this page declares about its owner's look."""
    end = _HEAD_END_RE.search(html)
    head = BeautifulSoup(html[: end.start()] if end else html[:_HEAD_FALLBACK_CHARS], "html.parser")
    metas = _metas(head)
    objects = list(_json_ld(html))
    notes: list[str] = []

    logo = _logo(objects, metas, page_url, notes)
    colour = _theme_colour(head, notes)
    image, alt, width, height = "", "", 0, 0
    product = _product(objects)
    if _is_product_page(page_url, metas, product):
        image, from_open_graph = _picture(metas, product, page_url, logo)
        if image:
            alt = _alt(product, metas, head)
            if from_open_graph:
                width, height = _number(metas, "og:image:width"), _number(metas, "og:image:height")
    return SiteIdentity(
        logo_url=logo, theme_color=colour, image_url=image, image_alt=alt,
        image_width=width, image_height=height, notes=tuple(dict.fromkeys(notes)),
    )


def same_site(first: str, second: str) -> bool:
    """Whether two URLs are on the same site, `www.` or not."""
    host = _page_key(first)[0]
    return bool(host) and host == _page_key(second)[0]


def same_page(first: str, second: str) -> bool:
    """Whether two URLs name the same page: scheme, `www.`, a trailing slash,
    the query and the fragment do not count. A Shopify `?variant=` is the
    same product page with another colour selected."""
    left = _page_key(first)
    return bool(left[0]) and left == _page_key(second)


def picture_on(url: str, pages: Iterable[tuple[str | None, object]]) -> SiteIdentity | None:
    """The picture recorded for the page at `url`, from (source URL, document
    metadata) pairs, most recent first - the first match wins."""
    for source, metadata in pages:
        if not source or not same_page(source, url) or not isinstance(metadata, dict):
            continue
        identity = SiteIdentity.from_metadata(metadata.get("identity"))
        if identity.image_url:
            return identity
    return None


# ------------------------------------------------------------------ internals


def _page_key(url: str) -> tuple[str, str]:
    try:
        parts = urlsplit(url.strip())
    except ValueError:
        return ("", "")
    return ((parts.hostname or "").removeprefix("www."), parts.path.rstrip("/"))


def _metas(head: BeautifulSoup) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for tag in head.find_all("meta"):
        key = str(tag.get("property") or tag.get("name") or "").strip().lower()
        content = str(tag.get("content") or "").strip()
        if key and content:
            found.setdefault(key, []).append(content)
    return found


def _first(metas: dict[str, list[str]], key: str) -> str:
    values = metas.get(key)
    return values[0] if values else ""


def _number(metas: dict[str, list[str]], key: str) -> int:
    value = _first(metas, key)
    return int(value) if value.isdigit() else 0


def _json_ld(html: str) -> Iterator[dict]:
    """Every top-level JSON-LD object, `@graph` members included - and only
    those, for the reason `_SELF_TYPES` gives."""
    for match in _JSON_LD_RE.finditer(html):
        text = match.group(1).strip()
        text = text.removeprefix("<!--").removesuffix("-->").strip()
        try:
            data = json.loads(text)
        except ValueError:
            continue
        for item in data if isinstance(data, list) else [data]:
            if not isinstance(item, dict):
                continue
            yield item
            graph = item.get("@graph")
            if isinstance(graph, list):
                yield from (member for member in graph if isinstance(member, dict))


def _types(item: dict) -> set[str]:
    declared = item.get("@type")
    values = declared if isinstance(declared, list) else [declared]
    return {str(value).rsplit("/", 1)[-1].lower() for value in values if value}


def _image_values(value: object) -> Iterator[str]:
    """The URLs in a schema.org image or logo, which may be a string, an
    ImageObject, or a list of either."""
    for item in value if isinstance(value, list) else [value]:
        if isinstance(item, str):
            yield item.strip()
        elif isinstance(item, dict):
            for key in ("url", "contentUrl"):
                if isinstance(item.get(key), str):
                    yield item[key].strip()
                    break


def _is_svg(url: str) -> bool:
    try:
        path = urlsplit(url).path.lower()
    except ValueError:
        return False
    return path.endswith(".svg") or url.lower().startswith("data:image/svg")


def _usable(url: str) -> bool:
    """An image an inbox can fetch and display: a public http(s) address that
    is not an SVG. A `data:` image is refused outright - Gmail strips them,
    and an embedded picture is the one thing that can push a message past its
    clipping limit."""
    try:
        parts = urlsplit(url)
    except ValueError:
        return False
    return (
        parts.scheme in {"http", "https"} and bool(parts.hostname)
        and not _is_svg(url) and not any(character.isspace() for character in url)
    )


def _logo(objects: list[dict], metas: dict[str, list[str]], page_url: str, notes: list[str]) -> str:
    declared = [
        urljoin(page_url, value)
        for item in objects if _types(item) & _SELF_TYPES
        for value in _image_values(item.get("logo")) if value
    ]
    declared += [urljoin(page_url, value) for value in metas.get("og:logo", [])]
    for url in declared:
        if _usable(url):
            return url
    if any(_is_svg(url) for url in declared):
        notes.append(
            "The site's logo is an SVG, which Gmail and Outlook do not display. "
            "Paste the address of a PNG or JPEG version to use it."
        )
    else:
        notes.append(
            "The site declares no logo for search engines, so none was picked up. "
            "Paste the address of a PNG or JPEG version to use one."
        )
    return ""


def _theme_colour(head: BeautifulSoup, notes: list[str]) -> str:
    for name in ("theme-color", "msapplication-tilecolor"):
        for tag in head.find_all("meta", attrs={"name": re.compile(f"^{name}$", re.IGNORECASE)}):
            # A dark-scheme colour is the toolbar at night, not the brand.
            if "dark" in str(tag.get("media") or "").lower():
                continue
            colour = parse_colour(str(tag.get("content") or ""))
            if not colour:
                continue
            if contrast(colour, WHITE) < MIN_SURFACE_CONTRAST:
                notes.append(
                    f"The site's theme colour ({colour}) is too pale to show on a white "
                    "email, so it was not used."
                )
                continue
            return colour
    if not any("theme colour" in note for note in notes):
        notes.append("The site declares no theme colour.")
    return ""


def _product(objects: list[dict]) -> dict | None:
    """The page's own product, if it sells one: a JSON-LD Product with an
    offer. Review widgets declare the whole shop as a Product with a rating
    and no offer, on every page including the home page."""
    for item in objects:
        if "product" in _types(item) and item.get("offers"):
            return item
    return None


def _is_product_page(page_url: str, metas: dict[str, list[str]], product: dict | None) -> bool:
    if not urlsplit(page_url).path.strip("/"):
        return False
    if _first(metas, "og:type").lower().startswith("product"):
        return True
    if _first(metas, "product:price:amount") or _first(metas, "og:price:amount"):
        return True
    return product is not None


def _picture(
    metas: dict[str, list[str]], product: dict | None, page_url: str, logo: str
) -> tuple[str, bool]:
    """The page's photograph and whether it came from Open Graph, whose
    declared dimensions then describe it."""
    open_graph = [
        value
        for key in ("og:image:secure_url", "og:image:url", "og:image", "twitter:image", "twitter:image:src")
        for value in metas.get(key, [])
    ]
    structured = list(_image_values(product.get("image"))) if product else []
    candidates = [
        (urljoin(page_url, value), index < len(open_graph))
        for index, value in enumerate(open_graph + structured) if value
    ]
    usable = [(url, graph) for url, graph in candidates if _usable(url) and url != logo]
    for url, graph in usable:
        if urlsplit(url).path.lower().endswith(_RASTER_SUFFIXES):
            return url, graph
    return usable[0] if usable else ("", False)


def _alt(product: dict | None, metas: dict[str, list[str]], head: BeautifulSoup) -> str:
    """What the picture shows, for the reader whose client blocked it: the
    product's own name, else the page title without the shop's name after
    it."""
    name = product.get("name") if product else None
    text = name if isinstance(name, str) and name.strip() else (
        _first(metas, "og:title") or (head.title.string if head.title and head.title.string else "")
    )
    text = re.split(r"\s+[|–—]\s+", text.strip())[0].strip()
    return text[:_MAX_ALT_CHARS]
