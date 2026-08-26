"""The subject bake-off: the one part of the deliverable nothing else improves.

Every rewrite in the system replaces the subject as a by-product of replacing
the body, and every judgment scores it only as part of the email underneath.
These are the properties that make replacing it deliberate rather than a fifth
way of changing it by accident.
"""

import json

import pytest

from app.marketing.briefs import EmailBrief
from app.marketing.email_copy import Email
from app.marketing.subject_lines import SubjectBakeOff, SubjectOption
from tests.marketing.conftest import (
    RoleScriptedProvider,
    artifacts_fixture,
    inbox_verdict,
    make_session,
    subject_options,
)

PERSONAS = ["a developer who ships weekly"]
BRIEF = EmailBrief(position=1, single_idea="release notes are a Friday problem")


def email(subject: str = "The line it already had") -> Email:
    return Email(
        position=1,
        subject=subject,
        preview_text="what changes on Monday",
        greeting="Hi there,",
        body="You wrote the same release note three times last month.",
        call_to_action="Start the trial",
        sign_off="- the team",
    )


async def improve(provider: RoleScriptedProvider, variants: int = 4):
    return await SubjectBakeOff(make_session(provider)).improve(
        email=email(),
        brief=BRIEF,
        artifacts=artifacts_fixture(),
        personas=PERSONAS,
        variants=variants,
    )


# ---------------------------------------------------------------- the field


@pytest.mark.asyncio
async def test_the_line_it_already_had_is_in_the_running():
    """Without the incumbent in the field the bake-off can only replace the
    subject, never keep it - so four weak alternatives would evict a strong
    line every time, and the step would be a random walk with a cost."""
    provider = RoleScriptedProvider(
        {"subject_lines": subject_options(4), "inbox_scanner": inbox_verdict(40, 10, 10, 10, 10)}
    )

    improved, summary = await improve(provider)

    assert improved.subject == "The line it already had"
    assert "kept" in summary


@pytest.mark.asyncio
async def test_a_line_more_people_would_open_replaces_it():
    provider = RoleScriptedProvider(
        {"subject_lines": subject_options(4), "inbox_scanner": inbox_verdict(10, 12, 38, 11, 9)}
    )

    improved, _ = await improve(provider)

    assert improved.subject == "Release notes, option 2"
    assert improved.preview_text == "a different bet, number 2"


@pytest.mark.asyncio
async def test_the_body_is_never_touched():
    provider = RoleScriptedProvider(
        {"subject_lines": subject_options(4), "inbox_scanner": inbox_verdict(10, 40, 9, 9, 9)}
    )

    improved, _ = await improve(provider)

    assert improved.body == email().body
    assert improved.call_to_action == email().call_to_action


# ------------------------------------------------------- what never gets judged


def test_an_option_too_long_for_an_inbox_is_not_sendable():
    """Length is arithmetic, so a bad option is dropped for free rather than
    sent back for a rewrite that costs a whole turn."""
    assert SubjectOption(subject="x" * 66, preview="fine").sendable is False
    assert SubjectOption(subject="fine", preview="x" * 111).sendable is False
    assert SubjectOption(subject="same words", preview="Same words").sendable is False
    assert SubjectOption(subject="fine", preview="extends it").sendable is True


@pytest.mark.asyncio
async def test_unsendable_options_are_dropped_before_anybody_scores_them():
    long_one = json.dumps(
        {
            "options": [
                {"subject": "x" * 80, "preview": "too long to send", "approach": "no"},
                {"subject": "This one fits", "preview": "and extends the subject", "approach": "y"},
            ]
        }
    )
    provider = RoleScriptedProvider(
        {"subject_lines": long_one, "inbox_scanner": inbox_verdict(10, 40)}
    )

    improved, _ = await improve(provider, variants=2)

    # Two lines were scored, not three: the incumbent and the one that fits.
    assert improved.subject == "This one fits"


# --------------------------------------------------------------- when it fails


@pytest.mark.asyncio
async def test_no_alternatives_leaves_the_email_exactly_as_it_was():
    provider = RoleScriptedProvider({"subject_lines": json.dumps({"options": []})})

    improved, summary = await improve(provider)

    assert improved == email()
    assert "sendable" in summary


@pytest.mark.asyncio
async def test_a_writer_that_will_not_answer_is_not_a_failed_email():
    """The subject step runs on a finished, judged email. A model that cannot
    produce alternatives must cost the run that step and nothing else."""
    provider = RoleScriptedProvider({"subject_lines": "not json"})

    improved, summary = await improve(provider)

    assert improved == email()
    assert summary


@pytest.mark.asyncio
async def test_readers_who_could_not_answer_leave_the_line_alone():
    provider = RoleScriptedProvider(
        {"subject_lines": subject_options(4), "inbox_scanner": "not json either"}
    )

    improved, summary = await improve(provider)

    assert improved == email()
    assert "nobody could judge" in summary


@pytest.mark.asyncio
async def test_a_score_for_a_line_that_was_not_offered_is_ignored():
    """A reader naming option 9 of a field of five is answering about nothing,
    and a bake-off that indexed on it would swap in whatever happened to sit
    at that position."""
    provider = RoleScriptedProvider(
        {
            "subject_lines": subject_options(2),
            "inbox_scanner": json.dumps(
                {
                    "scores": [
                        {"option": 1, "opens_in_100": 30, "why": "fine"},
                        {"option": 9, "opens_in_100": 99, "why": "nonsense"},
                    ]
                }
            ),
        }
    )

    improved, _ = await improve(provider, variants=2)

    assert improved.subject == "The line it already had"
