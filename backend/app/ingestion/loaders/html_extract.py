"""Turning a fetched page into readable content and onward links.

Shared by the single-page loader and the crawler so both see a page the same
way - a crawler that extracted content differently from the loader would make
the depth of a run change what it believes about the same URL.
"""

import re
from urllib.parse import parse_qs, urldefrag, urljoin, urlparse

from bs4 import BeautifulSoup
from markdownify import markdownify

from app.ingestion.loaders.public_content import hydrate_public_article

#: Navigation and scripting. A header may contain product or pricing copy,
#: rather than site chrome; it is handled separately below.
_REMOVED_TAGS = ("script", "style", "nav", "footer", "noscript", "svg")

_DOCUMENTATION_HOSTS = frozenset({"docs", "doc", "documentation", "help", "support",
                                   "developers", "developer"})

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
    hydrate_public_article(soup)

    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    description_tag = soup.find("meta", attrs={"name": "description"})
    description = description_tag.get("content", "").strip() if description_tag else ""

    for tag_name in _REMOVED_TAGS:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    # Purchase and signup forms can contain the only published price or trial
    # condition. Keep their copy; field values are not rendered by markdownify.
    for form in soup.find_all("form"):
        action = urlparse(str(form.get("action", ""))).path.rstrip("/")
        if form.get("role") == "search" or action in {"/search", "/localization"}:
            form.decompose()
        else:
            form.unwrap()

    # CDN query strings are not product facts. Preserve accessible descriptions,
    # captions and enclosing hyperlink destinations without reading image URLs
    # as thousands of characters of evidence. Literal code remains untouched.
    for picture in soup.find_all("img"):
        if picture.find_parent(["pre", "code"]) is not None:
            continue
        labels = [str(picture.get(key, "")).strip() for key in ("alt", "title")]
        picture.replace_with(" ".join(dict.fromkeys(label for label in labels if label)))

    for tag in soup.select('[role="navigation"]'):
        tag.decompose()
    for tag in soup.find_all(["header", "aside"]):
        links = tag.find_all("a")
        text = tag.get_text(" ", strip=True)
        if len(links) >= 3 and text and sum(len(link.get_text(" ", strip=True)) for link in links) / len(text) > 0.7:
            tag.decompose()

    for header in soup.find_all("header"):
        in_content = header.find_parent(["main", "article", "section"]) is not None
        has_copy = header.find(["h1", "h2", "h3", "h4", "h5", "h6", "p"]) is not None
        if not in_content and not has_copy:
            header.decompose()

    for anchor in soup.find_all("a", href=True):
        href = str(anchor["href"])
        if re.search(r"(?:facebook\.com/sharer|linkedin\.com/shareArticle|"
                     r"(?:twitter|x)\.com/intent/|threads\.com/intent/|reddit\.com/submit|"
                     r"chatgpt\.com/\?prompt=|claude\.ai/new\?q=)", href):
            anchor.decompose()

    body = soup.body or soup
    mains = soup.find_all("main")
    if len(mains) == 1 and len(mains[0].get_text(" ", strip=True)) >= 200:
        # Keep real hero/offer headers outside main; a navigation header was
        # removed above. Link discovery still uses the complete original HTML.
        heroes = [header for header in soup.find_all("header")
                  if header.find_parent(["main", "article", "section"]) is None
                  and header.find(["h1", "h2", "p"]) is not None]
        body = "\n".join(str(header) for header in heroes) + str(mains[0])
    markdown = markdownify(str(body), heading_style="ATX", bullets="-").strip()
    return title, description, markdown


def within_source_site(url: str, root_url: str) -> bool:
    """Allow only the source host and linked documentation hosts beneath it.

    No sibling domains, arbitrary subdomains or guessed documentation URLs.
    Every fetch still passes public_http's redirect and public-address checks.
    """
    try:
        target, root = urlparse(url), urlparse(root_url)
        host = (target.hostname or "").lower().removeprefix("www.")
        origin = (root.hostname or "").lower().removeprefix("www.")
        ports_match = target.port == root.port
    except ValueError:
        return False
    if target.scheme not in {"http", "https"} or target.username or target.password:
        return False
    if host == origin:
        return ports_match
    return any(host == prefix + "." + origin for prefix in _DOCUMENTATION_HOSTS) and ports_match


def extract_links(html: str, base_url: str, *, site_root: str | None = None) -> list[str]:
    return [url for url, _ in extract_link_candidates(html, base_url, site_root=site_root)]


_FOCUS_STOP = frozenset(["the", "and", "for", "with", "from", "that", "this", "their", "our", "your", "site", "company", "product", "products", "service", "services", "customer", "customers", "review", "reviews", "test", "tests", "testing", "independent", "across", "about", "using", "people", "into", "than", "what", "which", "they", "them", "offer", "offers"])


def _focus_words(text: str) -> set[str]:
    return {word.removesuffix("s") for word in re.findall(r"[a-zA-Z]{2,}", text.lower())
            if word not in _FOCUS_STOP}


def extract_link_candidates(
    html: str, base_url: str, *, site_root: str | None = None, focus: str = "",
) -> list[tuple[str, int]]:
    """Same-site pages worth following, best first.

    Follow the source host and its linked documentation subdomains. Other
    domains and arbitrary subdomains cannot become this company's evidence.
    """
    soup = BeautifulSoup(html, "html.parser")
    hydrate_public_article(soup)

    scored: dict[str, int] = {}
    focus_words = _focus_words(focus)
    for anchor in soup.find_all("a", href=True):
        href = str(anchor["href"]).strip()
        if not href or href.startswith(("mailto:", "tel:", "javascript:", "#")):
            continue
        try:
            resolved, _ = urldefrag(urljoin(base_url, href))
            parsed = urlparse(resolved)
        except ValueError:
            continue
        if parsed.scheme not in ("http", "https"):
            continue
        if not within_source_site(resolved, site_root or base_url):
            continue
        if not is_worth_reading(resolved):
            continue
        score = priority_of(resolved)
        if focus_words:
            matched = focus_words & _focus_words(parsed.path + " " + anchor.get_text(" ", strip=True))
            score = score + min(150, 70 * len(matched)) if matched else min(score, 60)
        if score > scored.get(resolved, -1):
            scored[resolved] = score

    return sorted(scored.items(), key=lambda item: (-item[1], len(item[0])))


def is_worth_reading(url: str) -> bool:
    path = urlparse(url).path.lower()
    if path.endswith(_SKIP_SUFFIXES):
        return False
    if re.search(r"/(?:page|pages)/\d+(?:/|$)", path) or any(
        key in parse_qs(urlparse(url).query) for key in ("page", "paged", "offset")
    ):
        return False
    segments = {segment for segment in path.split("/") if segment}
    return not (segments & _SKIP_SEGMENTS)


def priority_of(url: str) -> int:
    """How badly a marketing system wants this page. Ties break on shallowness -
    /pricing beats /pricing/enterprise/eu when the budget only allows one."""
    path = urlparse(url).path.lower()
    for score, hints in _PRIORITY_HINTS:
        if score == 100:
            matched = bool(re.search(r"/(?:pricing|plans?|prices?)(?:/|$)", path))
        else:
            matched = any(hint in path for hint in hints)
        if matched:
            return score
    depth = len([segment for segment in path.split("/") if segment])
    #: The home page (depth 0) is always worth having.
    return 95 if depth == 0 else max(1, 15 - depth)
