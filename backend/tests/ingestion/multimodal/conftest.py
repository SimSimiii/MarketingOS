import io

import pytest
from PIL import Image

from app.ingestion.ocr.base import OCRProvider, OCRResult
from app.ingestion.vision.base import (
    BrandingInfo,
    DetectedObjects,
    DominantColors,
    ExtractedText,
    ImageDescription,
    LayoutDescription,
    VisionProvider,
)


def make_png_bytes(color: str = "blue", size: tuple[int, int] = (12, 8)) -> bytes:
    image = Image.new("RGB", size, color=color)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture
def png_bytes() -> bytes:
    return make_png_bytes()


@pytest.fixture
def png_path(tmp_path):
    path = tmp_path / "product.png"
    path.write_bytes(make_png_bytes())
    return path


class FakeOCRProvider(OCRProvider):
    def __init__(self, text: str = "Buy Now", language: str | None = "en") -> None:
        self.text = text
        self.language = language
        self.calls: list[bytes] = []

    async def extract_text(self, image: bytes) -> OCRResult:
        self.calls.append(image)
        return OCRResult(text=self.text, detected_language=self.language)


class FakeVisionProvider(VisionProvider):
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def analyze_image(self, image: bytes, mime_type: str) -> ImageDescription:
        self.calls.append("analyze_image")
        return ImageDescription(description="A factual description of the image", confidence=0.9)

    async def extract_text(self, image: bytes, mime_type: str) -> ExtractedText:
        self.calls.append("extract_text")
        return ExtractedText(text="Buy Now", detected_language="en")

    async def describe_layout(self, image: bytes, mime_type: str) -> LayoutDescription:
        self.calls.append("describe_layout")
        return LayoutDescription(
            regions=["header", "hero", "navigation", "cta button", "footer"],
            details={"typography": ["sans-serif"]},
        )

    async def identify_objects(self, image: bytes, mime_type: str) -> DetectedObjects:
        self.calls.append("identify_objects")
        return DetectedObjects(objects=["bottle", "label"])

    async def identify_branding(self, image: bytes, mime_type: str) -> BrandingInfo:
        self.calls.append("identify_branding")
        return BrandingInfo(logos=["Acme"], brand_names=["Acme Co"])

    async def identify_colors(self, image: bytes, mime_type: str) -> DominantColors:
        self.calls.append("identify_colors")
        return DominantColors(colors=["#ffffff", "#ff0000"])


@pytest.fixture
def fake_ocr() -> FakeOCRProvider:
    return FakeOCRProvider()


@pytest.fixture
def fake_vision() -> FakeVisionProvider:
    return FakeVisionProvider()
