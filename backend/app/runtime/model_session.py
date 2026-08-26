import asyncio
import json
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel

from app.ai.base import AIMessage, AIProvider, AIRequest, AIResponse
from app.ai.model_router import ModelRouter, ModelTier
from app.ai.models import usage_cost_usd
from app.runtime.events import (
    EventBus,
    ModelCallFinished,
    ModelCallRetried,
    ModelCallStarted,
)
from app.runtime.exceptions import OutputValidationError, ProviderError
from app.runtime.json_parsing import JsonOutputError, parse_model_json
from app.runtime.prompt_engine import PromptEngine

logger = logging.getLogger("marketingos.runtime")

#: A structured answer that came back malformed gets its own errors handed
#: back once. Past that the call fails: a model that has stopped following a
#: schema does not usually start again on the third ask, and the phase above
#: has cheaper recovery than a loop here.
_STRUCTURED_ATTEMPTS = 2

#: How many times one call may be *sent*, when the failure is transport rather
#: than content: the CLI refusing to spawn, a dropped socket, a subprocess
#: that died before it answered.
#:
#: Distinct from `_STRUCTURED_ATTEMPTS`, which re-asks a model that answered
#: badly. This re-asks a model that never answered at all, and it is the
#: cheaper of the two by a wide margin - a call that failed in transport
#: consumed no tokens, so a retry costs latency and nothing else.
#:
#: It is also the difference between a blip and a lost campaign. A balanced
#: run makes tens of calls, each one a subprocess spawn; at any per-call
#: failure rate p, the chance a whole run survives is (1-p)^n, and without a
#: retry there is nothing between one unlucky spawn and thirteen minutes of
#: billed work thrown away.
_PROVIDER_ATTEMPTS = 3

#: Seconds to wait before the *second* resend, and each one after it. The
#: first resend is immediate on purpose: the failures this exists for - a
#: subprocess that lost a spawn race, a pipe the peer closed - are already
#: over by the time they are reported, and a second spent waiting for them to
#: clear is a second spent against a deadline the pipeline is holding.
#:
#: A provider that is genuinely down fails the immediate retry too, and only
#: then is anything waited on.
_RETRY_BACKOFF_SECONDS = 1.0


def _schema_text(schema: type[BaseModel]) -> str:
    """The schema as the model is shown it: compact, and without the `title`
    keys Pydantic generates.

    Pretty-printing a JSON schema spends about a third of its characters on
    indentation, and every `title` is a restatement of the field name beside
    it ("Single Idea" above `single_idea`) that tells a model nothing its own
    key did not. The field names and descriptions - which do carry meaning -
    are untouched. Across a run this is a few thousand tokens for no change in
    what was communicated.
    """
    return json.dumps(_without_titles(schema.model_json_schema()), separators=(",", ":"))


def _without_titles(node: Any) -> Any:
    if isinstance(node, dict):
        return {
            key: _without_titles(value) for key, value in node.items() if key != "title"
        }
    if isinstance(node, list):
        return [_without_titles(item) for item in node]
    return node


@dataclass(frozen=True)
class RoleCall:
    """One model round-trip, as the run's ledger records it."""

    role: str
    model: str
    tier: ModelTier
    input_tokens: int
    output_tokens: int
    duration_ms: float
    #: Input priced as a cache write and as a cache read. Separate fields
    #: rather than folded into `input_tokens` because they are the difference
    #: between an honest and a fictional budget - see AIUsage.
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0
    #: What this call cost, provider-reported where possible.
    cost_usd: float = 0.0

    @property
    def billable_input_tokens(self) -> int:
        return (
            self.input_tokens + self.cache_creation_input_tokens + self.cache_read_input_tokens
        )


