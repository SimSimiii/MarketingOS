import json
from datetime import UTC, datetime
from pathlib import Path

from app.ingestion.documents import RawDocument, SourceType
from app.ingestion.exceptions import LoaderError
from app.ingestion.loaders.base import Loader


class JsonLoader(Loader):
    """`source` is a raw JSON string, or a server-created .json path when
    `is_path`. Content becomes a pretty-printed text representation - JSON has
    no natural prose form, so this is the most faithful lossless rendering."""

    source_type = SourceType.JSON

    async def load(self, source: str, *, is_path: bool = False) -> RawDocument:
        raw_text = source
        if is_path:
            try:
                raw_text = Path(source).read_text(encoding="utf-8")
            except OSError as exc:
                raise LoaderError(f"Failed to read JSON source '{source}': {exc}") from exc

        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise LoaderError(f"Invalid JSON in source '{source}': {exc}") from exc

        content = json.dumps(data, indent=2, ensure_ascii=False)

        return RawDocument(
            content=content,
            source=source,
            source_type=self.source_type,
            fetched_at=datetime.now(UTC),
        )
