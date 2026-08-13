from pathlib import Path

from app.ingestion.documents import KnowledgeDocument, RawDocument
from app.ingestion.metadata import build_source_metadata
from app.ingestion.normalizers.base import Normalizer

_MARKDOWN_CONTENT_TYPES = {"website", "markdown"}


class DefaultNormalizer(Normalizer):
    """Generic normalizer that works for every MVP source unmodified. A new
    source only needs a custom Normalizer if its RawDocument doesn't fit this
    shape - title/author/content_type derivation is deliberately generic."""

    async def normalize(self, raw: RawDocument) -> KnowledgeDocument:
        title = raw.metadata.get("title") or self._fallback_title(raw)
        content_type = "text/markdown" if raw.source_type.value in _MARKDOWN_CONTENT_TYPES else (
            "application/json" if raw.source_type.value == "json" else "text/plain"
        )

        return KnowledgeDocument(
            title=title,
            source=raw.source_type,
            url=raw.metadata.get("url") or (raw.source if raw.source_type.value == "website" else None),
            author=raw.metadata.get("author") or None,
            created_at=raw.fetched_at,
            metadata=build_source_metadata(raw),
            content=raw.content,
            content_type=content_type,
        )

    @staticmethod
    def _fallback_title(raw: RawDocument) -> str:
        for line in raw.content.splitlines():
            stripped = line.strip().lstrip("#").strip()
            if stripped:
                return stripped[:120]
        return Path(raw.source).stem or raw.source
