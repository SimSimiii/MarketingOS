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
    assert fast.tournament is False and maximum.tournament is True
    assert fast.subject_variants < maximum.subject_variants
    assert fast.sequence_pass is False and maximum.sequence_pass is True
    assert fast.max_duration_seconds < maximum.max_duration_seconds
    assert fast.max_total_tokens < maximum.max_total_tokens


def test_the_default_preset_can_tell_two_drafts_apart():
    """The measurement that everything else is read off. Balanced ran with one
    cold reader and no side-by-side comparison, so "did this rewrite help" was
    one absolute score against another - and in a measured run three openings
    and a rewrite all came back at 2/10, which is the instrument failing rather
    than four drafts being identical."""
    balanced = PRESETS["balanced"]

    assert balanced.reader_panel is True, "one reader is one sample of a stochastic judge"
    assert balanced.tournament is True
    assert balanced.draft_candidates > 1


def test_the_default_preset_optimises_the_line_most_recipients_only_see():
    assert PRESETS["balanced"].subject_variants > 0


def test_only_fast_will_write_from_material_that_proves_nothing():
    """Everywhere else the run stops and asks. `fast` is the preset for
    someone who wants a draft in four minutes and has accepted what that
    means."""
    assert PRESETS["fast"].require_proof is False
    assert PRESETS["balanced"].require_proof is True
    assert PRESETS["maximum"].require_proof is True


def test_every_preset_defaults_to_the_model_that_cleared_the_sellable_bar():
    """Preset pricing comes from call count rather than weaker default models."""
    for preset in PRESETS.values():
        router = ModelRouter(preset.model_overrides)
        assert router.resolve("email_writer", ModelTier.DEEP) == "gpt-5.6-sol"
        assert router.resolve("blind_reader", ModelTier.BALANCED) == "gpt-5.6-sol"
        assert router.resolve("knowledge_compiler", ModelTier.FAST) == "gpt-5.6-sol"


def test_a_user_can_still_put_a_whole_run_on_one_model():
    """An operator wildcard can still replace the preset's validated default."""
    router = ModelRouter({**PRESETS["maximum"].model_overrides, "*": "haiku"})

    assert router.resolve("blind_reader", ModelTier.BALANCED) == "haiku"
    assert router.resolve("email_writer", ModelTier.DEEP) == "haiku"


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
