from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from app.ai.base import AIProvider, AIRequest, AIResponse, AIUsage


class FakeAIProvider(AIProvider):
    """Deterministic AIProvider for tests - no real network/CLI calls."""

    def __init__(self, reply: str = "fake reply") -> None:
        self.reply = reply
        self.calls: list[AIRequest] = []

    async def generate(self, request: AIRequest) -> AIResponse:
        self.calls.append(request)
        return AIResponse(
            content=self.reply,
            model=request.model or "fake-model",
            usage=AIUsage(input_tokens=10, output_tokens=5),
        )

    async def stream(self, request: AIRequest) -> AsyncIterator[str]:
        for chunk in self.reply.split():
            yield chunk

    def count_tokens(self, text: str) -> int:
        return len(text.split())


class ExplodingProvider(AIProvider):
    """A vendor SDK failing the way they usually do: an exception that
    stringifies to nothing useful."""

    def __init__(self, error: Exception | None = None) -> None:
        self.error = error or RuntimeError()

    async def generate(self, request: AIRequest) -> AIResponse:
        raise self.error

    async def stream(self, request: AIRequest) -> AsyncIterator[str]:
        raise self.error
        yield ""  # pragma: no cover - unreachable, satisfies the async generator

    def count_tokens(self, text: str) -> int:
        return 0


@pytest.fixture
def prompts_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "prompts"
    directory.mkdir()
    (directory / "dummy.md").write_text(
        "You are {{ agent_name }} (v{{ version }}).\nSay hello to: {{ message }}\n",
        encoding="utf-8",
    )
    return directory


@pytest.fixture
def fake_provider() -> FakeAIProvider:
    return FakeAIProvider()
