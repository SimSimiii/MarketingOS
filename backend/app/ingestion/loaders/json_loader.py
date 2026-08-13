import json
from datetime import UTC, datetime
from pathlib import Path

from app.ingestion.documents import RawDocument, SourceType
from app.ingestion.exceptions import LoaderError
from app.ingestion.loaders.base import Loader


class JsonLoader(Loader):
    """`source` is either a path to an existing .json file, or a raw JSON
    string. Content becomes a pretty-printed text representation - JSON has
    no natural prose form, so this is the most faithful lossless rendering."""

    source_type = SourceType.JSON

    async def load(self, source: str) -> RawDocument:
        path = Path(source)
        raw_text = path.read_text(encoding="utf-8") if path.is_file() else source

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
