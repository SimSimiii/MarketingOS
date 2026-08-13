import asyncio
import os
import sys
import threading
from collections.abc import AsyncIterator, Callable, Coroutine
from pathlib import Path
from typing import Any

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, ResultMessage, TextBlock, query

from app.ai.base import AIProvider, AIRequest, AIResponse, AIUsage

#: Marks the end of a bridged stream (see `_stream_via_proactor`).
_STREAM_DONE = object()

#: The CLI counts each assistant message as a turn, and a long answer (a full
#: email sequence, say) can arrive as more than one. With no tools enabled
#: there is nothing to loop on, so this is a runaway guard rather than a
#: budget - keep it well clear of normal generations.
_MAX_TURNS = 8

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


def _needs_proactor_thread() -> bool:
    """True when the running loop cannot spawn the CLI subprocess.

    On Windows only `ProactorEventLoop` supports subprocesses; a
    `SelectorEventLoop` raises a bare `NotImplementedError`, which the SDK
    surfaces as the message-less "Failed to start Claude Code: ". Uvicorn
    picks the selector loop for its worker whenever it spawns one - i.e. with
    `--reload` or `--workers` - so the API would fail exactly where it is
    most likely to be run.
    """
    if sys.platform != "win32":
        return False
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return False
    proactor = getattr(asyncio, "ProactorEventLoop", None)
    return proactor is not None and not isinstance(loop, proactor)


def _run_in_proactor_loop[T](factory: Callable[[], Coroutine[Any, Any, T]]) -> T:
    """Run one coroutine on a private ProactorEventLoop. Blocking - call it
    from a worker thread, never from the event loop."""
    loop = asyncio.ProactorEventLoop()  # type: ignore[attr-defined]
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(factory())
    finally:
        asyncio.set_event_loop(None)
        loop.close()


class _ProactorLoopThread:
    """One ProactorEventLoop, on one background thread, alive for the process
    - every CLI spawn on Windows runs on it instead of getting its own.

    `generate()` used to reach the CLI through `asyncio.to_thread(
    _run_in_proactor_loop, ...)`, which builds a fresh OS thread and a fresh
    ProactorEventLoop (with the IOCP handle underneath it) for every single
    model call and tears both down straight after. A knowledge compilation
    does that 4-6 times in a row and a campaign many more times, so this is
    pure per-call overhead on the hot path.

    This is an efficiency fix, not a correctness one - it is deliberately not
    what makes oversized prompts work; see
    `_MAX_INLINE_SYSTEM_PROMPT_CHARS` for that.
    """

    _instance: "_ProactorLoopThread | None" = None
    _instance_lock = threading.Lock()

    def __init__(self) -> None:
        self.loop = asyncio.ProactorEventLoop()  # type: ignore[attr-defined]
        self._thread = threading.Thread(
            target=self._run_forever, name="claude-cli-proactor", daemon=True
        )
        self._thread.start()

    def _run_forever(self) -> None:
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    @classmethod
    def instance(cls) -> "_ProactorLoopThread":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    async def run[T](self, factory: Callable[[], Coroutine[Any, Any, T]]) -> T:
        """Schedule one coroutine on the persistent loop and await it from
        the caller's own loop - `run_coroutine_threadsafe` is the standard
        bridge for exactly this, and `wrap_future` hands its result back as
        something the caller's loop can `await` directly."""
        future = asyncio.run_coroutine_threadsafe(factory(), self.loop)
        return await asyncio.wrap_future(future)


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

    def _options(self, request: AIRequest, system_prompt: str) -> ClaudeAgentOptions:
        return ClaudeAgentOptions(
            model=request.model or self._default_model,
            system_prompt=system_prompt,
            max_turns=_MAX_TURNS,
            allowed_tools=[],
            permission_mode="default",
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
            elif isinstance(message, ResultMessage):
                usage = _usage_from(message)
                if getattr(message, "result", None):
                    final_text = message.result

        return AIResponse(content=final_text, model=model, usage=usage)

    async def _stream(self, request: AIRequest) -> AsyncIterator[str]:
        options, prompt = self._payload(request)

        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock) and block.text:
                        yield block.text

    def count_tokens(self, text: str) -> int:
        """Rough approximation (~4 chars/token). The Claude Agent SDK doesn't
        expose an offline tokenizer; replace with real usage-based counting
        once available."""
        return max(1, len(text) // 4)
