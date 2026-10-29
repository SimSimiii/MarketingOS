"""Recover explicitly public article prose from inert page data, never execute it.

Only narrative fields are read. Application globals, accounts, test results,
prices, and arbitrary nested strings are deliberately outside this adapter.
"""

import html
import json
import re

from bs4 import BeautifulSoup

_MAX_STATE_CHARS = 500_000
_MAX_ARTICLE_CHARS = 60_000


def is_access_wall(title: str, content: str) -> bool:
    """Explicit access screens are not articles, even when they contain prose."""
    headings = re.sub(r"\W+", " ", html.unescape(title).casefold()).strip()
    if any(headings.endswith(phrase) for phrase in (
        "prove your humanity", "verify you are human", "just a moment", "access denied",
    )):
        return True
    beginning = re.sub(r"\W+", " ", html.unescape(content[:700]).casefold()).strip()
    return len(content) < 2000 and any(phrase in beginning for phrase in (
        "you ve been blocked by network security", "your request has been blocked due to a network policy",
        "verify you are human before continuing", "complete the captcha to continue",
    ))


def _public(value: dict) -> bool:
    return not any(value.get(key) is True for key in (
        "locked", "is_locked", "isPremium", "is_premium", "early_access", "paywalled",
        "paywall", "isBehindPaywall", "requiresSubscription",
    )) and value.get("isAccessibleForFree") is not False and value.get("published") is not False


def hydrate_public_article(soup: BeautifulSoup) -> None:
    """Attach a main only when the response has no substantive article/main."""
    if any(len(tag.get_text(" ", strip=True)) >= 200 for tag in soup.find_all(["main", "article"])):
        return
    for tag in soup.select('[data-props], script[type="application/ld+json"]'):
        raw = tag.get("data-props") if tag.has_attr("data-props") else tag.get_text()
        if not isinstance(raw, str) or len(raw) > _MAX_STATE_CHARS:
            continue
        try:
            data = json.loads(raw)
        except (ValueError, RecursionError):
            continue
        if not isinstance(data, dict) or not _public(data):
            continue
        parts: list[str] = []
        page = data.get("page_data", {}).get("page") if isinstance(data.get("page_data"), dict) else None
        if isinstance(page, dict) and _public(page) and page.get("type") in ("RecommendationPage", "ArticlePage"):
            content = page.get("recommendation") or page.get("article")
            if not isinstance(content, dict) or not _public(content):
                continue
            parts.extend(content[key] for key in ("introduction", "text")
                         if isinstance(content.get(key), str))
            # These are the public recommendation narratives, not the raw
            # measurements or member-only review tables in the same payload.
            recommendations = content.get("product_recommendations", [])
            if isinstance(recommendations, list):
                for item in recommendations[:20]:
                    if not isinstance(item, dict) or not _public(item):
                        continue
                    if isinstance(item.get("title"), str):
                        parts.append("<h2>" + html.escape(item["title"]) + "</h2>")
                    if isinstance(item.get("description"), str):
                        parts.append(item["description"])
            if isinstance(content.get("conclusion"), str):
                parts.append(content["conclusion"])
        elif data.get("@type") in ("Article", "NewsArticle", "BlogPosting"):
            if isinstance(data.get("articleBody"), str):
                parts.append("<p>" + html.escape(data["articleBody"]) + "</p>")
        if not parts:
            continue
        body = "\n".join(parts)
        if len(body) > _MAX_ARTICLE_CHARS:
            continue
        article = BeautifulSoup(body, "html.parser")
        if len(article.get_text(" ", strip=True)) < 200:
            continue
        main = soup.new_tag("main")
        title = data.get("title") or data.get("headline")
        if isinstance(title, str):
            heading = soup.new_tag("h1")
            heading.string = title
            main.append(heading)
        main.append(article)
        (soup.body or soup).append(main)
        return


def content_issues(markdown: str) -> list[str]:
    """Detect incomplete extraction, not whether a product is good or bad."""
    prose = re.sub(r"```.*?```", "", markdown, flags=re.DOTALL)
    issues = []
    if len(re.findall(r"(?im)^\s*null\s*:?\s*$", prose)) >= 8:
        issues.append("dynamic_values_missing")
    links = re.findall(r"\[[^\]]+\]\([^\n)]+\)", prose)
    without_links = re.sub(r"\[[^\]]+\]\([^\n)]+\)", "", prose)
    if len(links) >= 8 and len(re.sub(r"\W", "", without_links)) < 120:
        issues.append("navigation_only")
    return issues
