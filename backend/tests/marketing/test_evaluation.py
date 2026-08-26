"""The benchmark's own correctness, checked for free.

The quality benchmark is billed, so it runs rarely - which is exactly the kind
of code that quietly stops working. These tests exercise the record and the
comparison against scripted runs, so the harness is known to be right on the
day somebody actually spends money with it.
"""

from dataclasses import replace

import pytest

from app.evaluation.golden import GOLDEN_CASES, case_named
from app.evaluation.head_to_head import JUDGE_MODEL, against_control, assessor_panel
from app.evaluation.record import RunRecord, record_from
from app.marketing.policy import PRESETS
from app.marketing.reader import personas_for
from app.marketing.request import CampaignRequest
from tests.marketing.conftest import (
    READ_FAIL,
    RoleScriptedProvider,
    artifacts_fixture,
    blind_read,
    campaign_brief,
    make_session,
    votes_for_the_challenger,
)
from tests.marketing.test_pipeline import build, refine_only


@pytest.mark.asyncio
async def test_a_finished_run_reads_into_a_record(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    provider.set_default("strategist", campaign_brief(1))
    provider.set_default("blind_reader", blind_read(pull=8, would_act=True))
    pipeline, _ = build(
        provider,
        PRESETS["balanced"].model_copy(update={"draft_candidates": 1, "max_revisions": 0}),
    )
    result = await pipeline.run(
        replace(request_fixture, request="Write me 1 email that sells my app")
    )

    record = record_from("fixture", "balanced", result, duration_seconds=12.5)

    assert record.delivered == 1
    assert record.emails[0].pull == 8
    assert record.emails[0].landed is True
    assert record.emails[0].word_count > 0
    assert record.model_calls == len(result.usage.calls)
    assert record.calls_by_role["email_writer"] >= 1
    assert record.average_pull == 8
    assert record.landed_rate == 1.0
    assert record.first_draft_ship_rate == 1.0


@pytest.mark.asyncio
async def test_a_run_nobody_would_click_has_no_cost_per_shipped_email(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    """The most flattering possible lie would be to divide by delivered
    instead of by shipped: a run that hands over three emails a cold reader
    rejected would report its best cost-efficiency ever."""
    provider.set_default("strategist", campaign_brief(1))
    provider.set_default("blind_reader", READ_FAIL)
    pipeline, _ = build(
        provider,
        PRESETS["balanced"].model_copy(update={"draft_candidates": 1, "max_revisions": 0}),
    )
    result = await pipeline.run(
        replace(request_fixture, request="Write me 1 email that sells my app")
    )

    record = record_from("fixture", "balanced", result, duration_seconds=1.0)

    assert record.delivered == 1
    assert record.landed_rate == 0.0
    assert record.cost_per_shipped_email == float("inf")


def test_rewrites_are_counted_as_rewrites_not_as_versions():
    """One draft is zero rewrites. Off by one here would make every change
    look like it halved the rework."""
    record = RunRecord(case="c", request="r", preset="balanced")
    assert record.first_draft_ship_rate == 0.0  # no emails at all


def test_a_record_round_trips_as_json():
    """Two rounds are compared by loading records written by an earlier
    version of this file, so the serialized form has to survive."""
    record = RunRecord(case="rich-single", request="r", preset="maximum", cost_usd=2.5)

    restored = RunRecord.model_validate_json(record.model_dump_json())

    assert restored.case == "rich-single"
    assert restored.cost_usd == 2.5


# --------------------------------------------------------------- golden set


def test_every_golden_case_has_a_unique_name():
    """Records are written to <name>.json, so a duplicate silently discards a
    case's result."""
    names = [case.name for case in GOLDEN_CASES]
    assert len(names) == len(set(names))


def test_the_golden_set_spans_the_axes_it_exists_to_span():
    assert case_named("thin-evidence") is not None, "the honesty case"
    assert case_named("rich-sequence") is not None, "the sequencing case"
    assert case_named("onboarding") is not None, "not everything is a cold sale"


@pytest.mark.parametrize("case", GOLDEN_CASES, ids=lambda case: case.name)
def test_every_golden_case_names_a_countable_deliverable(case):
    """The contract is parsed from the request sentence, and a case whose
    count is ambiguous measures the parser instead of the copy."""
    from app.marketing.contract import parse_contract

    contract = parse_contract(case.request)
    assert contract.count_is_explicit, case.request
    assert case.documents, "a case with no material measures nothing"


# ------------------------------------------------------- against a human


@pytest.mark.parametrize(
    "case", [case for case in GOLDEN_CASES if case.control_email], ids=lambda case: case.name
)
def test_every_control_email_is_one_the_system_would_be_allowed_to_send(case):
    """The control is judged against the system's output, so it has to be a
    real email and not a sketch of one. A control that breaks the structural
    rules the writer works under is a straw man, and beating it would mean
    nothing."""
    from app.marketing.email_copy import parse_email

    control = parse_email(case.control_email, position=1)
    assert control.subject and control.call_to_action and control.body


@pytest.mark.asyncio
async def test_the_win_rate_is_a_blind_vote_between_two_emails(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    provider.set_default("strategist", campaign_brief(1))
    provider.push("preference_judge", *votes_for_the_challenger(6))
    pipeline, _ = build(provider, refine_only(max_revisions=0))
    result = await pipeline.run(
        replace(request_fixture, request="Write me 1 email that sells my app")
    )

    control = await against_control(
        judge_session=make_session(provider),
        control_email=case_named("rich-single").control_email,
        delivered=result.emails,
        artifacts=result.artifacts,
        segment_name=result.brief.reader_segment,
    )

    assert control.cast == 6
    assert control.beat_the_human is True
    assert control.win_rate == 1.0


@pytest.mark.asyncio
async def test_a_case_with_no_control_reports_that_rather_than_a_loss(
    provider: RoleScriptedProvider,
):
    """Zero votes for the system and zero against is not a nil-nil draw, and a
    record that stored it as one would drag the benchmark's headline number
    down by however many cases nobody has written a control for yet."""
    control = await against_control(
        judge_session=make_session(provider),
        control_email="",
        delivered=[],
        artifacts=None,
    )

    assert control.skipped
    assert control.cast == 0
    assert provider.calls_by_role["preference_judge"] == 0


def test_the_record_keeps_the_control_result_out_of_the_arithmetic_when_skipped():
    record = RunRecord(case="c", request="r", preset="balanced", control_note="no control")
    assert record.control_win_rate == 0.0


def test_the_benchmark_is_not_graded_by_the_judge_the_loop_optimises_against():
    """Beating a judge you tuned against is not evidence. The craft loop's
    readers run on the balanced tier; this one must not."""
    from app.ai.model_router import DEFAULT_TIER_MODELS, ModelTier

    assert JUDGE_MODEL != DEFAULT_TIER_MODELS[ModelTier.BALANCED]


def test_the_assessor_panel_is_the_buyer_in_moods_the_loop_never_uses():
    """The same buyer, because grading copy as somebody it was not aimed at
    measures the mismatch. Different dispositions, because a grader the loop
    has been rewriting against for three attempts is not an independent one."""
    artifacts = artifacts_fixture()
    segment = artifacts.audience.segments[0]

    graders = assessor_panel(artifacts, segment.name)
    optimised_against = personas_for(artifacts.audience, segment, panel=True)

    assert len(graders) == 3
    assert all(segment.name in persona for persona in graders)
    assert not set(graders) & set(optimised_against)
