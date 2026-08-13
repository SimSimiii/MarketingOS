from app.ai.model_router import ModelRouter, ModelTier


def test_a_tier_resolves_to_the_model_that_kind_of_thinking_is_worth():
    """Roles ask for a kind of thinking, never for a model - so a new model
    generation moves one mapping instead of every role."""
    router = ModelRouter()
    assert router.resolve("blind_reader", ModelTier.BALANCED) == "sonnet"
    assert router.resolve("email_writer", ModelTier.DEEP) == "opus"
    assert router.resolve("knowledge_compiler", ModelTier.FAST) == "haiku"


def test_a_per_role_override_wins_over_the_tier():
    router = ModelRouter({"email_writer": "fable5"})
    assert router.resolve("email_writer", ModelTier.DEEP) == "fable5"
    assert router.resolve("blind_reader", ModelTier.BALANCED) == "sonnet"  # untouched


def test_a_wildcard_override_applies_to_every_role():
    router = ModelRouter({"*": "haiku"})
    assert router.resolve("email_writer", ModelTier.DEEP) == "haiku"
    assert router.resolve("conversion_critic", ModelTier.DEEP) == "haiku"


def test_a_specific_override_beats_the_wildcard():
    router = ModelRouter({"*": "haiku", "conversion_critic": "opus"})
    assert router.resolve("conversion_critic", ModelTier.DEEP) == "opus"
    assert router.resolve("email_writer", ModelTier.DEEP) == "haiku"


def test_the_tier_map_itself_can_be_remapped():
    router = ModelRouter(tier_models={ModelTier.DEEP: "fable5"})
    assert router.resolve("email_writer", ModelTier.DEEP) == "fable5"
    assert router.resolve("blind_reader", ModelTier.BALANCED) == "sonnet"
