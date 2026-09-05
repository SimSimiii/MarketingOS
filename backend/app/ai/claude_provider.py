import asyncio
import os
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, ResultMessage, TextBlock, query

from app.ai._win_loop import (
    _needs_proactor_thread,
    _ProactorLoopThread,
    _run_in_proactor_loop,
)
from app.ai.base import (
    AIProvider,
    AIRequest,
    AIResponse,
    AIUsage,
    ProviderCallError,
    ResearchTool,
)

#: Marks the end of a bridged stream (see `_stream_via_proactor`).
_STREAM_DONE = object()

#: The CLI counts each assistant message as a turn, and a long answer (a full
#: email sequence, say) can arrive as more than one. With no tools enabled
#: there is nothing to loop on, so this is a runaway guard rather than a
#: budget - keep it well clear of normal generations.
_MAX_TURNS = 8

#: The same guard for a call that may search and read. Here it *is* a budget:
#: every turn is a search or a page fetch the operator pays for, and a research
#: role with an unbounded loop is the one way this system could spend real
#: money without a phase deciding to. Twenty is comfortably more than the
#: four-to-six round trips a competitor profile actually takes, and far short
#: of a runaway.
_MAX_RESEARCH_TURNS = 20

#: How a vendor-agnostic capability is spelled for this CLI.
_CLI_TOOL_NAMES: dict[ResearchTool, str] = {
    ResearchTool.WEB_SEARCH: "WebSearch",
    ResearchTool.WEB_FETCH: "WebFetch",
}

#: The SDK passes the system prompt to the CLI as a command-line argument
#: (`--system-prompt <text>`), and Windows caps an entire command line at
#: 32,767 characters. Past that, CreateProcess refuses to start the process at
#: all and the SDK reports the resulting OSError as
#: `CLINotFoundError: Claude Code not found at: ...` - which is a lie: the
#: binary is present and fine, the argument list is simply too long. It is a
#: hard, reproducible threshold, not a flake, and it is reached routinely -
#: the knowledge compiler's audience pass alone renders a ~42,000 character
#: prompt once a business has a few pages of material.
#:
#: 15,000 leaves generous headroom for the rest of the command line and for
#: the quote-escaping Windows applies when building it.
_MAX_INLINE_SYSTEM_PROMPT_CHARS = 15_000

#: What the model is told when its real instructions had to travel by stdin.
_OVERSIZED_SYSTEM_NOTICE = (
    "Your operating instructions for this task are at the start of the user "
    "message, above the '--- TASK ---' separator. Follow them exactly, as if "
    "they had been given to you here."
)

_TASK_SEPARATOR = "\n\n--- TASK ---\n\n"

_NON_RETRYABLE_ASSISTANT_ERRORS = frozenset(
    {"authentication_failed", "billing_error", "rate_limit", "invalid_request"}
)


def _assistant_failure(kind: str, detail: str) -> ProviderCallError:
    """Preserve the CLI's useful synthetic error before the SDK discards it.

    Claude Code represents authentication and billing failures as an
    ``AssistantMessage`` followed by a contradictory result carrying
    ``is_error=true`` and ``subtype=success``. Ignoring the assistant's
    ``error`` field is what turns an actionable failure into the SDK's
    misleading ``error result: success``.
    """
    label = kind.replace("_", " ")
    explanation = detail.strip() or "Claude Code returned no error detail."
    guidance = (
        " Sign in again with Claude Code (`claude auth login`) and retry."
        if kind == "authentication_failed"
        else ""
    )
    message = f"Claude Code {label}: {explanation}"
    if not message.endswith("."):
        message += "."
    return ProviderCallError(
        message + guidance,
        retryable=kind not in _NON_RETRYABLE_ASSISTANT_ERRORS,
    )


def _result_failure(message: ResultMessage) -> ProviderCallError:
    """Classify an error result that arrived without a synthetic assistant."""
    errors = getattr(message, "errors", None) or []
    detail = "; ".join(errors) or (getattr(message, "result", None) or "").strip()
    status = getattr(message, "api_error_status", None)
    subtype = getattr(message, "subtype", "unknown error")
    if not detail:
        detail = f"HTTP {status}" if status else f"result subtype {subtype}"
    retryable = bool(status and status >= 500) or subtype == "error_during_execution"
    return ProviderCallError(
        f"Claude Code call failed: {detail}",
        retryable=retryable,
    )


