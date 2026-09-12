from datetime import UTC, datetime
from pathlib import Path

from app.ingestion.documents import RawDocument, SourceType
from app.ingestion.exceptions import LoaderError
from app.ingestion.loaders.base import Loader


class PlainTextLoader(Loader):
    """`source` is raw text, or a server-created .txt path when `is_path`."""

    source_type = SourceType.PLAIN_TEXT

    async def load(self, source: str, *, is_path: bool = False) -> RawDocument:
        content = source
        if is_path:
            try:
                content = Path(source).read_text(encoding="utf-8")
            except OSError as exc:
                raise LoaderError(f"Failed to read text source '{source}': {exc}") from exc

        return RawDocument(
            content=content.strip(),
            source=source,
            source_type=self.source_type,
            fetched_at=datetime.now(UTC),
        )
