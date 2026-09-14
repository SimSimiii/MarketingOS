from dataclasses import asdict

from app.ai.claude_provider import ClaudeProvider
from app.ai.model_router import ModelRouter
from app.core.config import PROMPTS_DIR
from app.ingestion.exceptions import AnalysisError
from app.ingestion.vision.base import (
    BrandingInfo,
    DetectedObjects,
    DominantColors,
    ExtractedText,
    ImageDescription,
    LayoutDescription,
    VisionProvider,
    VisualExtraction,
)
from app.ingestion.vision.prompts import (
    ANALYZE_IMAGE_PROMPT,
    DESCRIBE_LAYOUT_PROMPT,
    EXTRACT_TEXT_PROMPT,
    IDENTIFY_BRANDING_PROMPT,
    IDENTIFY_COLORS_PROMPT,
    IDENTIFY_OBJECTS_PROMPT,
)
from app.runtime.events import EventBus
from app.runtime.exceptions import ProviderError
from app.runtime.model_session import ModelSession
from app.runtime.prompt_engine import get_prompt_engine


class ClaudeVisionProvider(VisionProvider):
    def __init__(self, model: str) -> None:
        self._session = ModelSession(
            ClaudeProvider(model), get_prompt_engine(PROMPTS_DIR), EventBus(),
            ModelRouter(overrides={"image_reader": model}), "image-ingestion",
        )

    @property
    def usage(self):
        return asdict(self._session.usage)

    async def read_image(self, image, mime_type):
        instruction = self._session.render("image_extraction", {})
        return await self._query(image, mime_type, instruction, VisualExtraction)

    async def analyze_image(self, image, mime_type):
        return await self._query(image, mime_type, ANALYZE_IMAGE_PROMPT, ImageDescription)

    async def extract_text(self, image, mime_type):
        return await self._query(image, mime_type, EXTRACT_TEXT_PROMPT, ExtractedText)

    async def describe_layout(self, image, mime_type):
        return await self._query(image, mime_type, DESCRIBE_LAYOUT_PROMPT, LayoutDescription)

    async def identify_objects(self, image, mime_type):
        return await self._query(image, mime_type, IDENTIFY_OBJECTS_PROMPT, DetectedObjects)

    async def identify_branding(self, image, mime_type):
        return await self._query(image, mime_type, IDENTIFY_BRANDING_PROMPT, BrandingInfo)

    async def identify_colors(self, image, mime_type):
        return await self._query(image, mime_type, IDENTIFY_COLORS_PROMPT, DominantColors)

    async def _query(self, image, mime_type, instruction, output_model):
        try:
            return await self._session.structured_image(
                role="image_reader", image=image, mime_type=mime_type,
                schema=output_model, instruction=instruction,
            )
        except (ProviderError, ValueError) as exc:
            raise AnalysisError(f"Image extraction failed: {exc}") from exc
