import pytest

from app.marketing.briefs import CampaignBrief
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
