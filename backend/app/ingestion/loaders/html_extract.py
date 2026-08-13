"""Turning a fetched page into readable content and onward links.

Shared by the single-page loader and the crawler so both see a page the same
way - a crawler that extracted content differently from the loader would make
the depth of a run change what it believes about the same URL.
"""

from urllib.parse import urldefrag, urljoin, urlparse

from bs4 import BeautifulSoup
from markdownify import markdownify

#: Chrome, navigation and scripting - never the content a marketer wrote.
_REMOVED_TAGS = ("script", "style", "nav", "header", "footer", "noscript", "svg", "form")

#: Paths that never carry marketing evidence, and one of which (login) will
#: happily serve a crawler a hundred identical pages.
_SKIP_SEGMENTS = frozenset(
    (
        "login", "signin", "sign-in", "signup", "sign-up", "register", "logout",
        "account", "dashboard", "app", "admin", "cart", "checkout",
        "privacy", "terms", "legal", "cookie", "cookies", "gdpr", "dpa", "imprint",
        "careers", "jobs", "unsubscribe", "rss", "feed", "sitemap", "search",
        "tag", "tags", "author", "authors", "category",
    )
)
_SKIP_SUFFIXES = (
    ".pdf", ".zip", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".mp4", ".mp3",
    ".css", ".js", ".xml", ".ics", ".dmg", ".exe",
)

#: Pages worth reading first, highest first. This ordering is most of what
#: makes a small crawl budget produce a usable evidence ledger: pricing and
#: customer pages carry the specifics, the blog carries the voice.
_PRIORITY_HINTS: tuple[tuple[int, tuple[str, ...]], ...] = (
    (100, ("pricing", "plans", "price")),
    (90, ("customers", "case-stud", "case_stud", "testimonial", "stories", "success")),
    (80, ("product", "features", "how-it-works", "how_it_works", "platform", "solutions")),
    (70, ("about", "company", "why", "manifesto")),
    (60, ("docs", "documentation", "quickstart", "getting-started", "guide")),
    (50, ("security", "compliance", "trust", "soc2")),
    (40, ("faq", "help", "support")),
    (30, ("blog", "changelog", "news", "release")),
    (20, ("integrations", "connect", "api")),
)


def extract_content(html: str) -> tuple[str, str, str]:
    """(title, meta description, markdown body) for one page."""
    soup = BeautifulSoup(html, "html.parser")

    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    description_tag = soup.find("meta", attrs={"name": "description"})
    description = description_tag.get("content", "").strip() if description_tag else ""

    for tag_name in _REMOVED_TAGS:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    body = soup.body or soup
    markdown = markdownify(str(body), heading_style="ATX", bullets="-").strip()
    return title, description, markdown


def extract_links(html: str, base_url: str) -> list[str]:
    """Same-site pages worth following, best first.

    Only the starting site is followed. A crawler that wandered onto a
    competitor's domain because the footer linked to it would quietly file
    someone else's claims as this company's evidence.
    """
    soup = BeautifulSoup(html, "html.parser")
    origin = urlparse(base_url).netloc.lower().removeprefix("www.")

    scored: dict[str, int] = {}
    for anchor in soup.find_all("a", href=True):
        href = str(anchor["href"]).strip()
        if not href or href.startswith(("mailto:", "tel:", "javascript:", "#")):
            continue
        resolved, _ = urldefrag(urljoin(base_url, href))
        parsed = urlparse(resolved)
        if parsed.scheme not in ("http", "https"):
            continue
        if parsed.netloc.lower().removeprefix("www.") != origin:
            continue
        if not is_worth_reading(resolved):
            continue
        score = priority_of(resolved)
        if score > scored.get(resolved, -1):
            scored[resolved] = score

    return sorted(scored, key=lambda url: (-scored[url], len(url)))


def is_worth_reading(url: str) -> bool:
    path = urlparse(url).path.lower()
    if path.endswith(_SKIP_SUFFIXES):
        return False
    segments = {segment for segment in path.split("/") if segment}
    return not (segments & _SKIP_SEGMENTS)


def priority_of(url: str) -> int:
    """How badly a marketing system wants this page. Ties break on shallowness -
    /pricing beats /pricing/enterprise/eu when the budget only allows one."""
    path = urlparse(url).path.lower()
    for score, hints in _PRIORITY_HINTS:
        if any(hint in path for hint in hints):
            return score
    depth = len([segment for segment in path.split("/") if segment])
    #: The home page (depth 0) is always worth having.
    return 95 if depth == 0 else max(1, 15 - depth)
