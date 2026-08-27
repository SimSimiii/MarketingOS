from app.ai.models import DEFAULT_TIER_MODELS, ModelTier

#: `ModelTier` and the tier map moved to `app.ai.models`, where the catalog
#: that has to name a tier per model lives. Re-exported here because every
#: caller in the system spells it `from app.ai.model_router import ModelTier`,
#: and a rename that touches thirty call sites to move one class is churn, not
#: a refactor.
__all__ = ["DEFAULT_TIER_MODELS", "ModelRouter", "ModelTier"]


class ModelRouter:
    """Resolves which model a role's call actually goes to.

    Three layers, most specific first: an override for that exact role id, a
    blanket "*" override (how a policy preset - or an operator picking "every
    agent" - moves the whole run onto one model), then the tier map. Override
    wins outright; there is no blending.
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
