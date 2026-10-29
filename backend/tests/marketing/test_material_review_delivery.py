"""A paid-run regression: desired previews must not erase grounded drafts."""
import json

import pytest

from app.knowledge.artifacts import BusinessProfile, CallToAction, KnowledgeArtifacts, OfferSheet
from app.knowledge.ledger import Evidence, EvidenceKind, EvidenceLedger
from app.marketing.pipeline import CampaignRunResult
from app.marketing.request import CampaignRequest
from tests.marketing.conftest import blind_read, campaign_brief, email_draft
from tests.marketing.test_pipeline import build, refine_only

GAP = (
    "The supplied material does not establish what poll invitees receive or whether "
    "they must create accounts, and it provides no pre-signup example."
)
BODY = (
    "When several people need to settle on a time, use a free SavvyCal meeting poll. "
    "Add candidate times, then invite everyone to vote on the options that work best for them.\n\n"
    "SavvyCal is online meeting scheduling software. Its meeting polls are free and ad-free.\n\n"
    "After creating an account, you can try the poll format for a conversation involving "
    "several people and decide whether collecting votes suits the meeting."
)


@pytest.mark.asyncio
@pytest.mark.parametrize("stepped", [False, True])
async def test_signup_preview_objection_keeps_the_draft_and_explicit_review(provider, stepped):
    artifacts = KnowledgeArtifacts(
        business=BusinessProfile(company_name="SavvyCal", what_it_does="online meeting scheduling software"),
        offer=OfferSheet(calls_to_action=[CallToAction(
            id="sign_up", label="Sign up for SavvyCal", url="https://savvycal.com/signup",
        )]),
        evidence=EvidenceLedger(entries=[
            Evidence(id="E63", kind=EvidenceKind.FEATURE,
                     claim="Meeting polls invite people to vote on suitable times.",
                     verbatim="Invite people to vote on times that work best for them.",
                     source="https://savvycal.com/features"),
            Evidence(id="E64", kind=EvidenceKind.FEATURE,
                     claim="Meeting polls are free and ad-free.",
                     verbatim="Free meeting polls, with no ads.", source="https://savvycal.com/features"),
        ]),
    )
    planned = json.loads(campaign_brief(1))
    planned["orientation"] = "SavvyCal is online meeting scheduling software."
    planned["emails"][0].update(
        evidence_ids=["E63", "E64"], next_step_evidence_ids=["E63", "E64"],
        action_id="sign_up", next_step_url="https://savvycal.com/signup",
        single_idea="Free, ad-free polls invite people to vote on suitable times.",
        call_to_action="Sign up for SavvyCal",
    )
    provider.set_default("strategist", json.dumps(planned))
    provider.set_default("email_writer", email_draft(
        subject="A free poll for meeting times", body=BODY, cta="Sign up for SavvyCal",
    ).replace("PS: The free tier stays free after the trial ends.", "PS:"))
    provider.set_default("blind_reader", blind_read(pull=8, would_act=True))
    provider.set_default("conversion_critic", json.dumps({
        "verdict":"revise", "failure_mode":"missing_material", "strategy_gap":GAP,
        "summary":"The reader would prefer to inspect the participant experience first.",
    }))
    pipeline, _ = build(provider, refine_only(max_revisions=0), artifacts=artifacts)
    request = CampaignRequest(name="Polls", request="Write exactly one acquisition email")
    if stepped:
        result = CampaignRunResult()
        contract = pipeline.read_contract(request)
        context, brief = await pipeline.plan(request, contract, result)
        outcome = await pipeline.craft_position(
            request=request, brief=brief, context=context, result=result, position=1, previous=[],
        )
        assert outcome is not None
        result.outcomes.append(outcome)
        result = await pipeline.conclude(
            request=request, contract=contract, brief=brief, context=context, result=result,
        )
    else:
        result = await pipeline.run(request)
    assert result.status == "degraded"
    assert result.report.delivered == result.report.promised == 1
    assert result.emails[0].body == BODY
    assert result.report.emails[0].clean
    assert not result.report.emails[0].landed
    assert any(GAP in issue for issue in result.report.emails[0].unresolved)
    assert not result.report.questions
    assert not result.report.contract_violations
