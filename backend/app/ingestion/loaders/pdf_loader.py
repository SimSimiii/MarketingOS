from datetime import UTC, datetime
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.ingestion.documents import RawDocument, SourceType
from app.ingestion.exceptions import LoaderError
from app.ingestion.loaders.base import Loader


class PdfLoader(Loader):
    """`source` is a path to a .pdf file. Extracts page text only - no OCR,
    no layout reconstruction, no LLM."""

    source_type = SourceType.PDF

    async def load(self, source: str) -> RawDocument:
        path = Path(source)
        if not path.is_file():
            raise LoaderError(f"PDF source not found: '{source}'")

        try:
            reader = PdfReader(str(path))
            pages = [page.extract_text() or "" for page in reader.pages]
        except PdfReadError as exc:
            raise LoaderError(f"Failed to read PDF '{source}': {exc}") from exc

        content = "\n\n".join(page.strip() for page in pages if page.strip())
        metadata = dict(reader.metadata or {})

        return RawDocument(
            content=content,
            source=source,
            source_type=self.source_type,
            fetched_at=datetime.now(UTC),
            metadata={
                "title": (metadata.get("/Title") or "").strip(),
                "author": (metadata.get("/Author") or "").strip(),
                "page_count": len(reader.pages),
            },
        )
