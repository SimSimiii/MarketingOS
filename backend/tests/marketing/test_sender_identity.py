import pytest

from app.marketing.briefs import CampaignBrief
from app.marketing.email_copy import parse_email, render_review
from app.marketing.gates import GateReport, evidence_gate, overlap_gate
from app.marketing.reader import PanelRead
from app.marketing.request import CampaignRequest
from app.marketing.writer import EmailWriter
from tests.marketing.conftest import (
    RoleScriptedProvider,
    artifacts_fixture,
    campaign_brief,
    email_draft,
    make_session,
)


@pytest.mark.asyncio
@pytest.mark.parametrize("sender", ["", "Ari"])
async def test_signoff_uses_brand_only_unless_the_user_supplies_a_sender(sender):
    artifacts = artifacts_fixture()
    provider = RoleScriptedProvider()
    response = email_draft().replace("SIGNOFF: - The team", "SIGNOFF: - Ari" if sender else "SIGNOFF: - Product support")
    provider.set_default("email_writer", response)
    campaign = CampaignBrief.model_validate_json(campaign_brief(count=1))
    draft = await EmailWriter(make_session(provider)).draft(
        brief=campaign.emails[0], campaign=campaign,
        request=CampaignRequest(name="Sender audit", request="Write one acquisition email", sender_name=sender),
        artifacts=artifacts, previous=[],
    )
    assert draft.sign_off == ("- Ari" if sender else f"- {artifacts.business.company_name}")


@pytest.mark.asyncio
@pytest.mark.parametrize("name", ["", "Ari"])
async def test_user_role_identity_is_preserved_in_drafts_rewrites_and_adjustments(name):
    artifacts = artifacts_fixture()
    role = "Independent affiliate"
    request = CampaignRequest(name="Affiliate", request="Write an acquisition email",
                              sender_name=name, sender_role=role)
    provider = RoleScriptedProvider().set_default("email_writer",
        email_draft().replace("SIGNOFF: - The team", "SIGNOFF: - Invented product support"))
    writer = EmailWriter(make_session(provider))
    campaign = CampaignBrief.model_validate_json(campaign_brief(count=1))
    args = {"brief": campaign.emails[0], "campaign": campaign, "request": request,
            "artifacts": artifacts, "previous": []}
    draft = await writer.draft(**args)
    rewritten = await writer.revise(draft=draft, gates=GateReport(), read=PanelRead(), **args)
    adjusted = await writer.adjust(draft=rewritten, instruction="More direct", **args)
    expected = f"- {request.sender} — {artifacts.business.company_name}"
    assert [item.sign_off for item in (draft, rewritten, adjusted)] == [expected] * 3
    assert len(provider.requests_for("email_writer")) == 3


def test_sender_signature_does_not_hide_repeated_marketing_in_the_body():
    first = parse_email(email_draft(), 1).model_copy(update={
        "subject": "Products", "body": "A book product.",
        "sign_off": "- Independent affiliate — LedgerLoop",
    })
    second = first.model_copy(update={"position": 2, "subject": "Readers",
                                      "body": "An owned reader list."})
    assert overlap_gate(second, [first], company_name="LedgerLoop").passed
    first.body += " Your next launch becomes simple with these tools together."
    second.body += " Your next launch becomes simple with these tools together."
    assert overlap_gate(second, [first], company_name="LedgerLoop").blocking


def test_signature_still_passes_through_factual_checks():
    from app.knowledge.ledger import EvidenceIndex

    draft = parse_email(email_draft(), 1)
    draft.sign_off = "- Independent affiliate — LedgerLoop, promising 847% growth"
    assert evidence_gate(render_review(draft), EvidenceIndex(artifacts_fixture().evidence)).blocking
