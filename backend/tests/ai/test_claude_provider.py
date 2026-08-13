"""Regression tests for the event-loop bridge in ClaudeProvider.

The Claude Agent SDK drives the CLI as a subprocess. On Windows a
`SelectorEventLoop` cannot spawn subprocesses - it raises a message-less
`NotImplementedError` that the SDK reports as "Failed to start Claude Code: ".
Uvicorn hands its worker a selector loop whenever it spawns one (`--reload`,
`--workers`), which is precisely how the API gets run, so the provider must
not depend on the host loop.
"""

import asyncio
import sys

import pytest

from app.ai import claude_provider
from app.ai.base import AIMessage, AIRequest
from app.ai.claude_provider import ClaudeProvider, _needs_proactor_thread


class _FakeTextBlock:
    def __init__(self, text: str) -> None:
        self.text = text


class _FakeAssistantMessage:
    def __init__(self, text: str) -> None:
        self.content = [_FakeTextBlock(text)]


def _install_fake_query(monkeypatch, chunks: list[str], loops: list[object]) -> None:
    """Replace the SDK's `query` with a fake that records which event loop it
    ran on, so a test can prove the call was moved off the caller's loop."""

    async def fake_query(prompt: str, options):
        loops.append(asyncio.get_running_loop())
        for chunk in chunks:
            yield _FakeAssistantMessage(chunk)

    monkeypatch.setattr(claude_provider, "query", fake_query)
    monkeypatch.setattr(claude_provider, "AssistantMessage", _FakeAssistantMessage)
    monkeypatch.setattr(claude_provider, "TextBlock", _FakeTextBlock)


def _request() -> AIRequest:
    return AIRequest(
        system_prompt="You are terse.",
        messages=[AIMessage(role="user", content="Say OK")],
        model="test-model",
    )


@pytest.mark.asyncio
async def test_generate_runs_on_the_caller_loop_when_it_can_spawn_subprocesses(monkeypatch):
    loops: list[object] = []
    _install_fake_query(monkeypatch, ["OK"], loops)
    monkeypatch.setattr(claude_provider, "_needs_proactor_thread", lambda: False)

    response = await ClaudeProvider(default_model="test-model").generate(_request())

    assert response.content == "OK"
    assert loops == [asyncio.get_running_loop()]


@pytest.mark.asyncio
async def test_generate_moves_to_its_own_loop_when_the_host_loop_cannot(monkeypatch):
    loops: list[object] = []
    _install_fake_query(monkeypatch, ["OK"], loops)
    monkeypatch.setattr(claude_provider, "_needs_proactor_thread", lambda: True)

    response = await ClaudeProvider(default_model="test-model").generate(_request())

    assert response.content == "OK"
    # The SDK call happened on a private loop, not the one serving the request.
    assert loops and loops[0] is not asyncio.get_running_loop()


@pytest.mark.asyncio
async def test_generate_reuses_the_same_proactor_loop_across_calls(monkeypatch):
    """The actual bug this fixes: a fresh ProactorEventLoop (and OS thread)
    per call is what eventually produced CLINotFoundError partway through a
    run in production. Every call must land on the same persistent loop
    instead of a new one each time."""
    loops: list[object] = []
    _install_fake_query(monkeypatch, ["OK"], loops)
    monkeypatch.setattr(claude_provider, "_needs_proactor_thread", lambda: True)

    provider = ClaudeProvider(default_model="test-model")
    for _ in range(3):
        await provider.generate(_request())

    assert len(loops) == 3
    assert len({id(loop) for loop in loops}) == 1


@pytest.mark.asyncio
async def test_stream_is_bridged_back_to_the_caller_loop(monkeypatch):
    loops: list[object] = []
    _install_fake_query(monkeypatch, ["one ", "two ", "three"], loops)
    monkeypatch.setattr(claude_provider, "_needs_proactor_thread", lambda: True)

    chunks = [chunk async for chunk in ClaudeProvider(default_model="test-model").stream(_request())]

    assert chunks == ["one ", "two ", "three"]
    assert loops and loops[0] is not asyncio.get_running_loop()


