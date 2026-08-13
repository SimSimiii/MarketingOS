import io

import pytesseract
from langdetect import LangDetectException, detect
from PIL import Image, UnidentifiedImageError

from app.ingestion.exceptions import AnalysisError
from app.ingestion.ocr.base import OCRProvider, OCRResult


def _detect_language(text: str) -> str | None:
    if len(text.strip()) < 20:
        return None
    try:
        return detect(text)
    except LangDetectException:
        return None


class TesseractOCRProvider(OCRProvider):
    """OCRProvider backed by the Tesseract OCR engine via `pytesseract`.

    Requires the `tesseract` binary to be installed separately on the host
    (e.g. via the platform's package manager) - `pytesseract` is only a thin
    Python wrapper around that executable, same shape of external dependency
    as the Claude CLI that app.ai.claude_provider.ClaudeProvider relies on.
    """

    async def extract_text(self, image: bytes) -> OCRResult:
        try:
            with Image.open(io.BytesIO(image)) as pil_image:
                text = pytesseract.image_to_string(pil_image)
        except UnidentifiedImageError as exc:
            raise AnalysisError(f"Not a readable image for OCR: {exc}") from exc
        except pytesseract.TesseractNotFoundError as exc:
            raise AnalysisError(
                "Tesseract binary not found - install it separately (pytesseract only "
                f"wraps the executable, it doesn't bundle it): {exc}"
            ) from exc

        stripped = text.strip()
        return OCRResult(text=stripped, detected_language=_detect_language(stripped))
