from dataclasses import dataclass, field
from enum import StrEnum

from app.ai.base import AIUsage, ResearchTool


class ModelTier(StrEnum):
    """What a call is worth paying for, named by the kind of thinking it does.

    Roles ask for a tier, never a model. A role that extracts fields from text
    it was handed is not doing the same work as one judging whether a piece of
    copy will make somebody buy, and the difference between those two is the
    only thing that should decide model spend. Naming the tier after the work
    also means a new model generation moves one mapping instead of every role.

    Lives here rather than beside `ModelRouter` because a tier is a fact about
    models, and the catalog below has to name one per model. `model_router`
    re-exports it, so every existing `from app.ai.model_router import
    ModelTier` still resolves.
    """

    #: Mechanical extraction and reformatting of text already in the prompt.
    FAST = "fast"
    #: Distillation and synthesis - reading a lot, writing down what matters.
    BALANCED = "balanced"
    #: Judgment and craft: strategy, copy, criticism. Never economize here.
    DEEP = "deep"


class ModelVendor(StrEnum):
    """Who bills for a call, and therefore which provider has to make it.

    This is the field `RoutingProvider` dispatches on: a run with the writer on
    a GPT model and the critic on Claude is two vendors inside one campaign,
    and nothing above the provider layer should have to know that.
    """

    ANTHROPIC = "anthropic"
    OPENAI = "openai"


class ClaudeModel(StrEnum):
    """The Claude models MarketingOS is allowed to route work to.

    Short CLI aliases, not pinned snapshot ids - the Claude Code CLI that
    ClaudeProvider drives resolves each alias to its latest version, so the
    catalog never goes stale. Fable is included per product decision but is
    unverified on older CLI installs; a campaign that requests it will
    surface a clear ProviderError (see app.runtime.runtime._provider_error)
    rather than silently falling back, if the local CLI does not know it.
    """

    HAIKU = "haiku"
    SONNET = "sonnet"
    OPUS = "opus"
    FABLE = "fable5"


class OpenAIModel(StrEnum):
    """The GPT models MarketingOS is allowed to route work to.

    Full slugs, not aliases: unlike the Claude CLI, Codex takes the exact model
    name and OpenAI retires slugs on dated schedules rather than moving an
    alias forward. That makes this list perishable by construction - it is
    correct as of 2026-08-26 and will need revisiting. Two consequences are
    designed for rather than fought:

    - `gpt-5.4` and `gpt-5.4-mini` are deliberately absent. They retire from
      Codex on 2026-08-31, so shipping them would mean shipping a default that
      breaks within the week.
    - The picker accepts a slug that is not in this list (see
      `app.ai.roles.validate_overrides`), so a model released tomorrow is
      usable today without a deploy.
    """

    #: The default for a ChatGPT-authenticated Codex session.
    SOL = "gpt-5.6-sol"
    TERRA = "gpt-5.6-terra"
    LUNA = "gpt-5.6-luna"
    #: ChatGPT Pro only - a run that asks for it on a lesser plan fails the
    #: call rather than quietly downgrading.
    SPARK = "gpt-5.3-codex-spark"
    #: Previous generation, kept selectable: it is the fallback when a 5.6
    #: model behaves worse on a specific role than the one it replaced.
    GPT_5_5 = "gpt-5.5"


@dataclass(frozen=True)
class ModelSpec:
    """One selectable model, as the picker has to present it.

    Carries what a person needs in order to choose between two names in a
    dropdown - who bills for it, roughly what it is for, and what it cannot do
    - so the frontend renders the catalog instead of restating it. A list of
    models hardcoded in TypeScript is a list that disagrees with the router the
    first time either side changes.
    """

    id: str
    vendor: ModelVendor
    label: str
    #: One line, written for someone choosing, not for a spec sheet.
    blurb: str
    #: The tier this model is the default for, when it is one. `None` means
    #: selectable but never chosen automatically.
    default_for: "ModelTier | None" = None
    #: Capabilities this model can be given. A role that needs one the model
    #: does not have is refused at the session boundary rather than answered
    #: without it - see `AIProvider.available_tools`.
    tools: frozenset[ResearchTool] = field(default_factory=frozenset)
    #: Set when the model needs a plan the operator may not have. Shown as a
    #: warning in the picker; not enforced here, because only the vendor knows.
    requires: str | None = None


