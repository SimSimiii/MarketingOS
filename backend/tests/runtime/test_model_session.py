"""The single choke point every model call in the system goes through."""

import json
from pathlib import Path

import pytest
from pydantic import BaseModel

from app.ai.model_router import ModelRouter, ModelTier
from app.runtime.events import (
    EventBus,
    ModelCallFinished,
    ModelCallRetried,
    ModelCallStarted,
)
from app.runtime.exceptions import OutputValidationError, ProviderError
from app.runtime.model_session import ModelSession, RoleCall
from app.runtime.prompt_engine import PromptEngine
from tests.runtime.conftest import ExplodingProvider, FakeAIProvider, FlakyProvider


class Answer(BaseModel):
    verdict: str
    score: int = 0


def session(provider, prompts_dir: Path, events: EventBus | None = None, **kwargs) -> ModelSession:
    return ModelSession(
        provider=provider,
        prompt_engine=PromptEngine(prompts_dir),
        events=events or EventBus(),
        model_router=ModelRouter(kwargs.pop("overrides", None)),
        execution_id="exec-1",
        **kwargs,
    )


@pytest.mark.asyncio
async def test_a_call_renders_its_prompt_from_disk(fake_provider: FakeAIProvider, prompts_dir: Path):
    """Prompts are never hardcoded in Python - that survived the redesign."""
    await session(fake_provider, prompts_dir).text(
        role="dummy",
        tier=ModelTier.FAST,
        template="dummy",
        variables={"agent_name": "Dummy", "version": "1.0.0", "message": "world"},
        task="Go.",
    )
    system = fake_provider.calls[0].system_prompt or ""
    assert "You are Dummy (v1.0.0)." in system
    assert "Say hello to: world" in system


@pytest.mark.asyncio
async def test_the_asking_role_is_carried_on_the_request(
    fake_provider: FakeAIProvider, prompts_dir: Path
):
    """Attribution without pattern-matching on prompt text - what per-role
    routing, caching and any honest test double all need."""
    await session(fake_provider, prompts_dir).text(
        role="email_writer", tier=ModelTier.DEEP, system_prompt="be brief", task="Go."
    )
    assert fake_provider.calls[0].role == "email_writer"


@pytest.mark.asyncio
async def test_the_tier_decides_the_model_and_an_override_beats_it(
    fake_provider: FakeAIProvider, prompts_dir: Path
):
    await session(fake_provider, prompts_dir).text(
        role="email_writer", tier=ModelTier.DEEP, system_prompt="x", task="Go."
    )
    assert fake_provider.calls[0].model == "opus"

    await session(fake_provider, prompts_dir, overrides={"*": "haiku"}).text(
        role="email_writer", tier=ModelTier.DEEP, system_prompt="x", task="Go."
    )
    assert fake_provider.calls[1].model == "haiku"


@pytest.mark.asyncio
async def test_structured_output_is_parsed_into_the_promised_model(prompts_dir: Path):
    provider = FakeAIProvider(json.dumps({"verdict": "ship", "score": 8}))
    answer = await session(provider, prompts_dir).structured(
        role="critic", tier=ModelTier.DEEP, system_prompt="x", task="Judge.", schema=Answer
    )
    assert answer.verdict == "ship"
    # The schema rides on the task, so a role's output model can change without
    # anyone editing markdown.
    assert "verdict" in provider.calls[0].messages[0].content


@pytest.mark.asyncio
async def test_a_malformed_answer_is_handed_its_own_errors_once(prompts_dir: Path):
    class Flaky(FakeAIProvider):
        async def generate(self, request):
            self.calls.append(request)
            reply = "here you go!" if len(self.calls) == 1 else json.dumps({"verdict": "ship"})
            return await FakeAIProvider(reply).generate(request)

    provider = Flaky()
    answer = await session(provider, prompts_dir).structured(
        role="critic", tier=ModelTier.DEEP, system_prompt="x", task="Judge.", schema=Answer
    )
    assert answer.verdict == "ship"
    assert "was not valid Answer JSON" in provider.calls[1].messages[0].content


