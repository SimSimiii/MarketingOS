"""What the campaign form collects has to survive into the strategist's context.

`render_context()` is the only place the user's own framing reaches a prompt -
`strategist.py` passes it as `campaign_context` - and every line of it is
optional, so a field the form never fills is indistinguishable from one the
user left blank. That is how `goals` stayed unreachable: the backend accepted
it, rendered it and shipped golden cases that set it, while no form collected
it, so every campaign the product produced planned without the one line saying
what the sequence was for.
"""

from app.marketing.request import CampaignRequest


def _request(**kwargs: object) -> CampaignRequest:
    return CampaignRequest(name="Launch", request="Write exactly 3 emails", **kwargs)  # type: ignore[arg-type]


def test_the_goal_reaches_the_context_the_strategist_reads() -> None:
    context = _request(goals="trial signups").render_context()
    assert "What the user wants out of it: trial signups" in context


def test_a_campaign_with_no_goal_says_nothing_about_one() -> None:
    """Omitted rather than rendered empty: a blank line invites the strategist
    to invent an objective, and an invented one outranks nothing."""
    context = _request().render_context()
    assert "What the user wants out of it" not in context


def test_every_line_the_form_collects_survives_into_the_context() -> None:
    context = _request(
        product_description="A note-taking app",
        target_market="independent repair shops",
        goals="trial signups",
        sender_name="Marco",
        sender_role="founder",
    ).render_context()

    assert "Campaign: Launch" in context
    assert "What the user says the product is: A note-taking app" in context
    assert "Who the user says they are targeting: independent repair shops" in context
    assert "What the user wants out of it: trial signups" in context
    assert "Who it comes from: Marco, founder" in context
