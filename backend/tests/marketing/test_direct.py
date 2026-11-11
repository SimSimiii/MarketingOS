from dataclasses import replace

import pytest

from app.knowledge.artifacts import CallToAction
from app.knowledge.corpus import Document
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
async def test_direct_buys_a_source_review_even_when_reader_does_not_like_it(read):
    request, artifacts, policy = inputs()
    provider = RoleScriptedProvider({"email_writer": email_draft(), "blind_reader": read})
    result = await EmailCampaignPipeline(session=make_session(provider),
        knowledge=FakeKnowledgeGateway(compiled=artifacts), policy=policy).run(request)
    assert len(result.emails) == 1
    assert result.brief.strategy_mode == "direct"
    assert result.brief.emails[0].next_step_url == "https://example.com/start"
    assert dict(provider.calls_by_role) == {"email_writer": 1, "claim_reviewer": 1, "blind_reader": 1}
    estimate = forecast(policy, parse_contract(request.request), knowledge_reused=True, direct_eligible=True)
    assert estimate.low == 3 and estimate.high == 4
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
    provider.review("The claimed 987 hours saved each week has no source.")
    result = await EmailCampaignPipeline(session=make_session(provider),
        knowledge=FakeKnowledgeGateway(compiled=artifacts), policy=policy).run(request)
    assert not result.emails
    assert result.status == "failed"


def test_unknown_compilation_keeps_a_conservative_forecast():
    request, _, policy = inputs()
    estimate = forecast(policy, parse_contract(request.request), material_chars=1000, direct_eligible=None)
    assert estimate.low == estimate.compile_low + 3
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


@pytest.mark.asyncio
@pytest.mark.parametrize("repair", [False, True])
async def test_focused_activation_writes_and_checks_once_with_one_optional_repair(repair):
    request, artifacts, policy = inputs()
    request = replace(request, cta_url="https://example.com/start")
    provider = RoleScriptedProvider({"email_writer": email_draft()})
    if repair:
        provider.review("The free-tier promise is unsupported.", "")
        provider.push("email_writer", email_draft(), email_draft().replace(
            "PS: The free tier stays free after the trial ends.\n", "",
        ))
    result = await EmailCampaignPipeline(
        session=make_session(provider), knowledge=FakeKnowledgeGateway(compiled=artifacts), policy=policy,
    ).run(request)
    assert result.status == "completed", result.abort_reason
    assert not result.report.reads_expected
    count = 2 if repair else 1
    assert dict(provider.calls_by_role) == {"email_writer": count, "claim_reviewer": count}
    assert result.outcomes[0].best.gates.semantic_review["approved"]
    assert result.outcomes[0].best.attempt == count


@pytest.mark.asyncio
@pytest.mark.parametrize("supported", [False, True])
async def test_required_fact_is_checked_before_the_writer_and_carries_its_source(supported):
    request, artifacts, policy = inputs()
    url = "https://docs.example.com/import"
    quote = "Trial workspaces can import CSV files."
    request = replace(
        request, cta_url="https://example.com/start", product_url="https://example.com",
        intent=request.intent.model_copy(update={
            "required_fact": "Can trial workspaces import CSV files?", "required_source_url": url,
        }),
    )
    knowledge = FakeKnowledgeGateway(
        compiled=artifacts, documents=[Document(id="docs", title="CSV import", source=url, content=quote)],
    )
    answer = ('{"claims":[{"source_id":"S1","kind":"feature","claim":"' + quote
              + '","verbatim":"' + quote + '"}],"note":""}') if supported else '{"claims":[],"note":"Trial eligibility is missing."}'
    provider = RoleScriptedProvider({"material_research_synthesis": answer, "email_writer": email_draft()})
    result = await EmailCampaignPipeline(session=make_session(provider), knowledge=knowledge, policy=policy).run(request)
    assert provider.requests[0].template == "material_research_synthesis"
    if supported:
        assert result.status == "completed", result.abort_reason
        assert result.brief.emails[0].evidence_ids == ["R1"]
        assert result.artifacts.evidence.get("R1").source == url
    else:
        assert "Trial eligibility is missing." in result.abort_reason
        assert dict(provider.calls_by_role) == {"material_researcher": 1}
