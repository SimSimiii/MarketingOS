"""Choosing between two drafts, and the ways that goes wrong quietly.

A preference judge fails like a miscalibrated grader rather than like a bug: it
returns a confident winner every time, and only the ballot arithmetic says
whether the winner is the email or the letter it was labelled with. Both
failures are pinned here.
"""

import pytest

from app.marketing.email_copy import Email
from app.marketing.tournament import PreferenceJudge, _ballot
from tests.marketing.conftest import (
    VOTE_A,
    RoleScriptedProvider,
    make_session,
    votes_for_the_challenger,
    votes_for_the_champion,
)

PERSONA = "a developer who ships weekly"


def email(subject: str) -> Email:
    return Email(
        position=1,
        subject=subject,
        preview_text="what changes on Monday",
        greeting="Hi there,",
        body=f"This is the body of {subject}.",
        call_to_action="Start the trial",
        sign_off="- the team",
    )


def judge(provider: RoleScriptedProvider) -> PreferenceJudge:
    return PreferenceJudge(make_session(provider))


# ------------------------------------------------------------------ the ballot


def test_the_labels_are_swapped_on_half_the_ballot():
    """A model shown two options prefers one of the slots whatever is in it.
    Splitting the ballot evenly between orders is what turns the answer into a
    statement about the emails."""
    lines = _ballot([PERSONA], votes=4)

    assert [swapped for _, swapped in lines] == [False, True, False, True]


def test_a_ballot_is_never_odd():
    """An odd ballot cannot tie, which sounds like an advantage and is really a
    winner produced by whichever label order got the extra vote."""
    assert len(_ballot([PERSONA], votes=3)) % 2 == 0
    assert len(_ballot([PERSONA, PERSONA, PERSONA], votes=None)) % 2 == 0


def test_every_reader_votes_when_no_count_is_given():
    people = ["one", "two", "three", "four"]
    assert {persona for persona, _ in _ballot(people, votes=None)} == set(people)


# ------------------------------------------------------------- what it settles


@pytest.mark.asyncio
async def test_a_judge_that_always_picks_the_same_letter_settles_nothing():
    """The failure this whole design exists for. Every reader answering "A"
    used to be a clean sweep for whichever draft was passed first; with the
    labels alternating it is the tie it always was."""
    provider = RoleScriptedProvider({"preference_judge": VOTE_A})

    duel = await judge(provider).duel(
        challenger=email("the rewrite"), champion=email("the draft"), personas=[PERSONA]
    )

    assert duel.challenger_votes == duel.champion_votes
    assert duel.challenger_wins is False


@pytest.mark.asyncio
async def test_a_challenger_the_readers_preferred_takes_the_title():
    provider = RoleScriptedProvider().push("preference_judge", *votes_for_the_challenger(2))

    duel = await judge(provider).duel(
        challenger=email("the rewrite"), champion=email("the draft"), personas=[PERSONA]
    )

    assert duel.challenger_wins is True
    assert duel.challenger_votes == 2


@pytest.mark.asyncio
async def test_the_incumbent_holds_the_title_on_a_tie():
    """A challenger has to be preferred, not merely not disliked - the same
    rule as `better_of`, for the same reason: a rewrite that did not measurably
    improve anything usually sanded the edges off a draft that worked."""
    # Two readers who genuinely preferred the rewrite and two who genuinely
    # preferred the draft - not four readers who all said "A". Blocks of two
    # because the ballot alternates label order, so a block has to cover both
    # orders to mean "these readers preferred this email".
    provider = RoleScriptedProvider().push(
        "preference_judge", *votes_for_the_challenger(2), *votes_for_the_champion(2)
    )

    duel = await judge(provider).duel(
        challenger=email("the rewrite"),
        champion=email("the draft"),
        personas=[PERSONA],
        votes=4,
    )

    assert duel.challenger_votes == duel.champion_votes == 2
    assert duel.challenger_wins is False
    assert "a tie" in duel.render()


@pytest.mark.asyncio
async def test_a_duel_nobody_could_judge_decides_nothing():
    """Distinct from a loss. A caller that read an unanswered duel as a defeat
    would keep the incumbent because the judge broke, and record it as a
    reader's preference."""
    provider = RoleScriptedProvider({"preference_judge": "not json at all"})

    duel = await judge(provider).duel(
        challenger=email("the rewrite"), champion=email("the draft"), personas=[PERSONA]
    )

    assert duel.decided is False
    assert duel.unreported == 2
    assert duel.render() == "nobody could choose between them"


@pytest.mark.asyncio
async def test_both_emails_reach_the_reader_whole():
    provider = RoleScriptedProvider({"preference_judge": VOTE_A})

    await judge(provider).duel(
        challenger=email("the rewrite"), champion=email("the draft"), personas=[PERSONA]
    )

    prompt = provider.requests_for("preference_judge")[0].system_prompt or ""
    assert "the rewrite" in prompt
    assert "the draft" in prompt
    assert PERSONA in prompt


@pytest.mark.asyncio
async def test_the_reasons_come_back_with_the_verdict():
    """A duel that says only who won tells a writer nothing. Why the reader
    preferred one draft is the part a rewrite can act on."""
    provider = RoleScriptedProvider().push("preference_judge", *votes_for_the_challenger(2))

    duel = await judge(provider).duel(
        challenger=email("the rewrite"), champion=email("the draft"), personas=[PERSONA]
    )

    assert duel.reasons
    assert all(reason for reason in duel.reasons)
