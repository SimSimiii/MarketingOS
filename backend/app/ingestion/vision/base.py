from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class ImageDescription(BaseModel):
    """Factual visual description - no summarization or subjective judgment."""

    description: str
    confidence: float = 1.0


class ExtractedText(BaseModel):
    """Text a vision model reads directly off an image. Independent from
    OCRProvider - this is a second, separate way to get text, not a
    replacement for it."""

    text: str
    detected_language: str | None = None


class LayoutDescription(BaseModel):
    """Structural regions detected in the image (e.g. header, hero, footer),
    purely descriptive."""

    regions: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class DetectedObjects(BaseModel):
    objects: list[str] = Field(default_factory=list)


class BrandingInfo(BaseModel):
    logos: list[str] = Field(default_factory=list)
    brand_names: list[str] = Field(default_factory=list)


class DominantColors(BaseModel):
    colors: list[str] = Field(default_factory=list)  # hex codes, most dominant first


class VisionProvider(ABC):
    """Contract every vision backend (Claude, GPT, Gemini, local models)
    implements. Every operation is factual/structural extraction only - never
    summarization or marketing judgment."""

    @abstractmethod
    async def analyze_image(self, image: bytes, mime_type: str) -> ImageDescription:
        raise NotImplementedError

    @abstractmethod
    async def extract_text(self, image: bytes, mime_type: str) -> ExtractedText:
        raise NotImplementedError

    @abstractmethod
    async def describe_layout(self, image: bytes, mime_type: str) -> LayoutDescription:
        raise NotImplementedError

    @abstractmethod
    async def identify_objects(self, image: bytes, mime_type: str) -> DetectedObjects:
        raise NotImplementedError

    @abstractmethod
    async def identify_branding(self, image: bytes, mime_type: str) -> BrandingInfo:
        raise NotImplementedError

    @abstractmethod
    async def identify_colors(self, image: bytes, mime_type: str) -> DominantColors:
        raise NotImplementedError
