"""Which audience actually reached which role, measured rather than assumed.

An A/B/C experiment on audience intelligence is worthless if the arms did not
differ where they were supposed to differ. `demand()` returning a map does not
mean the strategist saw it; a segment at the head of the merged audience model
does not mean the cold reader was built from it. Both of those are true by
construction today, and both have been silently false before - the whole reason
this experiment exists is that a benchmark ran for months against
`positioning() is None` and nothing anywhere said so.

So the benchmark does not trust the wiring, it greps it. `PromptProbe` wraps
the provider, forwards every call untouched, and writes down which of a set of
known phrases appeared in the prompt that went out, keyed by the role that sent
it. It is a decorator over `AIProvider` and lives entirely in the evaluation
package: no production code knows it exists, no role behaves differently
because of it, and the only thing it can affect is the benchmark's own record.

Reading the result: `seen["strategist"]` containing `researched_fixture.trigger`
means the researched fixture's trigger sentence was in the strategist's prompt.
The `none` arm is probed for the *other* arms' markers too, so "this arm had no
audience intelligence" is a measurement rather than an omission.
"""

from collections import defaultdict
from collections.abc import AsyncIterator

from app.ai.base import AIProvider, AIRequest, AIResponse, ResearchTool


class PromptProbe(AIProvider):
    """Forwards to a real provider and records what reached each role's prompt."""

    def __init__(self, inner: AIProvider, markers: dict[str, str]) -> None:
        self._inner = inner
        #: label -> the verbatim phrase to look for. Folded once here rather
        #: than per call: a run makes hundreds of calls and every prompt is
        #: tens of thousands of characters.
        self._markers = {label: phrase.lower() for label, phrase in markers.items()}
        #: role -> the labels that turned up in at least one of its prompts.
        self.seen: dict[str, set[str]] = defaultdict(set)
        self.calls_by_role: dict[str, int] = defaultdict(int)

    # ------------------------------------------------------------ provider

    async def generate(self, request: AIRequest) -> AIResponse:
        self._record(request)
        return await self._inner.generate(request)

    async def stream(self, request: AIRequest) -> AsyncIterator[str]:
        self._record(request)
        async for chunk in self._inner.stream(request):
            yield chunk

    def count_tokens(self, text: str) -> int:
        return self._inner.count_tokens(text)

    def available_tools(self, model: str | None = None) -> frozenset[ResearchTool]:
        """Delegated, not answered.

        A probe that reported no tools would refuse a market role its web
        access, and one that reported all of them would let a run believe it
        had searched when it had not. Neither belongs in an instrument.
        """
        return self._inner.available_tools(model)

    # -------------------------------------------------------------- record

    def _record(self, request: AIRequest) -> None:
        role = request.role or "(unattributed)"
        self.calls_by_role[role] += 1
        # The task as well as the system prompt: most roles carry the audience
        # in the system prompt, but the reader carries the email there and its
        # instruction in the task, and a probe that read only one of the two
        # would answer differently for different roles for no reason.
        text = f"{request.system_prompt or ''}\n{_task_text(request)}".lower()
        for label, phrase in self._markers.items():
            if phrase in text:
                self.seen[role].add(label)

    def reached(self, *roles: str) -> dict[str, list[str]]:
        """What each of these roles saw, sorted, ready to be recorded as JSON.

        Roles that never ran are reported as an empty list rather than dropped:
        "the critic was off in this preset" and "the critic ran and saw nothing"
        are different findings, and a missing key would make them look alike.
        """
        return {role: sorted(self.seen.get(role, set())) for role in roles}


def _task_text(request: AIRequest) -> str:
    return "\n".join(message.content for message in request.messages)
