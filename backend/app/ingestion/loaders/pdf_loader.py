from datetime import UTC, datetime
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.ingestion.documents import RawDocument, SourceType
from app.ingestion.exceptions import LoaderError
from app.ingestion.loaders.base import Loader


class PdfLoader(Loader):
    """`source` is a server-created path to a .pdf file (`is_path`). Extracts page text only - no OCR,
    no layout reconstruction, no LLM."""

    source_type = SourceType.PDF

    async def load(self, source: str, *, is_path: bool = False) -> RawDocument:
        # A PDF only ever reaches us as an uploaded file, written to a
        # temporary path by the server. Reading a path the caller did not
        # vouch for would make any pasted string ending in ".pdf" a request
        # to read that file off this machine.
        if not is_path:
            raise LoaderError(
                "A PDF must be uploaded as a file, not submitted as text."
            )
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
