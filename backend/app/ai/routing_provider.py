"""One `AIProvider` that fans out to several, chosen per call by model.

Per-agent model choice makes a single campaign a multi-vendor run: the writer
on GPT, the critic on Claude, the cold reader on whichever is cheaper. Nothing
above the provider layer should learn that. `ModelSession` resolves a role to a
model and hands over one `AIRequest`; this reads the model on it and picks the
backend that can bill for it.

The alternative - teaching `ModelSession` about vendors - would put vendor
names in the one class that exists to keep them out.
"""

from collections.abc import AsyncIterator

from app.ai.base import AIProvider, AIRequest, AIResponse, ResearchTool
from app.ai.models import ModelVendor, vendor_of


class RoutingProvider(AIProvider):
    """Dispatches each call to the provider that owns its model.

    A vendor with no backend configured fails the call by name rather than
    falling back to the default one. A silent fallback here would be the worst
    failure this system has: the run would succeed, the report would say the
    writer ran on GPT, and it would have run on Claude.
    """

    def __init__(
        self,
        backends: dict[ModelVendor, AIProvider],
        default_vendor: ModelVendor = ModelVendor.ANTHROPIC,
    ) -> None:
        if default_vendor not in backends:
            raise ValueError(
                f"default vendor '{default_vendor}' has no backend; "
                f"got {sorted(backends)}"
            )
        self._backends = backends
        self._default_vendor = default_vendor

    def _backend(self, model: str | None) -> AIProvider:
        vendor = vendor_of(model or "", default=self._default_vendor)
        backend = self._backends.get(vendor)
        if backend is None:
            raise ValueError(
                f"model '{model}' is served by {vendor}, which is not configured. "
                f"Available: {', '.join(sorted(self._backends))}."
            )
        return backend

    async def generate(self, request: AIRequest) -> AIResponse:
        return await self._backend(request.model).generate(request)

    async def stream(self, request: AIRequest) -> AsyncIterator[str]:
        async for chunk in self._backend(request.model).stream(request):
            yield chunk

    def available_tools(self, model: str | None = None) -> frozenset[ResearchTool]:
        """What the model about to be called can reach for.

        Answered by the backend that would take the call, not by unioning every
        backend: a union would tell a market role that web fetch is available
        because *some* provider has it, and the role would then be handed to
        one that does not.
        """
        return self._backend(model).available_tools(model)

    def count_tokens(self, text: str) -> int:
        """Estimation only, and every backend does it the same crude way
        (~4 chars/token), so the default vendor's answer is the answer."""
        return self._backends[self._default_vendor].count_tokens(text)
