"""The writer is told the layout the run already chose, not asked to guess it.

HEADLINE and EYEBROW are the only fields that depend on it - the branded tier
sets a headline large, the plain one drops it - and a writer left to judge
from the request missed both ways. A request with no tier on it (a bench, a
post-run edit) keeps the old instruction rather than hearing a decision
nobody made.
"""

import pytest

from app.marketing.briefs import CampaignBrief
from app.marketing.render_html import EmailTier
from app.marketing.request import CampaignRequest
from app.marketing.writer import EmailWriter
from tests.marketing.conftest import (
    RoleScriptedProvider,
    artifacts_fixture,
    campaign_brief,
    email_draft,
    make_session,
)


async def _writer_prompt(tier: EmailTier | None) -> str:
    provider = RoleScriptedProvider()
    provider.set_default("email_writer", email_draft())
    campaign = CampaignBrief.model_validate_json(campaign_brief(count=1))
    await EmailWriter(make_session(provider)).draft(
        brief=campaign.emails[0],
        campaign=campaign,
        request=CampaignRequest(
            name="Layout", request="Write one acquisition email", email_tier=tier
        ),
        artifacts=artifacts_fixture(),
        previous=[],
    )
    return provider.requests_for("email_writer")[0].system_prompt or ""


@pytest.mark.asyncio
async def test_a_branded_run_tells_the_writer_to_write_the_headline():
    prompt = await _writer_prompt(EmailTier.BRANDED)

    assert "laid out as mail from the company" in prompt
    assert "Write the `HEADLINE`" in prompt
    assert "Leave both empty if you are unsure" not in prompt


@pytest.mark.asyncio
async def test_a_plain_run_tells_the_writer_to_leave_the_headline_out():
    prompt = await _writer_prompt(EmailTier.PLAIN)

    assert "Leave `HEADLINE` and `EYEBROW` empty" in prompt
    assert "Write the `HEADLINE`" not in prompt


@pytest.mark.asyncio
async def test_without_a_decision_the_writer_still_judges_it_from_the_request():
    prompt = await _writer_prompt(None)

    assert "Answer it from the request at the top" in prompt
    assert "Already decided" not in prompt
