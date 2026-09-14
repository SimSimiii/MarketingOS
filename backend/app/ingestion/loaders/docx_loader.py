from datetime import UTC, datetime

from app.ingestion.documents import RawDocument, SourceType
from app.ingestion.exceptions import LoaderError
from app.ingestion.extraction import extract_document
from app.ingestion.loaders.base import Loader


class DocxLoader(Loader):
    source_type = SourceType.DOCX

    async def load(self, source: str, *, is_path: bool = False) -> RawDocument:
        if not is_path:
            raise LoaderError("A DOCX must be uploaded as a file, not submitted as text.")
        result = await extract_document("docx", source)
        return RawDocument(source=source, source_type=self.source_type,
                           fetched_at=datetime.now(UTC), **result)