_CLAUDE_TOOLS = frozenset({ResearchTool.WEB_SEARCH, ResearchTool.WEB_FETCH})
#: Codex exposes live web search (`--search`) but has no equivalent of a
#: standalone fetch-this-URL tool. Declared honestly rather than approximated:
#: a research role that silently loses half its access returns confident
#: invention, which is the one failure this system is built to prevent.
_OPENAI_TOOLS = frozenset({ResearchTool.WEB_SEARCH})


MODEL_CATALOG: dict[str, ModelSpec] = {
    spec.id: spec
    for spec in (
        ModelSpec(
            id=ClaudeModel.HAIKU,
            vendor=ModelVendor.ANTHROPIC,
            label="Claude Haiku",
            blurb="Fastest and cheapest. Extraction and reformatting, not judgment.",
            default_for=ModelTier.FAST,
            tools=_CLAUDE_TOOLS,
        ),
        ModelSpec(
            id=ClaudeModel.SONNET,
            vendor=ModelVendor.ANTHROPIC,
            label="Claude Sonnet",
            blurb="The workhorse. Reads a lot, writes down what matters.",
            default_for=ModelTier.BALANCED,
            tools=_CLAUDE_TOOLS,
        ),
        ModelSpec(
            id=ClaudeModel.OPUS,
            vendor=ModelVendor.ANTHROPIC,
            label="Claude Opus",
            blurb="Strongest judgment. Strategy, copy and criticism.",
            default_for=ModelTier.DEEP,
            tools=_CLAUDE_TOOLS,
        ),
        ModelSpec(
            id=ClaudeModel.FABLE,
            vendor=ModelVendor.ANTHROPIC,
            label="Claude Fable",
            blurb="Tuned for prose. Worth trying on the writer and subject lines.",
            tools=_CLAUDE_TOOLS,
            requires="A Claude Code CLI recent enough to know the alias",
        ),
        ModelSpec(
            id=OpenAIModel.LUNA,
            vendor=ModelVendor.OPENAI,
            label="GPT-5.6 Luna",
            blurb="OpenAI's light model. The GPT counterpart to Haiku.",
            tools=_OPENAI_TOOLS,
        ),
        ModelSpec(
            id=OpenAIModel.TERRA,
            vendor=ModelVendor.OPENAI,
            label="GPT-5.6 Terra",
            blurb="Mid-weight GPT. Synthesis and summarizing.",
            tools=_OPENAI_TOOLS,
        ),
        ModelSpec(
            id=OpenAIModel.SOL,
            vendor=ModelVendor.OPENAI,
            label="GPT-5.6 Sol",
            blurb="OpenAI's strongest, and what Codex picks by default.",
            tools=_OPENAI_TOOLS,
        ),
        ModelSpec(
            id=OpenAIModel.SPARK,
            vendor=ModelVendor.OPENAI,
            label="GPT-5.3 Codex Spark",
            blurb="Long-horizon reasoning. Slow, and gated behind ChatGPT Pro.",
            tools=_OPENAI_TOOLS,
            requires="ChatGPT Pro",
        ),
        ModelSpec(
            id=OpenAIModel.GPT_5_5,
            vendor=ModelVendor.OPENAI,
            label="GPT-5.5",
            blurb="Previous generation. Keep for comparison against 5.6.",
            tools=_OPENAI_TOOLS,
        ),
    )
}


#: Slug fragments that identify a vendor for a model this catalog has never
#: heard of. Only consulted for operator-typed slugs (see `vendor_of`): every
#: model in `MODEL_CATALOG` is matched by identity first.
_VENDOR_HINTS: tuple[tuple[tuple[str, ...], ModelVendor], ...] = (
    (("gpt", "o1-", "o3-", "o4-", "codex"), ModelVendor.OPENAI),
    (("claude", "haiku", "sonnet", "opus", "fable"), ModelVendor.ANTHROPIC),
)


def vendor_of(model: str, default: ModelVendor = ModelVendor.ANTHROPIC) -> ModelVendor:
    """Which provider has to make this call.

    Catalog first, then a prefix guess, then the configured default. The guess
    exists because the picker accepts a slug this build has never seen - that
    is what keeps a model released after this deploy usable - and a slug
    starting `gpt-` routed to the Claude CLI would fail with an error naming
    the wrong vendor.
    """
    if spec := MODEL_CATALOG.get(model):
        return spec.vendor
    lowered = model.lower()
    for fragments, vendor in _VENDOR_HINTS:
        if any(fragment in lowered for fragment in fragments):
            return vendor
    return default


