"""GPT models, billed to the operator's ChatGPT plan rather than API credits.

The mirror of `ClaudeProvider`, and for the same reason: a ChatGPT subscription
has no HTTP API. The only surface OpenAI meters against the plan instead of the
API balance is Codex, so this provider drives the `codex` binary as a
subprocess exactly as the Claude Agent SDK drives `claude`. Everything that
looks like a hack here is the shape of that constraint, not a shortcut around
it - and the one line that actually decides who pays is `_clean_env`.
"""

import asyncio
import json
import logging
import os
import shutil
import tempfile
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from app.ai._win_loop import _needs_proactor_thread, _ProactorLoopThread
from app.ai.base import AIProvider, AIRequest, AIResponse, AIUsage, ResearchTool
from app.ai.models import OpenAIModel

logger = logging.getLogger("marketingos.ai.openai")

#: Codex has live web search (`--search`) and nothing that fetches one named
#: URL. Declared rather than approximated - see `ResearchTool`.
_SUPPORTED_TOOLS = frozenset({ResearchTool.WEB_SEARCH})

#: Codex takes no system prompt: `codex exec` has one prompt and its standing
#: instructions come from `AGENTS.md` files it discovers on disk. Writing one
#: per call would be a race between concurrent calls sharing a directory, so
#: the role prompt travels inside the message instead, above this separator.
#: The same fold `ClaudeProvider` uses for oversized prompts, and verified
#: there to be followed exactly, output format included.
_TASK_SEPARATOR = "\n\n--- TASK ---\n\n"

#: Seconds one call may take before it is killed. Deliberately generous: a deep
#: role on a reasoning model legitimately thinks for minutes. This is not the
#: budget - `ExecutionPolicy.max_duration_seconds` is - it is the guard against
#: a subprocess that will never answer at all, which would otherwise hold the
#: whole run until the campaign deadline.
_CALL_TIMEOUT_SECONDS = 600.0

#: How much of the CLI's stderr is quoted back in an error. Enough to carry a
#: rate-limit message or an auth failure, short enough not to bury it.
_STDERR_EXCERPT_CHARS = 800


class CodexNotInstalledError(RuntimeError):
    """The `codex` binary is not on this machine.

    Its own type because it is the one failure with a fix the operator can act
    on, and it must not read like a transient blip: `ModelSession` retries a
    provider three times before giving up, and three identical "not found"
    errors is a worse message than one that says what to install.
    """