def _usage_from(message: ResultMessage) -> AIUsage:
    """Read everything the CLI reports about what a call consumed.

    Only `input_tokens` and `output_tokens` used to be read here, and with this
    provider that is close to reading nothing: the CLI accounts for prompt
    input under `cache_creation_input_tokens` and `cache_read_input_tokens`,
    and a call whose whole 31,000-character system prompt was cached reports
    `input_tokens: 2`. Every campaign therefore recorded a two-digit input
    figure for a six-figure reality, which silently disabled the token budget
    and understated the cost on the user's screen by roughly 40%.

    `total_cost_usd` is the CLI's own accounting for the call, cache pricing
    included. It is kept alongside the token counts rather than instead of
    them: the tokens are what the budget guard limits, the cost is what the
    user is actually charged, and neither can be derived from the other once
    caching is in play.
    """
    raw = getattr(message, "usage", None) or {}
    return AIUsage(
        input_tokens=raw.get("input_tokens") or 0,
        output_tokens=raw.get("output_tokens") or 0,
        cache_creation_input_tokens=raw.get("cache_creation_input_tokens") or 0,
        cache_read_input_tokens=raw.get("cache_read_input_tokens") or 0,
        reported_cost_usd=getattr(message, "total_cost_usd", None),
    )


def _cli_path() -> str | None:
    """Locate the Claude Code CLI the SDK drives. Same lookup as AgentsOS."""
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
    """Strip ANTHROPIC_API_KEY so the CLI authenticates via the operator's Claude
    subscription (OAuth credentials in ~/.claude/.credentials.json) instead of
    silently switching to API-key billing."""
    return {key: value for key, value in os.environ.items() if key != "ANTHROPIC_API_KEY"}