def tools_for(model: str) -> frozenset[ResearchTool]:
    """What this model can reach for beyond its own prompt.

    An unknown slug inherits its vendor's capabilities rather than none: a GPT
    model released tomorrow searches the web the same way today's does, and
    returning an empty set would fail every research role on it.
    """
    if spec := MODEL_CATALOG.get(model):
        return spec.tools
    return _OPENAI_TOOLS if vendor_of(model) is ModelVendor.OPENAI else _CLAUDE_TOOLS


DEFAULT_TIER_MODELS: dict[ModelTier, str] = {
    ModelTier.FAST: ClaudeModel.HAIKU,
    ModelTier.BALANCED: ClaudeModel.SONNET,
    ModelTier.DEEP: ClaudeModel.OPUS,
}


#: Rough $ per 1K (input, output) tokens - only used to estimate spend against
#: an execution budget (see ExecutionPolicy.max_total_tokens / cost). Both CLIs
#: bill the operator's subscription, not per-token API usage, so this is an
#: estimate for the user's own budget tracking, never a real invoice.
#:
#: The Claude figures are list API prices. The OpenAI ones are deliberately
#: coarse: Codex reports token counts but no cost at all - unlike the Claude
#: CLI, which reports `total_cost_usd` - so for GPT calls this table is the
#: only number there is. They are set at the same order of magnitude as the
#: Claude tier each model answers to, which is enough for a budget guard and is
#: not claimed to be more.
MODEL_COST_PER_1K_TOKENS: dict[str, tuple[float, float]] = {
    ClaudeModel.HAIKU: (0.001, 0.005),
    ClaudeModel.SONNET: (0.003, 0.015),
    ClaudeModel.OPUS: (0.015, 0.075),
    ClaudeModel.FABLE: (0.003, 0.015),
    OpenAIModel.LUNA: (0.001, 0.005),
    OpenAIModel.TERRA: (0.003, 0.015),
    OpenAIModel.SOL: (0.015, 0.075),
    OpenAIModel.SPARK: (0.015, 0.075),
    OpenAIModel.GPT_5_5: (0.003, 0.015),
}

#: Cached input is not priced like fresh input, and treating it as if it were
#: overstates the cost of exactly the calls this system makes most: the same
#: writer system prompt, sent again a minute later. Writing to the cache costs
#: a surcharge over the base input rate; reading from it costs a fraction.
_CACHE_WRITE_MULTIPLIER = 1.25
_CACHE_READ_MULTIPLIER = 0.10


def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    """Cost of one call from token counts alone.

    Kept for callers that only have the two flat numbers. Anything holding a
    full `AIUsage` should call `usage_cost_usd`, which prices cached input
    correctly and defers to the provider's own figure when it gave one.
    """
    input_rate, output_rate = MODEL_COST_PER_1K_TOKENS.get(
        model, MODEL_COST_PER_1K_TOKENS[ClaudeModel.SONNET]
    )
    return (input_tokens / 1000) * input_rate + (output_tokens / 1000) * output_rate


def usage_cost_usd(model: str, usage: AIUsage) -> float:
    """What one call cost, preferring the provider's own accounting.

    When the provider reported a figure it wins outright: it knows its price
    list, including the caching discounts and any plan-level rates that no
    table in this repository can track. The arithmetic below is the fallback
    for providers that report only tokens - which is every Codex call - and it
    prices the three kinds of input separately, because after prompt caching
    they differ by a factor of more than ten and lumping them together is how a
    campaign's cost estimate ends up wrong in whichever direction the cache
    happened to fall.
    """
    if usage.reported_cost_usd is not None:
        return usage.reported_cost_usd
    input_rate, output_rate = MODEL_COST_PER_1K_TOKENS.get(
        model, MODEL_COST_PER_1K_TOKENS[ClaudeModel.SONNET]
    )
    return (
        (usage.input_tokens / 1000) * input_rate
        + (usage.cache_creation_input_tokens / 1000) * input_rate * _CACHE_WRITE_MULTIPLIER
        + (usage.cache_read_input_tokens / 1000) * input_rate * _CACHE_READ_MULTIPLIER
        + (usage.output_tokens / 1000) * output_rate
    )
