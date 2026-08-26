"""The forecast, checked against runs that actually happened.

An estimator validated only against its own unit tests drifts the first time
the loop changes shape, silently - and an estimate nobody can trust is worse
than no estimate at all, because it gets quoted back as though somebody had
measured it.

So these run the real pipeline against a scripted provider, count the calls it
made, and assert the forecast contained them. Every preset, at one email and
at several, on a run where the copy lands first time and on a run where every
rewrite is bought. If the craft loop gains a step, one of these fails.
"""

import pytest

from app.knowledge.compiler import _EVIDENCE_BATCH_CHARS as COMPILER_BATCH_CHARS
from app.marketing.contract import parse_contract
from app.marketing.forecast import (
    _EVIDENCE_BATCH_CHARS,
    Forecast,
    compile_forecast,
    forecast,
)
from app.marketing.policy import PRESETS, ExecutionPolicy, PolicyPreset
from app.marketing.request import CampaignRequest
from tests.marketing.conftest import (
    CRITIQUE_REVISE,
    READ_FAIL,
    RoleScriptedProvider,
    campaign_brief,
    default_answers,
)
from tests.marketing.test_pipeline import build

PRESET_NAMES: tuple[PolicyPreset, ...] = ("fast", "balanced", "maximum")


def request_for(count: int) -> CampaignRequest:
    return CampaignRequest(
        name="Launch",
        request=f"Write me {count} emails that make people buy my note-taking app",
        product_description="A note-taking app for developers",
    )


async def calls_made(preset: PolicyPreset, count: int, rewriting: bool) -> int:
    provider = RoleScriptedProvider(default_answers())
    provider.set_default("strategist", campaign_brief(count))
    if rewriting:
        # Nothing lands and the critic sends everything back, so the loop buys
        # every rewrite the policy allows.
        provider.set_default("blind_reader", READ_FAIL)
        provider.set_default("conversion_critic", CRITIQUE_REVISE)
    pipeline, _ = build(provider, PRESETS[preset])
    await pipeline.run(request_for(count))
    return sum(provider.calls_by_role.values())


@pytest.mark.parametrize("preset", PRESET_NAMES)
@pytest.mark.parametrize("count", [1, 3])
@pytest.mark.parametrize("rewriting", [False, True], ids=["lands-first", "rewriting"])
@pytest.mark.asyncio
async def test_a_real_run_lands_inside_its_own_forecast(
    preset: PolicyPreset, count: int, rewriting: bool
):
    made = await calls_made(preset, count, rewriting)
    estimate = forecast(
        PRESETS[preset], parse_contract(request_for(count).request), knowledge_reused=True
    )

    assert estimate.low <= made <= estimate.high, (
        f"{preset} at {count} email(s) made {made} calls, forecast {estimate.render()}"
    )


@pytest.mark.parametrize("preset", PRESET_NAMES)
@pytest.mark.asyncio
async def test_the_floor_is_a_floor_and_the_ceiling_is_a_ceiling(preset: PolicyPreset):
    """Both ends have to be reachable or the range is decoration.

    A floor no run ever gets near says nothing about a good run, and a ceiling
    a bad run sails past is the estimate that costs somebody money.
    """
    landed = await calls_made(preset, 3, rewriting=False)
    reworked = await calls_made(preset, 3, rewriting=True)
    estimate = forecast(
        PRESETS[preset], parse_contract(request_for(3).request), knowledge_reused=True
    )

    assert reworked > landed, "the rewriting run has to actually buy more"
    assert estimate.low <= landed
    assert reworked <= estimate.high


def test_reading_the_material_is_priced_and_reusing_it_is_free():
    """The largest saving in the system, and the one nobody knows about: a
    second campaign for the same business reads none of it again."""
    policy = PRESETS["balanced"]
    fresh = compile_forecast(policy, material_chars=40_000, reused=False)
    again = compile_forecast(policy, material_chars=40_000, reused=True)

    assert fresh.low == fresh.high, "reading is fixed work - there is nothing to vary"
    assert fresh.compile_low == fresh.low
    assert again.low == 0


def test_a_longer_site_costs_more_readings_not_a_longer_prompt():
    """The evidence pass reads a long document in several passes rather than
    truncating it, so material length shows up in the estimate."""
    policy = PRESETS["balanced"]
    small = compile_forecast(policy, material_chars=5_000, reused=False)
    large = compile_forecast(policy, material_chars=5 * _EVIDENCE_BATCH_CHARS, reused=False)

    assert large.low - small.low == 4


def test_the_batch_size_matches_the_compiler_that_actually_reads():
    """A forecast built on a stale constant is a forecast about a different
    program. Asserted rather than imported into the estimator, because that
    import would be a cycle."""
    assert _EVIDENCE_BATCH_CHARS == COMPILER_BATCH_CHARS


def test_a_cheaper_preset_forecasts_cheaper():
    """The whole point of showing this next to the picker. If the ordering
    ever inverts, the number is worse than useless - it is misleading."""
    contract = parse_contract(request_for(3).request)
    fast, balanced, maximum = (
        forecast(PRESETS[preset], contract, knowledge_reused=True) for preset in PRESET_NAMES
    )

    assert fast.high < balanced.high < maximum.high
    assert fast.low < balanced.low <= maximum.low


def test_a_request_with_no_number_is_still_forecast_on_the_working_assumption():
    contract = parse_contract("Write me an onboarding campaign")
    assert not contract.count_is_explicit
    assert forecast(PRESETS["balanced"], contract, knowledge_reused=True).low > 0


def test_forecasts_add_up():
    total = Forecast(low=1, high=2, compile_low=1, compile_high=1) + Forecast(low=3, high=4)
    assert total == Forecast(low=4, high=6, compile_low=1, compile_high=1)


def test_switching_off_a_judge_shows_up_in_the_estimate():
    """A custom policy has to move the number too - the presets are three
    points on a dial the user can also turn by hand."""
    contract = parse_contract(request_for(2).request)
    with_judges = forecast(PRESETS["balanced"], contract, knowledge_reused=True)
    without: ExecutionPolicy = PRESETS["balanced"].model_copy(
        update={"tournament": False, "critic_enabled": False, "subject_variants": 0}
    )

    assert forecast(without, contract, knowledge_reused=True).high < with_judges.high


def test_a_single_email_never_pays_for_a_sequence_pass():
    """A sequence of one is not a sequence and the pipeline skips the pass
    entirely, so quoting it would charge for work that cannot happen."""
    policy = PRESETS["balanced"]
    one = forecast(policy, parse_contract("Write me one email"), knowledge_reused=True)
    two = forecast(policy, parse_contract("Write me 2 emails"), knowledge_reused=True)
    three = forecast(policy, parse_contract("Write me 3 emails"), knowledge_reused=True)

    assert two.low - one.low > three.low - two.low, (
        "the second email brings the whole-sequence read with it; the third does not"
    )


def test_the_estimate_is_read_from_the_request_this_campaign_actually_made():
    """It has to move with what the user typed, or it is a property of the
    preset rather than of this campaign."""
    policy = PRESETS["balanced"]
    one = forecast(policy, parse_contract("Write me 1 email"), knowledge_reused=True)
    five = forecast(
        policy, parse_contract("Write me a five-email onboarding sequence"), knowledge_reused=True
    )

    assert five.low > one.low
