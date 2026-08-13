from enum import StrEnum

from app.ai.models import ClaudeModel


class ModelTier(StrEnum):
    """What a call is worth paying for, named by the kind of thinking it does.

    Roles ask for a tier, never a model. A role that extracts fields from text
    it was handed is not doing the same work as one judging whether a piece of
    copy will make somebody buy, and the difference between those two is the
    only thing that should decide model spend. Naming the tier after the work
    also means a new model generation moves one mapping instead of every role.
    """

    #: Mechanical extraction and reformatting of text already in the prompt.
    FAST = "fast"
    #: Distillation and synthesis - reading a lot, writing down what matters.
    BALANCED = "balanced"
    #: Judgment and craft: strategy, copy, criticism. Never economize here.
    DEEP = "deep"


DEFAULT_TIER_MODELS: dict[ModelTier, str] = {
    ModelTier.FAST: ClaudeModel.HAIKU,
    ModelTier.BALANCED: ClaudeModel.SONNET,
    ModelTier.DEEP: ClaudeModel.OPUS,
}


class ModelRouter:
    """Resolves which model a role's call actually goes to.

    Three layers, most specific first: an override for that exact role id, a
    blanket "*" override (how a policy preset moves the whole run onto one
    model), then the tier map. Override wins outright; there is no blending.
    """

    def __init__(
        self,
        overrides: dict[str, str] | None = None,
        tier_models: dict[ModelTier, str] | None = None,
    ) -> None:
        self._overrides = overrides or {}
        self._tier_models = {**DEFAULT_TIER_MODELS, **(tier_models or {})}

    def resolve(self, role_id: str, tier: ModelTier) -> str:
        if role_id in self._overrides:
            return self._overrides[role_id]
        if "*" in self._overrides:
            return self._overrides["*"]
        return self._tier_models[tier]
