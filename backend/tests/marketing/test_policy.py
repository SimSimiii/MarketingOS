from app.ai.model_router import ModelRouter, ModelTier
from app.marketing.policy import PRESETS, ExecutionPolicy, resolve_policy


def test_balanced_is_the_default():
    assert resolve_policy(None) == PRESETS["balanced"]


def test_the_presets_trade_judgment_calls_per_email_for_speed():
    """What a preset buys is passes over the copy, not a "creativity" dial."""
    fast, maximum = PRESETS["fast"], PRESETS["maximum"]

    assert fast.max_revisions < maximum.max_revisions
    assert fast.critic_enabled is False and maximum.critic_enabled is True
    assert fast.reader_panel is False and maximum.reader_panel is True
    assert fast.sequence_pass is False and maximum.sequence_pass is True
    assert fast.max_duration_seconds < maximum.max_duration_seconds
    assert fast.max_total_tokens < maximum.max_total_tokens


def test_maximum_buys_more_judgment_without_repricing_reactions():
    """`maximum` used to say `{"*": "opus"}`, and a blanket override beats the
    tier map outright - so the cold reader, which asks for BALANCED because a
    cold read is a reaction rather than a deliberation, ran on opus. In a
    measured run it made 21 of 38 calls and was the largest line on the bill.

    What the preset should widen is how much judgment is bought, not what a
    reaction is charged at."""
    router = ModelRouter(PRESETS["maximum"].model_overrides)

    assert router.resolve("email_writer", ModelTier.DEEP) == "opus"
    assert router.resolve("strategist", ModelTier.DEEP) == "opus"
    assert router.resolve("conversion_critic", ModelTier.DEEP) == "opus"
    assert router.resolve("sequence_reviewer", ModelTier.DEEP) == "opus"
    # ...and the roles that ask for a cheaper tier still get it.
    assert router.resolve("blind_reader", ModelTier.BALANCED) == "sonnet"
    assert router.resolve("knowledge_compiler", ModelTier.BALANCED) == "sonnet"


def test_a_user_can_still_put_a_whole_run_on_one_model():
    """Removing the preset's blanket override must not remove the ability to
    ask for one - a campaign's own model_overrides still take a `*`."""
    router = ModelRouter({**PRESETS["maximum"].model_overrides, "*": "haiku"})

    assert router.resolve("blind_reader", ModelTier.BALANCED) == "haiku"
    # An exact role id is more specific than the wildcard, and still wins.
    assert router.resolve("email_writer", ModelTier.DEEP) == "opus"


def test_custom_overrides_win_field_by_field_over_the_preset():
    policy = resolve_policy("balanced", {"critic_enabled": False, "max_revisions": 0})

    assert policy.critic_enabled is False
    assert policy.max_revisions == 0
    # Untouched fields keep the preset's values.
    assert policy.sequence_pass == PRESETS["balanced"].sequence_pass


def test_unknown_override_keys_are_ignored_rather_than_crashing_a_run():
    """A campaign row can still carry policy fields from the old director's
    schema; a run must not die on one."""
    policy = resolve_policy("balanced", {"review_threshold": 9, "max_revisions": 1})
    assert policy.max_revisions == 1
    assert not hasattr(policy, "review_threshold")


def test_resolving_a_preset_never_mutates_the_shared_preset_instance():
    resolve_policy("fast", {"max_revisions": 4})
    assert PRESETS["fast"].max_revisions != 4


def test_merge_fields_default_to_what_email_tools_actually_fill():
    assert "first_name" in ExecutionPolicy().merge_fields
