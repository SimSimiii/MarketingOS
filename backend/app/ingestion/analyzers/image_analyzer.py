from datetime import UTC, datetime
from typing import Any, ClassVar

from pydantic import BaseModel

from app.ingestion.analyzers.base import BaseAnalyzer
from app.ingestion.assets.base import Asset
from app.ingestion.documents import KnowledgeDocument, SourceType
from app.ingestion.exceptions import AnalysisError
from app.ingestion.ocr.base import OCRProvider, OCRResult
from app.ingestion.vision.base import VisionProvider


class ImageAnalysisResult(BaseModel):
    """The output_schema for ImageAnalyzer - also exactly what ends up in the
    produced KnowledgeDocument's metadata."""

    asset_type: str
    vision_provider: str
    ocr_provider: str
    ocr_text: str
    description: str
    detected_language: str | None
    detected_objects: list[str]
    detected_logos: list[str]
    dominant_colors: list[str]
    layout: list[str]
    confidence: float


class ImageAnalyzer(BaseAnalyzer):
    """Combines an OCRProvider and a VisionProvider (both injected - never
    instantiated here) into one factual KnowledgeDocument per image. Never
    summarizes; every field is a direct, structural extraction."""

    supported_asset_types: ClassVar[set[SourceType]] = {SourceType.IMAGE}
    output_schema: ClassVar[type[BaseModel]] = ImageAnalysisResult

    def __init__(self, ocr: OCRProvider, vision: VisionProvider) -> None:
        self._ocr = ocr
        self._vision = vision

    async def analyze(self, asset: Asset, content: bytes) -> list[KnowledgeDocument]:
        mime_type = asset.mime_type

        ocr_error = ""
        try:
            ocr_result = await self._ocr.extract_text(content)
        except (AnalysisError, RuntimeError) as exc:
            ocr_error = str(exc)
            ocr_result = OCRResult(text="", detected_language=None)
        visual = await self._vision.read_image(content, mime_type)

        result = ImageAnalysisResult(
            asset_type=SourceType.IMAGE.value,
            vision_provider=type(self._vision).__name__,
            ocr_provider=type(self._ocr).__name__,
            ocr_text=ocr_result.text,
            description=visual.description,
            detected_language=ocr_result.detected_language,
            detected_objects=visual.objects,
            detected_logos=visual.logos,
            dominant_colors=visual.colors,
            layout=visual.regions,
            confidence=visual.confidence,
        )

        metadata: dict[str, Any] = {
            **result.model_dump(),
            "layout_details": visual.details,
            "ocr_error": ocr_error,
            "vision_usage": getattr(self._vision, "usage", {}),
            "transcription_source": "ocr" if ocr_result.text.strip() else "vision",
            "asset": asset.model_dump(mode="json"),
        }

        document = KnowledgeDocument(
            title=asset.filename,
            source=SourceType.IMAGE,
            created_at=datetime.now(UTC),
            metadata=metadata,
            content=(f"Visible text ({'OCR' if ocr_result.text.strip() else 'vision transcription'}):\n"
                     f"{ocr_result.text or visual.text}\n\n"
                     f"Visual observation (not a product performance claim):\n{visual.description}"),
            content_type=asset.mime_type,
            asset_id=asset.id,
        )
        return [document]
