"""The argument, as opposed to the claim.

`single_idea` says what an email asserts. On its own it produces an assertion
with a citation attached - true, checkable, and no reason for a stranger to
act. What was missing was the shape persuasion actually has: here is what you
are living with, here is what you already do about it, here is why that keeps
failing, here is what this does instead.

These check that the four beats survive the trip from the strategist's answer
to the writer's prompt, because that trip is the only thing they are for. A
field a model fills and nothing renders is worse than no field: it costs
output tokens on every run and changes nothing.
"""

import json

import pytest

from app.marketing.briefs import CampaignBrief, EmailBrief
from app.marketing.request import CampaignRequest
from tests.marketing.conftest import RoleScriptedProvider, campaign_brief
from tests.marketing.test_choosing import one_email, writer_briefs
from tests.marketing.test_pipeline import build, refine_only

_SPINE = {
    "felt_need": "release notes are what is still open at four on a Friday",
    "status_quo": "a changelog script somebody on the team wrote and now maintains",
    "why_it_fails": "a script can list the commits and cannot say why any of them mattered",
    "mechanism": "reads the diff and the issue it closed as one thing, so the why is in the material",
}


def test_the_four_beats_reach_the_writer_in_order():
    """Order is the point. A writer handed `why_it_fails` inside a flat list
    of eleven attributes treats it as one more thing that could go on the
    page; handed it as the third beat, it is the sentence without which the
    fourth means nothing."""
    rendered = EmailBrief(position=1, single_idea="your script costs more than you think", **_SPINE).render()

    assert "The argument it makes, in this order:" in rendered
    for index, key in enumerate(
        ("felt_need", "status_quo", "why_it_fails", "mechanism"), start=1
    ):
        assert f"{index}. " in rendered
        assert _SPINE[key] in rendered
    assert rendered.index(_SPINE["why_it_fails"]) < rendered.index(_SPINE["mechanism"])


def test_an_unfilled_argument_refuses_rather_than_leaving_a_blank():
    """An empty beat is a decision not to invent one. Rendering it as an empty
    label invites the writer to fill it, and an invented status quo is worse
    than none - the reader knows what they actually do."""
    rendered = EmailBrief(position=1).render()

    assert "Not established" in rendered
    assert "do not invent a status quo" in rendered.lower()


def test_the_orientation_is_what_the_reader_has_to_be_left_holding():
    brief = CampaignBrief(
        reader="a developer who ships weekly",
        orientation="Notewright writes the release note from the branch you merged",
        promise="release notes stop being a Friday job",
    )
    assert "What we are selling them, in one sentence" in brief.render()
    assert "Notewright writes the release note" in brief.render()


@pytest.mark.asyncio
async def test_the_writer_is_told_what_it_is_selling(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    """The strategist's sentence where it wrote one - it is the one aimed at
    this reader rather than at everybody."""
    payload = json.loads(campaign_brief(1))
    payload["orientation"] = "a tool that writes the release note off the branch you merged"
    payload["emails"][0].update(_SPINE)
    provider.set_default("strategist", json.dumps(payload))

    pipeline, _ = build(provider, refine_only(max_revisions=0))
    await pipeline.run(one_email(request_fixture))

    prompt = writer_briefs(provider)[0]
    assert "a tool that writes the release note off the branch you merged" in prompt
    assert _SPINE["why_it_fails"] in prompt, "the beat the copy cannot invent for itself"
    assert "This sentence has to survive the email" in prompt


@pytest.mark.asyncio
async def test_a_strategist_that_wrote_no_orientation_falls_back_to_the_profile(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    """The profile's own sentence is a worse answer than a reader-shaped one
    and an enormously better one than nothing. A prompt cannot ask for the
    product to be named plainly and then decline to say what it is."""
    provider.set_default("strategist", campaign_brief(1))

    pipeline, _ = build(provider, refine_only(max_revisions=0))
    await pipeline.run(one_email(request_fixture))

    prompt = writer_briefs(provider)[0]
    assert "turns your merged commits into a release note" in prompt
    assert "rather than one written for this reader" in prompt
