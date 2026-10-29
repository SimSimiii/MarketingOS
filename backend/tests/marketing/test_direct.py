from dataclasses import replace

import pytest

from app.knowledge.artifacts import CallToAction
from app.marketing.contract import parse_contract
from app.marketing.direct import direct_brief
from app.marketing.forecast import forecast
from app.marketing.intent import CampaignIntent
from app.marketing.pipeline import EmailCampaignPipeline
from app.marketing.policy import PRESETS
from app.marketing.request import CampaignRequest
from tests.marketing.conftest import (
    READ_FAIL,
    READ_PASS,
    FakeKnowledgeGateway,
    RoleScriptedProvider,
    artifacts_fixture,
    email_draft,
    make_session,
)


def inputs():
    request = CampaignRequest(name="Activate", request="Write exactly one activation email",
                              intent=CampaignIntent(objective="activation", reader_relationship="customer"))
    artifacts = artifacts_fixture()
    artifacts.offer.calls_to_action = [CallToAction(label="Start the trial", url="https://example.com/start")]
    policy = PRESETS["balanced"].model_copy(update={"strategy_mode": "auto"})
    return request, artifacts, policy


@pytest.mark.parametrize("read", [READ_PASS, READ_FAIL])
@pytest.mark.asyncio
async def test_direct_uses_two_calls_even_when_reader_does_not_like_it(read):
    request, artifacts, policy = inputs()
    provider = RoleScriptedProvider({"email_writer": email_draft(), "blind_reader": read})
    result = await EmailCampaignPipeline(session=make_session(provider),
        knowledge=FakeKnowledgeGateway(compiled=artifacts), policy=policy).run(request)
    assert len(result.emails) == 1
    assert result.brief.strategy_mode == "direct"
    assert result.brief.emails[0].next_step_url == "https://example.com/start"
    assert dict(provider.calls_by_role) == {"email_writer": 1, "blind_reader": 1}
    estimate = forecast(policy, parse_contract(request.request), knowledge_reused=True, direct_eligible=True)
    assert estimate.low == estimate.high == 2
    if read == READ_FAIL:
        assert result.status == "degraded"


def test_ambiguous_action_never_uses_list_order_and_fixed_destination_must_match():
    request, artifacts, policy = inputs()
    artifacts.offer.calls_to_action.append(CallToAction(label="Read docs", url="https://example.com/docs"))
    assert direct_brief(request, artifacts, parse_contract(request.request), policy) is None
    chosen = direct_brief(replace(request, cta_url="https://example.com/docs"), artifacts,
                          parse_contract(request.request), policy)
    assert chosen.emails[0].call_to_action == "Read docs"
    assert direct_brief(replace(request, cta_url="https://unlicensed.example"), artifacts,
                        parse_contract(request.request), policy) is None


@pytest.mark.parametrize("change", [
    {"request": "Write exactly two activation emails"},
    {"intent": CampaignIntent(objective="acquisition")},
    {"intent": None},
])
def test_auto_preserves_planning_for_complex_or_legacy_jobs(change):
    request, artifacts, policy = inputs()
    request = replace(request, **change)
    assert direct_brief(request, artifacts, parse_contract(request.request), policy) is None


@pytest.mark.asyncio
async def test_direct_still_blocks_unlicensed_numbers():
    request, artifacts, policy = inputs()
    provider = RoleScriptedProvider({"email_writer": email_draft(body="Notewright writes release notes and saves 987 hours each week."), "blind_reader": READ_PASS})
    result = await EmailCampaignPipeline(session=make_session(provider),
        knowledge=FakeKnowledgeGateway(compiled=artifacts), policy=policy).run(request)
    assert not result.emails
    assert result.status == "failed"


def test_unknown_compilation_keeps_a_conservative_forecast():
    request, _, policy = inputs()
    estimate = forecast(policy, parse_contract(request.request), material_chars=1000, direct_eligible=None)
    assert estimate.low == estimate.compile_low + 2
    assert estimate.high > estimate.low


def test_direct_requires_agreement_with_user_action_and_a_destination():
    request, artifacts, policy = inputs()
    request = replace(request, intent=request.intent.model_copy(update={"desired_action": "Read pricing"}))
    assert direct_brief(request, artifacts, parse_contract(request.request), policy) is None
    request = replace(request, intent=request.intent.model_copy(update={"desired_action": "Start the trial"}))
    assert direct_brief(request, artifacts, parse_contract(request.request), policy) is not None
    artifacts.offer.calls_to_action[0].url = None
    assert direct_brief(request, artifacts, parse_contract(request.request), policy) is None


def test_reused_action_id_with_conflicting_destinations_is_ambiguous():
    request, artifacts, policy = inputs()
    artifacts.offer.calls_to_action[0].id = "duplicated"
    artifacts.offer.calls_to_action.append(CallToAction(id="duplicated", label="Start the trial", url="https://example.com/other"))
    assert direct_brief(request, artifacts, parse_contract(request.request), policy) is None
