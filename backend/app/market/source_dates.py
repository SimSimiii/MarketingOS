"""Publication dates from the fetched page, never the search model's memory."""

import json
import re
from datetime import date
from urllib.parse import urlsplit

from bs4 import BeautifulSoup


def _parse(value: str, as_of: date) -> date | None:
    match = re.search(r"\b(\d{4})[-/](\d{2})[-/](\d{2})(?!\d)", value)
    if not match:
        return None
    try:
        found = date(*(int(part) for part in match.groups()))
    except ValueError:
        return None
    return found if date(1990, 1, 1) <= found <= as_of else None


def date_from_url(url: str, as_of: date) -> date | None:
    # Ignore query parameters and fragments; a search date is not publication.
    return _parse(urlsplit(url).path, as_of)


def publication_date(html: str, url: str, as_of: date) -> tuple[date | None, str]:
    soup = BeautifulSoup(html, "html.parser")
    for meta in soup.find_all("meta"):
        key = str(meta.get("property") or meta.get("name") or meta.get("itemprop") or "").lower()
        if key in {"article:published_time", "datepublished", "pubdate", "dc.date.issued"}:
            found = _parse(str(meta.get("content", "")), as_of)
            if found:
                return found, "page_publication_metadata"

    def published(value: object) -> date | None:
        if isinstance(value, dict):
            found = _parse(str(value.get("datePublished", "")), as_of)
            if found:
                return found
            for child in (value.get("@graph"), value.get("mainEntity")):
                if isinstance(child, (dict, list)) and (found := published(child)):
                    return found
        if isinstance(value, list):
            for child in value:
                if found := published(child):
                    return found
        return None

    for script in soup.find_all("script", type="application/ld+json"):
        try:
            found = published(json.loads(script.string or script.get_text()))
        except (ValueError, RecursionError):
            continue
        if found:
            return found, "page_structured_publication_date"
    for time in soup.select('time[itemprop="datePublished"], time.published, time.entry-date'):
        if found := _parse(str(time.get("datetime", "")), as_of):
            return found, "page_publication_time"
    # Some article templates show a plain date directly below the title.
    # Do not scan prose, sidebars or footers for years: those are not dates
    # of publication, and dateModified above deliberately does not qualify.
    title = soup.find("h1")
    months = {name: number for number, names in enumerate(
        (("jan", "january"), ("feb", "february"), ("mar", "march"), ("apr", "april"),
         ("may",), ("jun", "june"), ("jul", "july"), ("aug", "august"),
         ("sep", "sept", "september"), ("oct", "october"), ("nov", "november"), ("dec", "december")), 1
    ) for name in names}
    for sibling in title.find_next_siblings(limit=3) if title else []:
        if sibling.name not in {"p", "time"}:
            continue
        text = sibling.get_text(" ", strip=True)
        match = re.fullmatch(r"(\d{1,2})\s+([A-Za-z]{3,9})\s+(\d{4})", text)
        if match and match.group(2).lower() in months:
            try:
                found = date(int(match.group(3)), months[match.group(2).lower()], int(match.group(1)))
            except ValueError:
                continue
            if date(1990, 1, 1) <= found <= as_of:
                return found, "page_title_date"
    if found := date_from_url(url, as_of):
        return found, "dated_url"
    return None, "unknown"
