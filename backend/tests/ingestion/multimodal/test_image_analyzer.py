import pytest

from app.ingestion.analyzers.image_analyzer import ImageAnalyzer
from app.ingestion.assets.loader import AssetLoader
from app.ingestion.documents import SourceType


@pytest.mark.asyncio
async def test_analyze_returns_one_knowledge_document(png_path, fake_ocr, fake_vision):
    asset, content = AssetLoader().load_image(str(png_path))
    documents = await ImageAnalyzer(ocr=fake_ocr, vision=fake_vision).analyze(asset, content)

    assert len(documents) == 1


@pytest.mark.asyncio
async def test_document_is_linked_to_its_asset(png_path, fake_ocr, fake_vision):
    asset, content = AssetLoader().load_image(str(png_path))
    [document] = await ImageAnalyzer(ocr=fake_ocr, vision=fake_vision).analyze(asset, content)

    assert document.asset_id == asset.id
    assert document.source == SourceType.IMAGE


@pytest.mark.asyncio
async def test_metadata_has_the_documented_shape(png_path, fake_ocr, fake_vision):
    asset, content = AssetLoader().load_image(str(png_path))
    [document] = await ImageAnalyzer(ocr=fake_ocr, vision=fake_vision).analyze(asset, content)

    for field in (
        "asset_type",
        "vision_provider",
        "ocr_provider",
        "detected_language",
        "detected_objects",
        "detected_logos",
        "dominant_colors",
        "layout",
        "confidence",
    ):
        assert field in document.metadata, field

    assert document.metadata["vision_provider"] == "FakeVisionProvider"
    assert document.metadata["ocr_provider"] == "FakeOCRProvider"
    assert document.metadata["detected_objects"] == ["bottle", "label"]
    assert document.metadata["detected_logos"] == ["Acme"]
    assert document.metadata["dominant_colors"] == ["#ffffff", "#ff0000"]


@pytest.mark.asyncio
async def test_uses_both_ocr_and_vision_independently(png_path, fake_ocr, fake_vision):
    asset, content = AssetLoader().load_image(str(png_path))
    await ImageAnalyzer(ocr=fake_ocr, vision=fake_vision).analyze(asset, content)

    assert len(fake_ocr.calls) == 1  # OCR called exactly once, independently of vision
    assert "analyze_image" in fake_vision.calls
    assert "describe_layout" in fake_vision.calls
    assert "identify_objects" in fake_vision.calls
    assert "identify_branding" in fake_vision.calls
    assert "identify_colors" in fake_vision.calls


@pytest.mark.asyncio
async def test_content_is_factual_ocr_text_not_a_summary(png_path, fake_ocr, fake_vision):
    asset, content = AssetLoader().load_image(str(png_path))
    [document] = await ImageAnalyzer(ocr=fake_ocr, vision=fake_vision).analyze(asset, content)

    # The document's content is the raw OCR text - never a generated summary.
    assert document.content == fake_ocr.text