@dataclass
class Usage:
    """Running spend for one campaign run, across every role."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0
    cost_usd: float = 0.0
    calls: list[RoleCall] = field(default_factory=list)

    @property
    def billable_input_tokens(self) -> int:
        return (
            self.input_tokens + self.cache_creation_input_tokens + self.cache_read_input_tokens
        )

    @property
    def total_tokens(self) -> int:
        """Every token this run consumed, cached input included.

        Cached input is the majority of what a campaign spends and it used to
        be invisible here, so `ExecutionPolicy.max_total_tokens` was comparing
        a real budget against a number several times too small and never
        fired. A budget that cannot be exceeded is not a budget.
        """
        return self.billable_input_tokens + self.output_tokens

    def record(self, call: RoleCall) -> None:
        self.calls.append(call)
        self.input_tokens += call.input_tokens
        self.output_tokens += call.output_tokens
        self.cache_creation_input_tokens += call.cache_creation_input_tokens
        self.cache_read_input_tokens += call.cache_read_input_tokens
        self.cost_usd += call.cost_usd

    def since(self, marker: int) -> "Usage":
        """Spend recorded after `marker` calls - how a phase reports what it
        cost without every role having to count for itself."""
        recent = self.calls[marker:]
        return Usage(
            input_tokens=sum(call.input_tokens for call in recent),
            output_tokens=sum(call.output_tokens for call in recent),
            cache_creation_input_tokens=sum(
                call.cache_creation_input_tokens for call in recent
            ),
            cache_read_input_tokens=sum(call.cache_read_input_tokens for call in recent),
            cost_usd=sum(call.cost_usd for call in recent),
            calls=list(recent),
        )


class ModelSession:
    """The single way anything in MarketingOS talks to a model.

    This is what is left of the old generic agent runtime, and the deletions
    are the point. There is no BaseAgent, no injected AgentContext and no
    shared memory blackboard, because the reasoning roles are concrete classes
    that are handed exactly what they need by the pipeline - a role that can
    receive arbitrary context through a bag is a role whose inputs nobody can
    reason about.

    What the runtime did earn stays here: prompts are rendered from disk and
    never hardcoded, vendor exceptions become typed ProviderErrors so one blip
    fails a call rather than a campaign, tokens are counted without any role
    doing bookkeeping, and every call announces itself on the event bus - which
    is what fills the minutes a campaign spends inside a single generate().
    """

    def __init__(
        self,
        provider: AIProvider,
        prompt_engine: PromptEngine,
        events: EventBus,
        model_router: ModelRouter,
        execution_id: str,
        on_call: Callable[[RoleCall], None] | None = None,
    ) -> None:
        self._provider = provider
        self._prompts = prompt_engine
        self._events = events
        self._router = model_router
        self._execution_id = execution_id
        self._on_call = on_call
        self.usage = Usage()

    def render(self, template: str, variables: dict[str, Any]) -> str:
        """Render a prompt template without calling anything - for the one
        caller that builds a system prompt itself (the blind reader, whose
        whole prompt is the email it must react to)."""
        return self._prompts.render(template, variables)

    async def text(
        self,
        *,
        role: str,
        tier: ModelTier,
        task: str,
        template: str | None = None,
        variables: dict[str, Any] | None = None,
        system_prompt: str | None = None,
    ) -> str:
        """One turn: a system prompt (rendered from `template`, or passed in
        already rendered) plus the task message, answered as free text."""
        system = (
            system_prompt
            if system_prompt is not None
            else self._prompts.render(template or role, variables or {})
        )
        model = self._router.resolve(role, tier)
        return await self._generate(role, tier, model, system, task, template or "")

    async def structured[T: BaseModel](
        self,
        *,
        role: str,
        tier: ModelTier,
        task: str,
        schema: type[T],
        template: str | None = None,
        variables: dict[str, Any] | None = None,
        system_prompt: str | None = None,
    ) -> T:
        """One turn answered as a single JSON object matching `schema`.

        The schema is appended to the task rather than described in the prompt
        template, so a role's output model can change without anyone editing
        markdown - and a malformed answer is handed its own validation errors
        for one correction turn.
        """
        system = (
            system_prompt
            if system_prompt is not None
            else self._prompts.render(template or role, variables or {})
        )
        model = self._router.resolve(role, tier)
        message = (
            f"{task}\n\nRespond with ONLY a single JSON object matching this schema "
            f"(no prose, no code fences):\n{_schema_text(schema)}"
        )

        last_error: JsonOutputError | None = None
        for _ in range(_STRUCTURED_ATTEMPTS):
            response = await self._generate(role, tier, model, system, message, template or "")
            try:
                return parse_model_json(response, schema)
            except JsonOutputError as exc:
                last_error = exc
                message = (
                    f"Your previous response was not valid {schema.__name__} JSON ({exc}).\n\n"
                    f"--- what you sent ---\n{response}\n--- end ---\n\n"
                    "Respond again with ONLY the JSON object, nothing before or after it."
                )

        raise OutputValidationError(
            f"Role '{role}' did not return valid {schema.__name__} JSON after "
            f"{_STRUCTURED_ATTEMPTS} attempts: {last_error}",
            role=role,
            raw_response=last_error.raw_text if last_error else None,
        )

    # ------------------------------------------------------------- internals

    async def _send(self, request: AIRequest, role: str, model: str) -> AIResponse:
        """Hand one request to the provider, resending it if it never landed.

        The retry is here rather than in the provider because this is the only
        place that knows the call is a role turn in a run somebody is paying
        for. Everything above it - the craft loop, the pipeline - is written to
        survive a *result* it does not like; none of it is written to survive
        the transport, and before this a single failed spawn escaped as a
        `ProviderError` through a pipeline that catches `CampaignError`, taking
        every finished email in the run with it.

        Only the transport is retried. A model that answered something
        unusable is `structured`'s problem and has its own, differently-shaped
        correction turn; resending that same prompt here would buy a second
        copy of the same bad answer at full price.
        """
        last: Exception | None = None
        for attempt in range(1, _PROVIDER_ATTEMPTS + 1):
            try:
                return await self._provider.generate(request)
            except Exception as exc:  # noqa: BLE001 - re-raised as ProviderError below
                last = exc
                if attempt == _PROVIDER_ATTEMPTS:
                    break
                detail = str(exc) or type(exc).__name__
                logger.info(
                    "model_session: %s call %d/%d failed in transport (%s) - resending",
                    role,
                    attempt,
                    _PROVIDER_ATTEMPTS,
                    detail,
                )
                self._events.publish(
                    ModelCallRetried(
                        agent_id=role,
                        execution_id=self._execution_id,
                        model=model,
                        attempt=attempt,
                        error=detail,
                    )
                )
                if attempt > 1:
                    await asyncio.sleep(_RETRY_BACKOFF_SECONDS * (attempt - 1))

        # Vendor exceptions often stringify to nothing, so keep the type
        # name: "" is not a debuggable failure message.
        detail = str(last) or type(last).__name__
        raise ProviderError(
            f"{type(self._provider).__name__} call failed after {_PROVIDER_ATTEMPTS} "
            f"attempt(s): {detail}",
            provider=type(self._provider).__name__,
            role=role,
            cause=type(last).__name__,
            attempts=_PROVIDER_ATTEMPTS,
        ) from last

    async def _generate(
        self, role: str, tier: ModelTier, model: str, system: str, task: str, template: str = ""
    ) -> str:
        request = AIRequest(
            system_prompt=system,
            messages=[AIMessage(role="user", content=task)],
            model=model,
            role=role,
            template=template,
        )
        self._events.publish(
            ModelCallStarted(
                agent_id=role,
                execution_id=self._execution_id,
                model=model,
                prompt_chars=len(system) + len(task),
            )
        )
        started = time.perf_counter()
        response = await self._send(request, role, model)
        duration_ms = (time.perf_counter() - started) * 1000
        resolved_model = response.model or model
        call = RoleCall(
            role=role,
            model=resolved_model,
            tier=tier,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            duration_ms=duration_ms,
            cache_creation_input_tokens=response.usage.cache_creation_input_tokens,
            cache_read_input_tokens=response.usage.cache_read_input_tokens,
            cost_usd=usage_cost_usd(resolved_model, response.usage),
        )
        self.usage.record(call)
        if self._on_call is not None:
            self._on_call(call)
        self._events.publish(
            ModelCallFinished(
                agent_id=role,
                execution_id=self._execution_id,
                model=call.model,
                input_tokens=call.input_tokens,
                output_tokens=call.output_tokens,
                duration_ms=duration_ms,
                response_chars=len(response.content),
                cache_creation_input_tokens=call.cache_creation_input_tokens,
                cache_read_input_tokens=call.cache_read_input_tokens,
                cost_usd=call.cost_usd,
            )
        )
        return response.content