@pytest.mark.asyncio
async def test_a_role_that_never_returns_valid_json_fails_typed(prompts_dir: Path):
    provider = FakeAIProvider("not json, sorry")
    with pytest.raises(OutputValidationError) as excinfo:
        await session(provider, prompts_dir).structured(
            role="critic", tier=ModelTier.DEEP, system_prompt="x", task="Judge.", schema=Answer
        )
    assert excinfo.value.details["role"] == "critic"


@pytest.mark.asyncio
async def test_a_vendor_exception_becomes_a_typed_provider_error(prompts_dir: Path):
    """A vendor exception that stringifies to nothing must not escape as
    itself - one blip would take down a campaign nobody catches it for."""
    with pytest.raises(ProviderError) as excinfo:
        await session(ExplodingProvider(), prompts_dir).text(
            role="email_writer", tier=ModelTier.DEEP, system_prompt="x", task="Go."
        )
    assert "RuntimeError" in str(excinfo.value)
    assert excinfo.value.details["role"] == "email_writer"


@pytest.mark.asyncio
async def test_tokens_are_counted_without_any_role_doing_bookkeeping(
    fake_provider: FakeAIProvider, prompts_dir: Path
):
    recorded: list[RoleCall] = []
    model_session = session(fake_provider, prompts_dir, on_call=recorded.append)

    await model_session.text(role="a", tier=ModelTier.FAST, system_prompt="x", task="Go.")
    await model_session.text(role="b", tier=ModelTier.DEEP, system_prompt="x", task="Go.")

    assert model_session.usage.total_tokens == 30
    assert [call.role for call in recorded] == ["a", "b"]


@pytest.mark.asyncio
async def test_every_call_announces_itself_so_a_run_never_looks_hung(
    fake_provider: FakeAIProvider, prompts_dir: Path
):
    events = EventBus()
    seen: list[str] = []
    events.subscribe(ModelCallStarted, lambda event: seen.append(f"start:{event.agent_id}"))
    events.subscribe(ModelCallFinished, lambda event: seen.append(f"end:{event.agent_id}"))

    await session(fake_provider, prompts_dir, events=events).text(
        role="blind_reader", tier=ModelTier.BALANCED, system_prompt="x", task="Go."
    )
    assert seen == ["start:blind_reader", "end:blind_reader"]


# ------------------------------------------------------- surviving the wire


@pytest.mark.asyncio
async def test_a_call_that_never_landed_is_sent_again(prompts_dir: Path):
    """The failure this exists for, and the reason it is worth a retry at all.

    Every call is a CLI subprocess spawn, and a spawn that loses a race fails
    before a single token is consumed - so resending costs latency and nothing
    else. Without this, one unlucky spawn out of the tens a campaign makes
    ended the whole run.
    """
    provider = FlakyProvider(failures=1)
    answer = await session(provider, prompts_dir).text(
        role="email_writer", tier=ModelTier.DEEP, system_prompt="x", task="Go."
    )

    assert answer == "answered on the retry"
    assert provider.attempts == 2


@pytest.mark.asyncio
async def test_a_resend_is_announced_rather_than_hidden(prompts_dir: Path):
    """A retry nobody can see is a provider failing half its calls that looks
    identical to one that is merely slow - the ledger shows nothing, because a
    call that failed consumed nothing."""
    events = EventBus()
    seen: list[ModelCallRetried] = []
    events.subscribe(ModelCallRetried, seen.append)

    await session(FlakyProvider(failures=1), prompts_dir, events=events).text(
        role="blind_reader", tier=ModelTier.BALANCED, system_prompt="x", task="Go."
    )

    assert [(event.agent_id, event.attempt) for event in seen] == [("blind_reader", 1)]
    assert "the CLI did not start" in seen[0].error


@pytest.mark.asyncio
async def test_a_provider_that_never_answers_still_fails_the_call(prompts_dir: Path):
    """Retrying is a floor, not a promise. A provider that is genuinely down
    has to surface as a typed ProviderError the phase above can account for -
    and the count is on the error, so a log line says how hard we tried."""
    provider = FlakyProvider(failures=99)
    with pytest.raises(ProviderError) as excinfo:
        await session(provider, prompts_dir).text(
            role="strategist", tier=ModelTier.DEEP, system_prompt="x", task="Go."
        )

    assert provider.attempts == excinfo.value.details["attempts"]
    assert provider.attempts > 1
