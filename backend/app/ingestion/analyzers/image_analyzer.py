from datetime import UTC, datetime
from typing import Any, ClassVar

from pydantic import BaseModel

from app.ingestion.analyzers.base import BaseAnalyzer
from app.ingestion.assets.base import Asset
from app.ingestion.documents import KnowledgeDocument, SourceType
from app.ingestion.ocr.base import OCRProvider
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

        ocr_result = await self._ocr.extract_text(content)
        description = await self._vision.analyze_image(content, mime_type)
        layout = await self._vision.describe_layout(content, mime_type)
        objects = await self._vision.identify_objects(content, mime_type)
        branding = await self._vision.identify_branding(content, mime_type)
        colors = await self._vision.identify_colors(content, mime_type)

        result = ImageAnalysisResult(
            asset_type=SourceType.IMAGE.value,
            vision_provider=type(self._vision).__name__,
            ocr_provider=type(self._ocr).__name__,
            ocr_text=ocr_result.text,
            description=description.description,
            detected_language=ocr_result.detected_language,
            detected_objects=objects.objects,
            detected_logos=branding.logos,
            dominant_colors=colors.colors,
            layout=layout.regions,
            confidence=description.confidence,
        )

        metadata: dict[str, Any] = {
            **result.model_dump(),
            "layout_details": layout.details,
            "asset": asset.model_dump(mode="json"),
        }

        document = KnowledgeDocument(
            title=asset.filename,
            source=SourceType.IMAGE,
            created_at=datetime.now(UTC),
            metadata=metadata,
            content=ocr_result.text,
            content_type=asset.mime_type,
            asset_id=asset.id,
        )
        return [document]
