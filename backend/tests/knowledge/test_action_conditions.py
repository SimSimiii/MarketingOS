import json

import pytest

from app.knowledge.artifacts import CallToAction, Plan
from app.knowledge.ledger import Evidence, EvidenceContext, EvidenceKind, EvidenceStrength
from app.marketing.request import CampaignRequest
from tests.marketing.conftest import (
    CRITIQUE_SHIP,
    RoleScriptedProvider,
    artifacts_fixture,
    campaign_brief,
    default_answers,
)
from tests.marketing.test_pipeline import build, refine_only


def term(id_, subject="Notewright Free plan", **overrides):
    return Evidence(
        id=id_, kind=EvidenceKind.FEATURE, claim=f"Plan condition {id_}",
        verbatim=f"Plan condition {id_}.", source="https://notewright.example/plans",
        strength=overrides.pop("strength", EvidenceStrength.STRONG),
        context=EvidenceContext(
            subject=subject, source_kind=overrides.pop("source_kind", "official_documentation"),
            claim_scope=overrides.pop("claim_scope", "offer"),
            conditions="Applies to the named plan", limitations="Not a response guarantee",
        ), **overrides,
    )


@pytest.mark.parametrize("action,expected", [
    ("Start for free", ["free", "moderate"]), ("Choose Pro", ["pro"]),
    ("Compare Free and Pro", []), ("Start trial", []), ("Build freeform pages", []),
])
def test_action_terms_require_an_unambiguous_plan_and_owned_licensed_scope(action, expected):
    current = artifacts_fixture()
    current.offer.plans = [Plan(name="Free"), Plan(name="Pro")]
    current.evidence.entries.extend([
        term("free"), term("pro", subject="Notewright Pro plan"),
        term("moderate", strength=EvidenceStrength.MODERATE),
        term("free_service", subject="Notewright free concierge migration"),
        term("rival", subject="AnotherVendor Free plan"),
        term("comparison", claim_scope="comparison"),
        term("vendor", source_kind="vendor_statement"),
        term("weak", strength=EvidenceStrength.WEAK),
        term("excluded"),
    ])

    result = current.conditions_for_action(action, excluded_ids={"excluded"})

    assert [entry.id for entry in result.entries] == expected


def test_action_terms_are_bounded_canonical_quotes_and_do_not_use_plan_summaries():
    current = artifacts_fixture()
    current.offer.plans = [Plan(name="Free", includes=["UNLICENSED_SUMMARY"])]
    facts = [term(f"free{index}") for index in range(9)]
    current.evidence.entries.extend(facts)

    result = current.conditions_for_action("Start for free")

    assert len(result.entries) == 6
    assert result.entries[0].model_dump() == facts[0].model_dump()
    assert "Applies to the named plan" in result.render()
    assert "Not a response guarantee" in result.render()
    assert "UNLICENSED_SUMMARY" not in result.render()


@pytest.mark.asyncio
async def test_active_offer_terms_reach_writer_and_critic_without_warming_the_reader():
    provider = RoleScriptedProvider(default_answers())
    current = artifacts_fixture()
    current.offer.plans = [Plan(name="Free")]
    current.offer.calls_to_action = [CallToAction(label="Start for free")]
    canonical = term("free_limit")
    current.evidence.entries.append(canonical)
    planned = json.loads(campaign_brief(1))
    planned["emails"][0]["call_to_action"] = "Start for free"
    provider.set_default("strategist", json.dumps(planned))
    provider.set_default("conversion_critic", CRITIQUE_SHIP)
    pipeline, _ = build(provider, refine_only(max_revisions=0), artifacts=current)

    await pipeline.run(CampaignRequest(name="Acquisition", request="Write exactly one acquisition email"))

    for role in ("email_writer", "conversion_critic"):
        task = provider.requests_for(role)[0].messages[0].content
        assert "Applicable plan conditions for this CTA" in task
        assert canonical.verbatim in task
        assert canonical.context.conditions in task
    assert all(canonical.verbatim not in (call.system_prompt or "")
               for call in provider.requests_for("blind_reader"))
    assert provider.calls_by_role["email_writer"] == 1
    assert provider.calls_by_role["conversion_critic"] == 1
