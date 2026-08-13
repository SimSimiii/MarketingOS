import pytest

from app.ingestion.documents import SourceType
from app.ingestion.exceptions import LoaderError
from app.ingestion.loaders.pdf_loader import PdfLoader
from tests.ingestion.conftest import build_minimal_pdf


@pytest.mark.asyncio
async def test_extracts_text_from_pdf(tmp_path):
    pdf_path = tmp_path / "doc.pdf"
    pdf_path.write_bytes(build_minimal_pdf(b"Hello PDF World"))

    raw = await PdfLoader().load(str(pdf_path))

    assert raw.source_type == SourceType.PDF
    assert "Hello PDF World" in raw.content
    assert raw.metadata["page_count"] == 1


@pytest.mark.asyncio
async def test_missing_file_raises_loader_error(tmp_path):
    with pytest.raises(LoaderError):
        await PdfLoader().load(str(tmp_path / "missing.pdf"))


@pytest.mark.asyncio
async def test_corrupt_pdf_raises_loader_error(tmp_path):
    pdf_path = tmp_path / "corrupt.pdf"
    pdf_path.write_bytes(b"not a real pdf")

    with pytest.raises(LoaderError):
        await PdfLoader().load(str(pdf_path))
