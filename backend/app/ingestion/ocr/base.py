from abc import ABC, abstractmethod

from pydantic import BaseModel


class OCRResult(BaseModel):
    text: str
    detected_language: str | None = None


class OCRProvider(ABC):
    """Reusable OCR abstraction, deliberately independent from VisionProvider
    - implementations use traditional OCR engines, never an LLM. ImageAnalyzer
    is the only place OCR and vision results get combined."""

    @abstractmethod
    async def extract_text(self, image: bytes) -> OCRResult:
        raise NotImplementedError
