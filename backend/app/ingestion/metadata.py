import hashlib
from typing import Any
from urllib.parse import urlparse

from langdetect import LangDetectException, detect

from app.ingestion.documents import RawDocument, SourceType

_WORDS_PER_MINUTE = 200


def _domain(source: str) -> str | None:
    parsed = urlparse(source)
    return parsed.netloc or None


def _detect_language(content: str) -> str | None:
    # langdetect is unreliable on very short strings and raises rather than
    # returning None - treat any failure as "undetectable".
    if len(content.strip()) < 20:
        return None
    try:
        return detect(content)
    except LangDetectException:
        return None


def build_source_metadata(raw: RawDocument) -> dict[str, Any]:
    """Metadata derivable from the raw fetch itself (source, not content).
    Safe to compute before cleaning - none of it depends on final text."""

    is_website = raw.source_type == SourceType.WEBSITE
    computed = {
        "source_type": raw.source_type.value,
        "url": raw.source if is_website else raw.metadata.get("url"),
        "domain": _domain(raw.source) if is_website else None,
        "crawl_timestamp": raw.fetched_at.isoformat(),
    }
    return {**raw.metadata, **computed}


def compute_content_metrics(content: str) -> dict[str, Any]:
    """Metadata that depends on the final (cleaned) content: must be computed
    after cleaning, not at normalization time, so word counts/hashes/language
    reflect what's actually stored."""

    word_count = len(content.split())
    return {
        "word_count": word_count,
        "reading_time_minutes": round(word_count / _WORDS_PER_MINUTE, 2),
        "language": _detect_language(content),
        "content_hash": hashlib.sha256(content.strip().encode("utf-8")).hexdigest(),
    }
