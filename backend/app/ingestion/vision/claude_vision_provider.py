import base64
import os
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any
from uuid import uuid4

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, TextBlock, query
from pydantic import BaseModel, ValidationError

from app.ingestion.exceptions import AnalysisError
from app.ingestion.vision.base import (
    BrandingInfo,
    DetectedObjects,
    DominantColors,
    ExtractedText,
    ImageDescription,
    LayoutDescription,
    VisionProvider,
)
from app.ingestion.vision.prompts import (
    ANALYZE_IMAGE_PROMPT,
    DESCRIBE_LAYOUT_PROMPT,
    EXTRACT_TEXT_PROMPT,
    IDENTIFY_BRANDING_PROMPT,
    IDENTIFY_COLORS_PROMPT,
    IDENTIFY_OBJECTS_PROMPT,
)


def _cli_path() -> str | None:
    explicit = os.environ.get("CLAUDE_CLI_PATH")
    if explicit and Path(explicit).exists():
        return explicit
    appdata = os.environ.get("APPDATA")
    if appdata:
        candidate = (
            Path(appdata) / "npm" / "node_modules" / "@anthropic-ai" / "claude-code" / "bin" / "claude.exe"
        )
        if candidate.exists():
            return str(candidate)
    return None


def _clean_env() -> dict[str, str]:
    return {key: value for key, value in os.environ.items() if key != "ANTHROPIC_API_KEY"}


class ClaudeVisionProvider(VisionProvider):
    """VisionProvider backed by the Claude Code CLI via the Claude Agent SDK,
    using its streaming input mode to send an image content block alongside
    each operation's instruction text. Requires the `claude` CLI to be
    installed and authenticated, same as app.ai.claude_provider.ClaudeProvider."""

    def __init__(self, model: str) -> None:
        self._model = model

    async def analyze_image(self, image: bytes, mime_type: str) -> ImageDescription:
        return await self._query(image, mime_type, ANALYZE_IMAGE_PROMPT, ImageDescription)

    async def extract_text(self, image: bytes, mime_type: str) -> ExtractedText:
        return await self._query(image, mime_type, EXTRACT_TEXT_PROMPT, ExtractedText)

    async def describe_layout(self, image: bytes, mime_type: str) -> LayoutDescription:
        return await self._query(image, mime_type, DESCRIBE_LAYOUT_PROMPT, LayoutDescription)

    async def identify_objects(self, image: bytes, mime_type: str) -> DetectedObjects:
        return await self._query(image, mime_type, IDENTIFY_OBJECTS_PROMPT, DetectedObjects)

    async def identify_branding(self, image: bytes, mime_type: str) -> BrandingInfo:
        return await self._query(image, mime_type, IDENTIFY_BRANDING_PROMPT, BrandingInfo)

    async def identify_colors(self, image: bytes, mime_type: str) -> DominantColors:
        return await self._query(image, mime_type, IDENTIFY_COLORS_PROMPT, DominantColors)

    async def _query[T: BaseModel](
        self, image: bytes, mime_type: str, instruction: str, output_model: type[T]
    ) -> T:
        options = ClaudeAgentOptions(
            model=self._model,
            max_turns=1,
            allowed_tools=[],
            permission_mode="default",
            cli_path=_cli_path(),
            env=_clean_env(),
            setting_sources=[],
        )

        final_text = ""
        try:
            async for message in query(prompt=self._stream(image, mime_type, instruction), options=options):
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock) and block.text.strip():
                            final_text = block.text
        except Exception as exc:
            raise AnalysisError(f"Claude vision call failed: {exc}") from exc

        try:
            return output_model.model_validate_json(final_text)
        except ValidationError as exc:
            raise AnalysisError(
                f"Claude vision response didn't match {output_model.__name__}: {exc}",
                raw_response=final_text,
            ) from exc

    @staticmethod
    async def _stream(image: bytes, mime_type: str, instruction: str) -> AsyncIterator[dict[str, Any]]:
        yield {
            "type": "user",
            "message": {
                "role": "user",
                "content": [
                    {"type": "text", "text": instruction},
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": mime_type,
                            "data": base64.b64encode(image).decode("ascii"),
                        },
                    },
                ],
            },
            "parent_tool_use_id": None,
            "session_id": f"vision-{uuid4().hex}",
        }
