import pytest

import app.ingestion.vision.claude_vision_provider as claude_vision_module
from app.ingestion.exceptions import AnalysisError
from app.ingestion.vision.base import ImageDescription, VisionProvider
from app.ingestion.vision.claude_vision_provider import ClaudeVisionProvider


class _FakeAssistantMessage:
    def __init__(self, content):
        self.content = content


class _FakeTextBlock:
    def __init__(self, text: str) -> None:
        self.text = text


def _install_fake_query(monkeypatch, response_text: str, captured: dict):
    """Patches the module's `query`/`AssistantMessage`/`TextBlock` so
    ClaudeVisionProvider's isinstance checks match our fakes, and records the
    streamed prompt dict for inspection - no real CLI/network call."""

    def fake_query(*, prompt, options):
        async def generator():
            async for message in prompt:
                captured["message"] = message
            yield _FakeAssistantMessage(content=[_FakeTextBlock(response_text)])

        return generator()

    monkeypatch.setattr(claude_vision_module, "query", fake_query)
    monkeypatch.setattr(claude_vision_module, "AssistantMessage", _FakeAssistantMessage)
    monkeypatch.setattr(claude_vision_module, "TextBlock", _FakeTextBlock)


def test_vision_provider_is_abstract():
    with pytest.raises(TypeError):
        VisionProvider()  # type: ignore[abstract]


@pytest.mark.asyncio
async def test_fake_vision_provider_implements_all_operations(fake_vision, png_bytes):
    description = await fake_vision.analyze_image(png_bytes, "image/png")
    text = await fake_vision.extract_text(png_bytes, "image/png")
    layout = await fake_vision.describe_layout(png_bytes, "image/png")
    objects = await fake_vision.identify_objects(png_bytes, "image/png")
    branding = await fake_vision.identify_branding(png_bytes, "image/png")
    colors = await fake_vision.identify_colors(png_bytes, "image/png")

    assert isinstance(description, ImageDescription)
    assert text.text == "Buy Now"
    assert "hero" in layout.regions
    assert "bottle" in objects.objects
    assert "Acme" in branding.logos
    assert colors.colors


@pytest.mark.asyncio
async def test_claude_vision_provider_streams_image_content_block(monkeypatch, png_bytes):
    captured: dict = {}
    _install_fake_query(monkeypatch, '{"description": "a photo", "confidence": 0.75}', captured)

    provider = ClaudeVisionProvider(model="fake-model")
    result = await provider.analyze_image(png_bytes, "image/png")

    assert result.description == "a photo"
    assert result.confidence == 0.75

    message = captured["message"]
    assert message["type"] == "user"
    content_blocks = message["message"]["content"]
    assert content_blocks[0]["type"] == "text"
    assert content_blocks[1]["type"] == "image"
    assert content_blocks[1]["source"]["type"] == "base64"
    assert content_blocks[1]["source"]["media_type"] == "image/png"


@pytest.mark.asyncio
async def test_claude_vision_provider_wraps_invalid_json_as_analysis_error(monkeypatch, png_bytes):
    _install_fake_query(monkeypatch, "not valid json", {})

    provider = ClaudeVisionProvider(model="fake-model")
    with pytest.raises(AnalysisError):
        await provider.analyze_image(png_bytes, "image/png")


@pytest.mark.asyncio
async def test_claude_vision_provider_wraps_transport_failure_as_analysis_error(monkeypatch, png_bytes):
    def failing_query(*, prompt, options):
        raise RuntimeError("CLI not available")

    monkeypatch.setattr(claude_vision_module, "query", failing_query)

    provider = ClaudeVisionProvider(model="fake-model")
    with pytest.raises(AnalysisError):
        await provider.extract_text(png_bytes, "image/png")
