from enum import StrEnum

from app.ai.base import AIUsage


class ClaudeModel(StrEnum):
    """The only models MarketingOS is allowed to route work to.

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


#: Rough $ per 1K (input, output) tokens - only used to estimate spend against
#: an execution budget (see ExecutionPolicy.max_total_tokens / cost). The
#: Claude Code CLI bills the operator's subscription, not per-token API
#: usage, so this is an estimate for the user's own budget tracking, never a
#: real invoice.
MODEL_COST_PER_1K_TOKENS: dict[str, tuple[float, float]] = {
    ClaudeModel.HAIKU: (0.001, 0.005),
    ClaudeModel.SONNET: (0.003, 0.015),
    ClaudeModel.OPUS: (0.015, 0.075),
    ClaudeModel.FABLE: (0.003, 0.015),
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
    for providers that report only tokens - and it prices the three kinds of
    input separately, because after prompt caching they differ by a factor of
    more than ten and lumping them together is how a campaign's cost estimate
    ends up wrong in whichever direction the cache happened to fall.
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
