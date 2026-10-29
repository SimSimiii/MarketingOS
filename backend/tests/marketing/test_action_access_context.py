import pytest

from app.knowledge.artifacts import CallToAction
from app.knowledge.ledger import MAX_EVIDENCE_IN_PROMPT, Evidence, EvidenceContext, EvidenceKind
from app.marketing.briefs import CampaignBrief
from app.marketing.critic import ConversionCritic
from app.marketing.gates import GateReport
from app.marketing.reader import PanelRead
from app.marketing.request import CampaignRequest
from app.marketing.writer import EmailWriter
from tests.marketing.conftest import (
    CRITIQUE_SHIP,
    RoleScriptedProvider,
    artifacts_fixture,
    campaign_brief,
    email_draft,
    make_session,
)


@pytest.mark.asyncio
@pytest.mark.parametrize("excluded", [False, True])
async def test_writer_and_critic_receive_selected_access_evidence_without_adding_calls(excluded):
    artifacts = artifacts_fixture()
    artifacts.offer.calls_to_action.append(CallToAction(label="Inspect",url="https://example.com/demo"))
    artifacts.evidence.entries.extend(Evidence(id=f"F{i}",kind=EvidenceKind.FEATURE,
        claim="Release note details",verbatim="Release note details") for i in range(MAX_EVIDENCE_IN_PROMPT+5))
    quote = "Open [the sample](https://example.com/demo) without registration."
    artifacts.evidence.entries.append(Evidence(id="ACCESS",kind=EvidenceKind.FEATURE,
        claim="Inspect the sample without registration",verbatim=quote,
        context=EvidenceContext(subject="Notewright demo",source_kind="official_documentation",
            claim_scope="capability",verification="quote_verified_in_material")))
    campaign = CampaignBrief.model_validate_json(campaign_brief(count=1))
    brief = campaign.emails[0].model_copy(update={"next_step_url":"https://example.com/demo",
        "forbidden_evidence_ids":["ACCESS"] if excluded else []})
    provider = RoleScriptedProvider({"email_writer":email_draft(),"conversion_critic":CRITIQUE_SHIP})
    session = make_session(provider)
    email = await EmailWriter(session).draft(brief=brief,campaign=campaign,
        request=CampaignRequest(name="Inspect",request="Write one acquisition email"),artifacts=artifacts,previous=[])
    await ConversionCritic(session).critique(email=email,brief=brief,campaign=campaign,
        artifacts=artifacts,read=PanelRead(),gates=GateReport())
    for role in ["email_writer","conversion_critic"]:
        assert provider.calls_by_role[role] == 1
        assert (quote in provider.requests_for(role)[0].system_prompt) is not excluded
