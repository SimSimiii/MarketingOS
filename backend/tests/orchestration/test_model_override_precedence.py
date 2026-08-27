"""Which model map a run actually routes on, once a preset and an operator
have both had an opinion.

`ModelRouter` checks an exact role id before it looks at the wildcard. That is
right for the router and it is a trap here: `maximum` ships per-role overrides,
so a plain merge would let a preset's suggestion outrank the operator's own
"every agent" choice - silently, and on the five roles they most likely meant.
"""

from app.ai.model_router import ModelRouter, ModelTier
from app.marketing.policy import PRESETS, ExecutionPolicy
from app.models.campaign import Campaign
from app.orchestration.campaign_orchestrator import _resolve_overrides


def _campaign(model_overrides: dict[str, str] | None) -> Campaign:
    return Campaign(
        name="Launch",
        request="three emails",
        product_description="a thing",
        model_overrides=model_overrides,
    )


def test_a_preset_with_no_opinion_leaves_the_operator_in_charge():
    overrides = _resolve_overrides(ExecutionPolicy(), _campaign({"email_writer": "gpt-5.6-sol"}))
    assert ModelRouter(overrides).resolve("email_writer", ModelTier.DEEP) == "gpt-5.6-sol"


def test_a_pin_beats_the_presets_choice_for_that_role():
    overrides = _resolve_overrides(
        PRESETS["maximum"], _campaign({"email_writer": "gpt-5.6-sol"})
    )
    router = ModelRouter(overrides)

    assert router.resolve("email_writer", ModelTier.DEEP) == "gpt-5.6-sol"
    # Everything the operator did not touch still follows the preset.
    assert router.resolve("strategist", ModelTier.DEEP) == "opus"


def test_every_agent_displaces_the_presets_per_role_overrides():
    """The bug this function exists for. `maximum` names five craft roles, and
    a merge would leave all five on opus while the panel showed GPT."""
    overrides = _resolve_overrides(PRESETS["maximum"], _campaign({"*": "gpt-5.6-sol"}))
    router = ModelRouter(overrides)

    for role in ("strategist", "email_writer", "conversion_critic", "sequence_reviewer"):
        assert router.resolve(role, ModelTier.DEEP) == "gpt-5.6-sol", role
    assert router.resolve("blind_reader", ModelTier.BALANCED) == "gpt-5.6-sol"


def test_a_pin_still_wins_over_the_operators_own_wildcard():
    """What the panel promises in as many words: anything pinned below still
    wins."""
    overrides = _resolve_overrides(
        PRESETS["maximum"], _campaign({"*": "gpt-5.6-sol", "conversion_critic": "opus"})
    )
    router = ModelRouter(overrides)

    assert router.resolve("conversion_critic", ModelTier.DEEP) == "opus"
    assert router.resolve("email_writer", ModelTier.DEEP) == "gpt-5.6-sol"


def test_no_operator_choice_leaves_the_preset_exactly_as_it_was():
    assert _resolve_overrides(PRESETS["fast"], _campaign(None)) == PRESETS["fast"].model_overrides


def test_the_presets_own_wildcard_is_not_disturbed_by_a_pin():
    """`fast` uses a wildcard itself. A single pin on top of it must not wipe
    the preset's blanket choice for every other role."""
    overrides = _resolve_overrides(PRESETS["fast"], _campaign({"email_writer": "fable5"}))
    router = ModelRouter(overrides)

    assert router.resolve("email_writer", ModelTier.DEEP) == "fable5"
    assert router.resolve("strategist", ModelTier.DEEP) == "sonnet"
