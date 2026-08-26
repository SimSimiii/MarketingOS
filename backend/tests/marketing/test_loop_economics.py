"""What a run is allowed to spend, pinned.

These are budget tests: they assert call counts and routing rather than copy
quality. They exist because every cost regression in this system so far has
been invisible at the level of "does the campaign still work" - a preset that
re-prices reactions as judgment, or a judge bought after the outcome is
already decided, produces exactly the same emails and a much larger bill.
"""

from dataclasses import replace

import pytest

from app.ai.model_router import ModelTier
from app.marketing.craft import EmailVersion, better_of
from app.marketing.email_copy import Email
from app.marketing.gates import GateIssue, GateReport, GateSeverity
from app.marketing.policy import PRESETS
from app.marketing.reader import BlindRead, PanelRead
from app.marketing.request import CampaignRequest
from tests.marketing.conftest import (
    READ_FAIL,
    RoleScriptedProvider,
    blind_read,
    campaign_brief,
)
from tests.marketing.test_pipeline import build, refine_only


def _version(
    attempt: int,
    pull: float,
    *,
    blocking: bool = False,
    critique: str | None = None,
    skipped: bool = False,
) -> EmailVersion:
    from app.marketing.critic import Critique

    gates = GateReport(
        issues=(
            [GateIssue(gate="evidence", detail="unsupported", severity=GateSeverity.BLOCKING)]
            if blocking
            else []
        )
    )
    return EmailVersion(
        attempt=attempt,
        email=Email(
            position=1,
            subject=f"attempt {attempt}",
            preview_text="p",
            greeting="Hi there,",
            body="b",
            call_to_action="Go",
            sign_off="- us",
        ),
        gates=gates,
        read=PanelRead(reads=[BlindRead(opened=True, pull=int(pull), would_act=pull >= 7)]),
        critique=Critique(verdict=critique) if critique else None,
        critic_skipped=skipped,
    )


# ------------------------------------------------------- choosing a version


def test_an_uncritiqued_version_cannot_win_on_a_point_it_never_earned():
    """The final attempt goes uncritiqued to save a deep-tier call. If a
    missing critique scored as approval, a draft nobody vetted would beat one
    the critic had explicitly sent back - buying the saving with the wrong
    email."""
    sent_back = _version(1, pull=6, critique="revise")
    never_asked = _version(2, pull=6, skipped=True)

    assert better_of(sent_back, never_asked) is sent_back
    assert better_of(never_asked, sent_back) is sent_back


def test_an_uncritiqued_version_still_wins_on_the_readers_verdict():
    """With the critic out of the comparison, the question falls through to
    the one the whole loop exists to move."""
    approved_but_flat = _version(1, pull=4, critique="ship")
    unjudged_but_wanted = _version(2, pull=9, skipped=True)

    assert better_of(approved_but_flat, unjudged_but_wanted) is unjudged_but_wanted


def test_a_blocked_email_never_wins_however_well_it_reads():
    assert better_of(_version(1, pull=10, blocking=True), _version(2, pull=3)).attempt == 2


def test_the_critic_decides_between_two_versions_it_actually_judged():
    approved = _version(1, pull=6, critique="ship")
    rejected = _version(2, pull=6, critique="revise")

    assert better_of(rejected, approved) is approved


def test_a_tie_goes_to_the_version_that_already_worked():
    assert better_of(_version(1, pull=7), _version(2, pull=7)).attempt == 1


# --------------------------------------------------------------- call counts


@pytest.mark.asyncio
async def test_the_critic_is_not_bought_after_the_outcome_is_decided(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    """A draft that never lands exhausts its rewrites. The critique on the
    last attempt is a deep-tier call whose entire output is edits for a
    rewrite that will not happen.

    Each read is better than the last so the loop keeps going - a flat score
    would trip the stop-early rule and never reach the final attempt.

    The saving is an ordering, not a rule: the critic is bought *after* the
    loop knows a rewrite will follow. It used to be bought before, so on the
    attempt where the loop then stopped, a deep-tier call had already been
    spent producing edits for a pass that never happened."""
    provider.set_default("strategist", campaign_brief(1))
    provider.push(
        "blind_reader",
        blind_read(pull=3, would_act=False),
        blind_read(pull=5, would_act=False),
        blind_read(pull=6, would_act=False),
    )
    one_email = replace(request_fixture, request="Write me 1 email that sells my app")

    pipeline, _ = build(provider, refine_only(max_revisions=2))
    await pipeline.run(one_email)

    # Three attempts, three cold reads - and one fewer critique than attempts.
    assert provider.calls_by_role["email_writer"] == 3
    assert provider.calls_by_role["blind_reader"] == 3
    assert provider.calls_by_role["conversion_critic"] == 2


@pytest.mark.asyncio
async def test_a_run_that_cannot_rewrite_at_all_still_critiques_once(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    """The saving must not silently remove the critic from a run configured
    for no rewrites - the critique is also the record of why an email is the
    way it is, and there would be none at all."""
    provider.set_default("strategist", campaign_brief(1))
    provider.set_default("blind_reader", READ_FAIL)
    one_email = replace(request_fixture, request="Write me 1 email that sells my app")

    pipeline, _ = build(
        provider,
        PRESETS["balanced"].model_copy(update={"max_revisions": 0, "draft_candidates": 1}),
    )
    await pipeline.run(one_email)

    assert provider.calls_by_role["conversion_critic"] == 1


@pytest.mark.asyncio
async def test_the_panel_reads_the_same_draft_concurrently(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    """Three readers, one draft, no reader seeing another's report - so they
    have no reason to be waited for one at a time."""
    provider.set_default("strategist", campaign_brief(1))
    one_email = replace(request_fixture, request="Write me 1 email that sells my app")

    pipeline, _ = build(
        provider,
        PRESETS["balanced"].model_copy(
            update={"reader_panel": True, "draft_candidates": 1, "max_revisions": 0}
        ),
    )
    await pipeline.run(one_email)

    assert provider.calls_by_role["blind_reader"] == 3
    concurrent = provider.max_concurrent_by_role["blind_reader"]
    assert concurrent == 3, f"the panel read one at a time ({concurrent} in flight at once)"


# ------------------------------------------------------------------ routing


def test_the_strongest_preset_does_not_reprice_the_cold_reader():
    """21 of 38 calls in a measured maximum run were cold reads. A cold read
    is a reaction, which is why the role asks for BALANCED - and a blanket
    preset override used to overrule that."""
    from app.ai.model_router import ModelRouter

    router = ModelRouter(PRESETS["maximum"].model_overrides)

    assert router.resolve("blind_reader", ModelTier.BALANCED) == "sonnet"
    assert router.resolve("email_writer", ModelTier.DEEP) == "opus"


def test_every_deep_role_is_named_in_the_strongest_preset():
    """The preset lists roles by hand, so a role added later would silently
    keep the default model. This is the reminder."""
    from app.marketing.critic import ROLE_ID as CRITIC
    from app.marketing.sequence import ROLE_ID as SEQUENCE
    from app.marketing.strategist import ROLE_ID as STRATEGIST
    from app.marketing.writer import ROLE_ID as WRITER

    overrides = PRESETS["maximum"].model_overrides
    for role in (STRATEGIST, WRITER, CRITIC, SEQUENCE):
        assert overrides.get(role) == "opus", role
