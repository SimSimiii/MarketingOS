import inspect

from app.ingestion.analyzers.image_analyzer import ImageAnalyzer
from app.ingestion.analyzers.website_screenshot_analyzer import WebsiteScreenshotAnalyzer
from app.ingestion.multimodal_pipeline import MultimodalIngestionPipeline
from app.ingestion.ocr.base import OCRProvider
from app.ingestion.vision.base import VisionProvider


def _required_params(cls) -> set[str]:
    signature = inspect.signature(cls.__init__)
    return {
        name
        for name, param in signature.parameters.items()
        if name != "self" and param.default is inspect.Parameter.empty
    }


def test_image_analyzer_requires_injected_ocr_and_vision():
    required = _required_params(ImageAnalyzer)
    assert "ocr" in required
    assert "vision" in required


def test_website_screenshot_analyzer_requires_injected_ocr_and_vision():
    required = _required_params(WebsiteScreenshotAnalyzer)
    assert "ocr" in required
    assert "vision" in required


def test_multimodal_pipeline_requires_all_dependencies_injected():
    required = _required_params(MultimodalIngestionPipeline)
    assert required == {"asset_loader", "analyzers", "store", "asset_store"}


def test_image_analyzer_never_instantiates_its_own_providers(fake_ocr, fake_vision):
    analyzer = ImageAnalyzer(ocr=fake_ocr, vision=fake_vision)
    # The exact instances passed in must be the ones used, not fresh defaults.
    assert analyzer._ocr is fake_ocr
    assert analyzer._vision is fake_vision


def test_ocr_and_vision_are_independent_abstractions():
    # Neither ABC references or depends on the other's type.
    import app.ingestion.ocr.base as ocr_base
    import app.ingestion.vision.base as vision_base

    assert VisionProvider not in vars(ocr_base).values()
    assert OCRProvider not in vars(vision_base).values()
