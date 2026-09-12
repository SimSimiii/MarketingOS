from datetime import UTC, datetime
from pathlib import Path

from app.ingestion.documents import RawDocument, SourceType
from app.ingestion.exceptions import LoaderError
from app.ingestion.loaders.base import Loader


class MarkdownLoader(Loader):
    """`source` is raw Markdown, or a server-created .md path when `is_path`."""

    source_type = SourceType.MARKDOWN

    async def load(self, source: str, *, is_path: bool = False) -> RawDocument:
        content = source
        if is_path:
            try:
                content = Path(source).read_text(encoding="utf-8")
            except OSError as exc:
                raise LoaderError(f"Failed to read markdown source '{source}': {exc}") from exc

        return RawDocument(
            content=content.strip(),
            source=source,
            source_type=self.source_type,
            fetched_at=datetime.now(UTC),
        )
