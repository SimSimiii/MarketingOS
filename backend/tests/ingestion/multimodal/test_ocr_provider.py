import pytest

from app.ingestion.exceptions import AnalysisError
from app.ingestion.ocr.base import OCRProvider
from app.ingestion.ocr.tesseract_provider import TesseractOCRProvider


def test_ocr_provider_is_abstract():
    with pytest.raises(TypeError):
        OCRProvider()  # type: ignore[abstract]


@pytest.mark.asyncio
async def test_fake_ocr_provider_returns_text(fake_ocr, png_bytes):
    result = await fake_ocr.extract_text(png_bytes)
    assert result.text == "Buy Now"
    assert result.detected_language == "en"


@pytest.mark.asyncio
async def test_tesseract_provider_extracts_text(monkeypatch, png_bytes):
    monkeypatch.setattr(
        "app.ingestion.ocr.tesseract_provider.pytesseract.image_to_string",
        lambda image: "Hello from OCR",
    )

    result = await TesseractOCRProvider().extract_text(png_bytes)
    assert result.text == "Hello from OCR"


@pytest.mark.asyncio
async def test_tesseract_provider_rejects_non_image_bytes():
    with pytest.raises(AnalysisError):
        await TesseractOCRProvider().extract_text(b"not an image")


@pytest.mark.asyncio
async def test_tesseract_provider_wraps_missing_binary(monkeypatch, png_bytes):
    import pytesseract

    def raise_not_found(image):
        raise pytesseract.TesseractNotFoundError()

    monkeypatch.setattr(
        "app.ingestion.ocr.tesseract_provider.pytesseract.image_to_string", raise_not_found
    )

    with pytest.raises(AnalysisError):
        await TesseractOCRProvider().extract_text(png_bytes)


@pytest.mark.asyncio
async def test_tesseract_provider_short_text_has_no_detected_language(monkeypatch, png_bytes):
    monkeypatch.setattr(
        "app.ingestion.ocr.tesseract_provider.pytesseract.image_to_string", lambda image: "hi"
    )
    result = await TesseractOCRProvider().extract_text(png_bytes)
    assert result.detected_language is None