def _codex_path() -> str | None:
    """Locate the Codex CLI.

    Same shape as `claude_provider._cli_path`: an explicit override first so an
    operator can point at a specific build, then the places npm and the
    official installer put it, then whatever is on PATH.
    """
    explicit = os.environ.get("CODEX_CLI_PATH")
    if explicit and Path(explicit).exists():
        return explicit
    candidates: list[Path] = []
    if appdata := os.environ.get("APPDATA"):
        # npm global installs on Windows: the shim, not the JS entry point.
        candidates += [Path(appdata) / "npm" / name for name in ("codex.cmd", "codex.exe")]
    if home := os.environ.get("USERPROFILE") or os.environ.get("HOME"):
        candidates += [
            Path(home) / ".codex" / "bin" / "codex.exe",
            Path(home) / ".codex" / "bin" / "codex",
            Path(home) / ".local" / "bin" / "codex",
        ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return shutil.which("codex")


def _clean_env() -> dict[str, str]:
    """Strip every API credential so Codex authenticates as the ChatGPT plan.

    The exact counterpart of `claude_provider._clean_env`, and the whole reason
    this provider exists. With `OPENAI_API_KEY` or `CODEX_API_KEY` visible,
    Codex bills the API balance and the run costs money the operator did not
    mean to spend; without them it falls back to the ChatGPT credentials
    written by `codex login` (`~/.codex/auth.json`), which is what the plan
    covers.

    Failing loudly would be worse than this: an operator who has an API key set
    for unrelated reasons should still get subscription billing, because that
    is what they asked this provider for.
    """
    return {
        key: value
        for key, value in os.environ.items()
        if key not in ("OPENAI_API_KEY", "CODEX_API_KEY")
    }


def _usage_from(raw: dict[str, Any] | None) -> AIUsage:
    """Read what one Codex turn consumed.

    Two mappings that are easy to get wrong and expensive to get wrong:

    `cached_input_tokens` is a *subset* of `input_tokens`, not a sibling of it.
    `AIUsage` splits them, so the cached part is moved across rather than added
    - copying both through as-is would double-count the majority of every call
    after the first and make the budget guard fire on runs that were fine.

    `reasoning_output_tokens` is billed as output and reported separately.
    Folding it in is what keeps a reasoning model's real cost visible instead
    of showing the handful of tokens it happened to say out loud.
    """
    raw = raw or {}
    total_input = raw.get("input_tokens") or 0
    cached = raw.get("cached_input_tokens") or 0
    return AIUsage(
        input_tokens=max(0, total_input - cached),
        cache_read_input_tokens=min(cached, total_input),
        output_tokens=(raw.get("output_tokens") or 0)
        + (raw.get("reasoning_output_tokens") or 0),
        # Codex reports tokens and never a price. Left None so
        # `usage_cost_usd` falls back to the table rather than recording a
        # confident zero, which would read as "this run was free".
        reported_cost_usd=None,
    )


class OpenAIProvider(AIProvider):
    """AIProvider backed by the Codex CLI, billed to the ChatGPT plan.

    Runs `codex exec --json` once per call and reads the JSONL it streams. The
    process is confined about as far as Codex allows: a read-only sandbox, an
    empty scratch directory as its working directory, and no session files left
    behind. It cannot see this repository and cannot write anything.
    """

    def __init__(self, default_model: str = OpenAIModel.SOL) -> None:
        self._default_model = default_model
        self._workdir: str | None = None

    def available_tools(self, model: str | None = None) -> frozenset[ResearchTool]:
        return _SUPPORTED_TOOLS

    # --------------------------------------------------------------- command

    def _cwd(self) -> str:
        """An empty directory to run Codex in, made once per provider.

        Codex reads `AGENTS.md` from its working directory and treats a git
        repo as the thing it is there to work on. Pointed at this project it
        would pick up both, so a marketing prompt would arrive carrying the
        repository's coding instructions - and the sandbox, however read-only,
        would have the source tree in reach. An empty directory removes the
        question rather than answering it.
        """
        if self._workdir is None or not Path(self._workdir).exists():
            self._workdir = tempfile.mkdtemp(prefix="marketingos-codex-")
        return self._workdir

    def _command(self, request: AIRequest) -> list[str]:
        binary = _codex_path()
        if binary is None:
            raise CodexNotInstalledError(
                "The Codex CLI is not installed, so GPT models cannot be reached. "
                "Install it with `npm install -g @openai/codex`, run `codex login` "
                "and sign in with ChatGPT (not an API key), or point CODEX_CLI_PATH "
                "at an existing build."
            )
        wants_search = ResearchTool.WEB_SEARCH in request.tools
        command = [
            binary,
            "exec",
            # One JSON object per line on stdout: the only way to get the
            # answer and the token counts out of the same call.
            "--json",
            # No session file per call. A campaign makes tens of calls and this
            # process is a server; without it every run leaves a trail of
            # transcripts in ~/.codex/sessions that nothing ever reads.
            "--ephemeral",
            # The scratch cwd is deliberately not a git repo, and Codex refuses
            # to start outside one unless told the environment is understood.
            "--skip-git-repo-check",
            # Nothing this system asks a model to do involves changing a file.
            "--sandbox",
            "read-only",
            "-m",
            request.model or self._default_model,
            "-C",
            self._cwd(),
        ]
        if wants_search:
            command.append("--search")
        # The prompt goes over stdin. Not an optimisation: Windows caps a whole
        # command line at 32,767 characters and a compiled-knowledge prompt runs
        # to ~42,000, so passing it as an argument fails to start the process at
        # all. `-` is the documented sentinel that forces the stdin read.
        command.append("-")
        return command

    @staticmethod
    def _prompt(request: AIRequest) -> str:
        task = "\n\n".join(message.content for message in request.messages)
        system = request.system_prompt or ""
        return f"{system}{_TASK_SEPARATOR}{task}" if system else task

    # ---------------------------------------------------------------- events

    async def _run(self, request: AIRequest) -> tuple[str, AIUsage, str]:
        """Run one `codex exec` and return (text, usage, resolved model)."""
        command = self._command(request)
        process = await asyncio.create_subprocess_exec(
            *command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=_clean_env(),
            cwd=self._cwd(),
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(self._prompt(request).encode("utf-8")),
                timeout=_CALL_TIMEOUT_SECONDS,
            )
        except TimeoutError:
            process.kill()
            await process.wait()
            raise TimeoutError(
                f"codex exec did not answer within {_CALL_TIMEOUT_SECONDS:.0f}s"
            ) from None

        text, usage, model, failure = _read_stream(stdout.decode("utf-8", "replace"))
        if failure is not None:
            raise RuntimeError(f"codex exec reported a failed turn: {failure}")
        if process.returncode != 0:
            detail = stderr.decode("utf-8", "replace").strip()[-_STDERR_EXCERPT_CHARS:]
            raise RuntimeError(
                f"codex exec exited {process.returncode}: {detail or 'no output on stderr'}"
            )
        if not text.strip():
            # A clean exit with nothing said is not a usable answer, and
            # returning "" would send an empty string into a JSON parser that
            # reports it as a schema failure - blaming the wrong layer.
            detail = stderr.decode("utf-8", "replace").strip()[-_STDERR_EXCERPT_CHARS:]
            raise RuntimeError(
                f"codex exec returned no assistant message. {detail or 'stderr was empty.'}"
            )
        return text, usage, model or (request.model or self._default_model)

    # --------------------------------------------------------------- surface

    async def generate(self, request: AIRequest) -> AIResponse:
        if _needs_proactor_thread():
            return await _ProactorLoopThread.instance().run(lambda: self._generate(request))
        return await self._generate(request)

    async def _generate(self, request: AIRequest) -> AIResponse:
        text, usage, model = await self._run(request)
        return AIResponse(content=text, model=model, usage=usage)

    async def stream(self, request: AIRequest) -> AsyncIterator[str]:
        """Codex exec streams events, not tokens.

        The whole assistant message arrives on one `item.completed` line, so
        there is nothing finer to yield than the finished answer. Implemented
        as a one-chunk stream rather than left unimplemented: every caller of
        `stream` wants text, and none of them requires it to arrive in pieces.
        """
        response = await self.generate(request)
        yield response.content

    def count_tokens(self, text: str) -> int:
        """Rough approximation (~4 chars/token), matching ClaudeProvider. The
        real counts come back with every call in `AIUsage`; this is only for
        callers estimating before they spend."""
        return max(1, len(text) // 4)


def _read_stream(stdout: str) -> tuple[str, AIUsage, str | None, str | None]:
    """Pull the answer, the usage, the model and any failure out of the JSONL.

    Tolerant by construction. The stream is a versioned event feed from a tool
    that ships weekly, so an unknown `type`, an unparseable line or a field
    that moved must cost at most the thing it carried - never the call. The
    only event whose absence is fatal is the assistant message itself, and the
    caller raises for that, having also seen stderr.
    """
    text = ""
    usage = AIUsage()
    model: str | None = None
    failure: str | None = None

    for line in stdout.splitlines():
        line = line.strip()
        if not line or not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            logger.debug("codex: ignoring unparseable line: %.120s", line)
            continue
        if not isinstance(event, dict):
            continue

        match event.get("type"):
            case "item.completed":
                item = event.get("item") or {}
                if item.get("type") == "agent_message":
                    # Last one wins: a turn that produced several messages ends
                    # on the one that answers the question.
                    if content := (item.get("text") or "").strip():
                        text = content
            case "turn.completed":
                usage = _usage_from(event.get("usage"))
            case "turn.failed":
                error = event.get("error") or {}
                failure = (
                    error.get("message") if isinstance(error, dict) else str(error)
                ) or "no detail given"
            case "thread.started":
                model = event.get("model") or model

    return text, usage, model, failure
