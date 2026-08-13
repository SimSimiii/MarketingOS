from datetime import UTC, datetime
from pathlib import Path

from app.ingestion.documents import RawDocument, SourceType
from app.ingestion.exceptions import LoaderError
from app.ingestion.loaders.base import Loader


class PlainTextLoader(Loader):
    """`source` is either a path to an existing .txt file, or raw text."""

    source_type = SourceType.PLAIN_TEXT

    async def load(self, source: str) -> RawDocument:
        path = Path(source)
        try:
            content = path.read_text(encoding="utf-8") if path.is_file() else source
        except OSError as exc:
            raise LoaderError(f"Failed to read text source '{source}': {exc}") from exc

        return RawDocument(
            content=content.strip(),
            source=source,
            source_type=self.source_type,
            fetched_at=datetime.now(UTC),
        )