@pytest.mark.asyncio
async def test_stream_failures_reach_the_caller(monkeypatch):
    async def exploding_query(prompt: str, options):
        raise RuntimeError("cli exploded")
        yield  # pragma: no cover - makes this an async generator

    monkeypatch.setattr(claude_provider, "query", exploding_query)
    monkeypatch.setattr(claude_provider, "_needs_proactor_thread", lambda: True)

    with pytest.raises(RuntimeError, match="cli exploded"):
        async for _ in ClaudeProvider(default_model="test-model").stream(_request()):
            pass


def _captured_call(monkeypatch) -> dict:
    """Record the options and prompt the SDK would actually be handed."""
    seen: dict = {}

    async def recording_query(prompt: str, options):
        seen["prompt"] = prompt
        seen["options"] = options
        yield _FakeAssistantMessage("OK")

    monkeypatch.setattr(claude_provider, "query", recording_query)
    monkeypatch.setattr(claude_provider, "AssistantMessage", _FakeAssistantMessage)
    monkeypatch.setattr(claude_provider, "TextBlock", _FakeTextBlock)
    monkeypatch.setattr(claude_provider, "_needs_proactor_thread", lambda: False)
    return seen


@pytest.mark.asyncio
async def test_a_normal_system_prompt_is_still_passed_as_a_system_prompt(monkeypatch):
    seen = _captured_call(monkeypatch)

    await ClaudeProvider(default_model="test-model").generate(_request())

    assert seen["options"].system_prompt == "You are terse."
    assert seen["prompt"] == "Say OK"


@pytest.mark.asyncio
async def test_an_oversized_system_prompt_travels_in_the_user_message(monkeypatch):
    """The bug this exists for: the SDK puts the system prompt on the CLI's
    command line, and Windows refuses to start a process whose command line
    exceeds 32,767 characters - reporting it as `CLINotFoundError`, which
    reads as a missing binary. Anything that large has to go over stdin
    instead, where there is no limit."""
    seen = _captured_call(monkeypatch)
    huge = "You are terse. " * 4000  # ~60k chars, well past the limit
    request = AIRequest(
        system_prompt=huge,
        messages=[AIMessage(role="user", content="Say OK")],
        model="test-model",
    )

    await ClaudeProvider(default_model="test-model").generate(request)

    # Nothing near the limit is left on the command line...
    assert seen["options"].system_prompt == claude_provider._OVERSIZED_SYSTEM_NOTICE
    assert len(seen["options"].system_prompt) < 1000
    # ...and the instructions still reach the model, ahead of the task.
    assert seen["prompt"].startswith(huge)
    assert seen["prompt"].endswith("Say OK")
    assert claude_provider._TASK_SEPARATOR in seen["prompt"]


@pytest.mark.asyncio
async def test_the_switch_happens_at_the_documented_threshold(monkeypatch):
    """A prompt right at the limit must not be folded; one past it must be."""
    limit = claude_provider._MAX_INLINE_SYSTEM_PROMPT_CHARS
    provider = ClaudeProvider(default_model="test-model")

    for size, folded in ((limit, False), (limit + 1, True)):
        seen = _captured_call(monkeypatch)
        await provider.generate(
            AIRequest(
                system_prompt="x" * size,
                messages=[AIMessage(role="user", content="Say OK")],
                model="test-model",
            )
        )
        was_folded = seen["options"].system_prompt == claude_provider._OVERSIZED_SYSTEM_NOTICE
        assert was_folded is folded, f"{size} chars"


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only loop constraint")
def test_selector_loop_is_detected_as_needing_a_proactor_thread():
    """The exact configuration uvicorn gives its worker under --reload."""
    results: list[bool] = []

    async def check() -> None:
        results.append(_needs_proactor_thread())

    for loop_type, expected in (
        (asyncio.SelectorEventLoop, True),
        (asyncio.ProactorEventLoop, False),
    ):
        loop = loop_type()
        try:
            loop.run_until_complete(check())
        finally:
            loop.close()
        assert results.pop() is expected, loop_type.__name__


def test_no_running_loop_needs_no_thread():
    assert _needs_proactor_thread() is False