class ClaudeProvider(AIProvider):
    """AIProvider backed by the Claude Code CLI via the Claude Agent SDK.

    Runs are billed against the operator's Claude subscription rather than API
    credits (same mechanism as AgentsOS). No tools are enabled - agents only
    need text generation, not file/shell access.
    """

    def __init__(self, default_model: str) -> None:
        self._default_model = default_model

    def available_tools(self, model: str | None = None) -> frozenset[ResearchTool]:
        return frozenset(_CLI_TOOL_NAMES)

    def _options(self, request: AIRequest, system_prompt: str) -> ClaudeAgentOptions:
        tools = [_CLI_TOOL_NAMES[tool] for tool in dict.fromkeys(request.tools)]
        return ClaudeAgentOptions(
            model=request.model or self._default_model,
            system_prompt=system_prompt,
            max_turns=request.max_turns
            or (_MAX_RESEARCH_TURNS if tools else _MAX_TURNS),
            allowed_tools=tools,
            # A tool the CLI must ask a human about is a tool that never runs:
            # nothing is attached to this process's stdin, so the prompt has
            # no one to answer it and the call hangs until the deadline takes
            # it. `bypassPermissions` is scoped by `allowed_tools` in the same
            # breath - with the list empty, which is every campaign call, it
            # grants nothing because there is nothing to grant, and on a
            # research call it grants exactly WebSearch and WebFetch. No
            # file, shell or edit tool is ever reachable from this process.
            permission_mode="bypassPermissions" if tools else "default",
            cli_path=_cli_path(),
            env=_clean_env(),
            setting_sources=[],
        )

    @staticmethod
    def _prompt_text(request: AIRequest) -> str:
        return "\n\n".join(message.content for message in request.messages)

    def _payload(self, request: AIRequest) -> tuple[ClaudeAgentOptions, str]:
        """The options and prompt for one call, routed around the Windows
        command-line limit.

        A system prompt small enough to survive CreateProcess is passed as a
        system prompt, which is where it belongs. One too large to survive it
        is moved into the user message instead - that travels over stdin as
        stream-json, which has no length limit - and the system prompt becomes
        a short pointer to it. Verified on the real CLI: a role prompt
        delivered this way is followed exactly, output format included.

        Splitting on size rather than always folding keeps every call that
        already fits behaving exactly as before.
        """
        system = request.system_prompt or ""
        if request.tools:
            turn_limit = request.max_turns or _MAX_RESEARCH_TURNS
            research_turns = max(0, turn_limit - 4)
            system += (
                "\n\n# Research budget\n"
                f"This call has a hard limit of {turn_limit} assistant turns, including "
                "tool use and your final answer. "
                f"Use at most {research_turns} turns for research; reserve the remaining "
                "turns for producing the requested final answer. Batch independent "
                "searches where possible. Stop earlier when searches stop yielding "
                "useful evidence. Return the supported findings you have, even if "
                "fewer than requested or empty, and explain the limitation in the "
                "requested output format. Do not keep searching to fill a quota."
            )
        task = self._prompt_text(request)
        if len(system) <= _MAX_INLINE_SYSTEM_PROMPT_CHARS:
            return self._options(request, system), task
        return (
            self._options(request, _OVERSIZED_SYSTEM_NOTICE),
            f"{system}{_TASK_SEPARATOR}{task}",
        )

    async def generate(self, request: AIRequest) -> AIResponse:
        if _needs_proactor_thread():
            return await _ProactorLoopThread.instance().run(lambda: self._generate(request))
        return await self._generate(request)

    async def stream(self, request: AIRequest) -> AsyncIterator[str]:
        if _needs_proactor_thread():
            async for chunk in self._stream_via_proactor(request):
                yield chunk
            return
        async for chunk in self._stream(request):
            yield chunk

    async def _stream_via_proactor(self, request: AIRequest) -> AsyncIterator[str]:
        """Pump a stream produced on a private ProactorEventLoop (in a worker
        thread) back into the caller's loop."""
        caller_loop = asyncio.get_running_loop()
        chunks: asyncio.Queue[Any] = asyncio.Queue()

        def produce() -> None:
            async def pump() -> None:
                async for chunk in self._stream(request):
                    caller_loop.call_soon_threadsafe(chunks.put_nowait, chunk)

            outcome: Any = _STREAM_DONE
            try:
                _run_in_proactor_loop(pump)
            except Exception as exc:  # noqa: BLE001 - re-raised on the caller's loop
                outcome = exc
            finally:
                # Always signal, or the consumer waits on the queue forever.
                caller_loop.call_soon_threadsafe(chunks.put_nowait, outcome)

        worker = asyncio.get_running_loop().run_in_executor(None, produce)
        try:
            while True:
                item = await chunks.get()
                if item is _STREAM_DONE:
                    return
                if isinstance(item, BaseException):
                    raise item
                yield item
        finally:
            await worker

    async def _generate(self, request: AIRequest) -> AIResponse:
        model = request.model or self._default_model
        options, prompt = self._payload(request)

        final_text = ""
        usage = AIUsage()
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                # Every text block of the message, not just the last one: a
                # long answer can arrive split across blocks, and keeping only
                # the final one silently truncates it to its own tail.
                blocks = [
                    block.text
                    for block in message.content
                    if isinstance(block, TextBlock) and block.text.strip()
                ]
                if blocks:
                    final_text = "\n".join(blocks)
                if error := getattr(message, "error", None):
                    raise _assistant_failure(error, final_text)
            elif isinstance(message, ResultMessage):
                usage = _usage_from(message)
                if getattr(message, "result", None):
                    final_text = message.result
                if getattr(message, "is_error", False):
                    raise _result_failure(message)

        return AIResponse(content=final_text, model=model, usage=usage)

    async def _stream(self, request: AIRequest) -> AsyncIterator[str]:
        options, prompt = self._payload(request)

        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                blocks = [
                    block.text
                    for block in message.content
                    if isinstance(block, TextBlock) and block.text
                ]
                if error := getattr(message, "error", None):
                    raise _assistant_failure(error, "\n".join(blocks))
                for block in blocks:
                    yield block

    def count_tokens(self, text: str) -> int:
        """Rough approximation (~4 chars/token). The Claude Agent SDK doesn't
        expose an offline tokenizer; replace with real usage-based counting
        once available."""
        return max(1, len(text) // 4)
