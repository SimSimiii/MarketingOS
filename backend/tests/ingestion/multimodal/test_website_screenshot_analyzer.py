import pytest

from app.ingestion.analyzers.website_screenshot_analyzer import WebsiteScreenshotAnalyzer
from app.ingestion.assets.loader import AssetLoader


@pytest.mark.asyncio
async def test_detects_hero_navigation_and_cta(png_path, fake_ocr, fake_vision):
    asset, content = AssetLoader().load_image(str(png_path))
    [document] = await WebsiteScreenshotAnalyzer(ocr=fake_ocr, vision=fake_vision).analyze(asset, content)

    assert document.metadata["hero_present"] is True
    assert document.metadata["navigation_present"] is True
    assert document.metadata["cta_present"] is True


@pytest.mark.asyncio
async def test_marketing_sections_exclude_chrome_regions(png_path, fake_ocr, fake_vision):
    asset, content = AssetLoader().load_image(str(png_path))
    [document] = await WebsiteScreenshotAnalyzer(ocr=fake_ocr, vision=fake_vision).analyze(asset, content)

    marketing_sections = document.metadata["marketing_sections"]
    assert "hero" in marketing_sections
    assert "cta button" in marketing_sections
    assert "header" not in marketing_sections
    assert "footer" not in marketing_sections
    assert "navigation" not in marketing_sections


@pytest.mark.asyncio
async def test_typography_captured_when_available(png_path, fake_ocr, fake_vision):
    asset, content = AssetLoader().load_image(str(png_path))
    [document] = await WebsiteScreenshotAnalyzer(ocr=fake_ocr, vision=fake_vision).analyze(asset, content)

    assert document.metadata["typography"] == ["sans-serif"]


@pytest.mark.asyncio
async def test_no_hero_or_cta_when_regions_absent(png_path, fake_ocr):
    from app.ingestion.vision.base import (
        BrandingInfo,
        DetectedObjects,
        DominantColors,
        ExtractedText,
        ImageDescription,
        LayoutDescription,
        VisionProvider,
    )

    class BareVisionProvider(VisionProvider):
        async def analyze_image(self, image, mime_type):
            return ImageDescription(description="plain image")

        async def extract_text(self, image, mime_type):
            return ExtractedText(text="")

        async def describe_layout(self, image, mime_type):
            return LayoutDescription(regions=["body"])

        async def identify_objects(self, image, mime_type):
            return DetectedObjects()

        async def identify_branding(self, image, mime_type):
            return BrandingInfo()

        async def identify_colors(self, image, mime_type):
            return DominantColors()

    asset, content = AssetLoader().load_image(str(png_path))
    [document] = await WebsiteScreenshotAnalyzer(ocr=fake_ocr, vision=BareVisionProvider()).analyze(
        asset, content
    )

    assert document.metadata["hero_present"] is False
    assert document.metadata["navigation_present"] is False
    assert document.metadata["cta_present"] is False
    assert document.metadata["marketing_sections"] == ["body"]
