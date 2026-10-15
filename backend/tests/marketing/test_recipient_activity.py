"""Recipient events must come from the request, never from earlier drafts.

Scripted calls check context propagation and repair routing, not whether a real
model obeys the instructions. No subscription or API quota is used.
"""

import pytest

from app.marketing.briefs import CampaignBrief, EmailBrief
from app.marketing.email_copy import parse_email
from app.marketing.gates import GateReport
from app.marketing.reader import PanelRead
from app.marketing.request import CampaignRequest
from app.marketing.sequence import SequenceReviewer, SequenceVerdict
from app.marketing.writer import EmailWriter
from tests.marketing.conftest import email_draft, make_session


@pytest.mark.asyncio
@pytest.mark.parametrize("has_previous", [False, True])
async def test_drafting_and_revision_keep_confirmed_trigger_separate_from_prior_copy(
    provider, artifacts, has_previous,
):
    trigger = "Recipients have signed up but have not completed their first run."
    request = CampaignRequest(name="Activation", request=trigger)
    previous = [parse_email(email_draft(), 1)] if has_previous else []
    brief = EmailBrief(position=2 if has_previous else 1, single_idea="Review a result")
    campaign = CampaignBrief(reader="Existing users", interpretation="Encourage a review")
    writer = EmailWriter(make_session(provider))
    draft = await writer.draft(
        brief=brief, campaign=campaign, request=request,
        artifacts=artifacts, previous=previous,
    )
    await writer.revise(
        draft=draft, brief=brief, campaign=campaign, request=request,
        artifacts=artifacts, previous=previous, gates=GateReport(), read=PanelRead(),
        critique_notes="Make review conditional on having completed a run.",
    )
    for call in provider.requests_for("email_writer"):
        assert trigger in call.system_prompt
        assert "Only an explicit" in call.system_prompt
        context = call.messages[0].content
        assert "Already written and sent" not in context
        if has_previous:
            assert previous[0].subject in context
            assert previous[0].body in context
            assert "not delivery, open, click or completion records" in context
        else:
            assert "Drafts establish no recipient activity" in context
    assert len(provider.requests_for("email_writer")) == 2


@pytest.mark.asyncio
async def test_sequence_review_routes_an_unconfirmed_completion_to_the_later_email(provider):
    provider.set_default("sequence_reviewer", SequenceVerdict(
        each_stands_alone=False,
        notes=[{
            "position": 2,
            "problem": "The report CTA assumes completion of the previous run request.",
            "fix": "Offer a conditional route to create a run before reviewing it.",
        }],
    ).model_dump_json())
    first = parse_email(email_draft(), 1)
    second = first.model_copy(update={
        "position": 2, "subject": "A different subject",
        "body": "Open your finished report to review the result.",
    })
    report = await SequenceReviewer(make_session(provider)).review(
        [first, second], CampaignBrief(reader="Signed-up users"),
        request=CampaignRequest(
            name="Activation", request="Recipients signed up but have not completed a run.",
        ),
    )
    assert not report.passed
    assert "conditional route" in report.instruction_for(2)
    assert provider.calls_by_role["sequence_reviewer"] == 1
    assert "Recipients signed up but have not completed a run." in (
        provider.requests_for("sequence_reviewer")[0].system_prompt
    )
