"""What a stranger takes away from the email, checked twice.

The failure these are about is not bad writing - it is the failure good
writing produces here. Every rule the writer follows pushes the product off
the page: open on the reader, argue one idea, prefer the specific to the
adjective, stay under two hundred words. Followed well they produce an email
that describes somebody's Tuesday with real precision, calls the product "it"
four times, and leaves a stranger with nothing to click toward.

Two instruments catch it, and they are deliberately different in kind. The
clarity gate is a string search over the rendered draft, so it costs nothing
and it is not a matter of opinion. The cold reader's `understood` is a
judgment about whether the sentence that *is* there actually landed, which no
regular expression can answer.
"""

import pytest

from app.knowledge.artifacts import BusinessProfile
from app.marketing.craft import EmailVersion, better_of
from app.marketing.email_copy import Email
from app.marketing.gates import GateReport, GateSeverity, clarity_gate
from app.marketing.reader import BlindRead, PanelRead
from app.marketing.request import CampaignRequest
from app.marketing.writer import _comprehension_failure
from tests.marketing.conftest import (
    RoleScriptedProvider,
    blind_read,
    campaign_brief,
    clicks_for,
    email_draft,
)
from tests.marketing.test_choosing import one_email
from tests.marketing.test_pipeline import build, refine_only

_NOTEWRIGHT = BusinessProfile(
    company_name="Notewright",
    what_it_does="turns your merged commits into a release note",
    category="developer tooling",
)

#: The failure in the shape it actually arrives in: fluent, specific about the
#: reader's week, and never once saying what is being sold. The product is
#: "it" throughout and the only thing naming the company is the sign-off.
#:
#: Lifted almost verbatim from the worked example that used to sit at the
#: bottom of prompts/writer.md, which is where the failure was being taught.
_ANONYMOUS = (
    "The work shipped Tuesday. The note about it is what is keeping you here on Friday.\n\n"
    "Your script assembles the commits. What it cannot say is why any of them mattered,\n"
    "which is the part support hears about later.\n\n"
    "Point it at the branch you merged and read what comes back.\n\n"
    "Keep the half that is right and rewrite the half that is not."
)


def _email(body: str, **overrides) -> Email:
    fields = {
        "position": 1,
        "subject": "The 4pm Friday paragraph",
        "preview_text": "the part of shipping nobody scheduled time for",
        "greeting": "Hi there,",
        "body": body,
        "call_to_action": "Point it at a branch",
        "sign_off": "- the Notewright team",
    }
    fields.update(overrides)
    return Email(**fields)


def test_an_email_that_names_the_product_only_in_the_signoff_is_blocked():
    """The sign-off answers who sent this, which is a different question.

    A reader who reaches the link having never met the name has nothing to
    attach the click to. Blocking rather than advisory because it is a fact
    about the text, not a judgment about it.
    """
    report = clarity_gate(_email(_ANONYMOUS), _NOTEWRIGHT)

    assert [issue.severity for issue in report.issues] == [GateSeverity.BLOCKING]
    assert "never names Notewright" in report.issues[0].detail
    assert "sign-off" in report.issues[0].detail, "the writer is told where it went wrong"


def test_naming_it_once_in_the_body_is_enough():
    """One sentence in the second paragraph, and the check goes quiet. What
    the gate wants is not a product page - it is the reader having met the
    name before they are asked to click it."""
    body = _ANONYMOUS.replace(
        "Point it at the branch",
        "Notewright is developer tooling: it reads the diff and the issue it closed as "
        "one thing.\n\n"
        "Point it at the branch",
    )
    assert clarity_gate(_email(body), _NOTEWRIGHT).issues == []


def test_a_name_with_no_category_around_it_is_advisory_only():
    """Named the way a stranger's surname is: a proper noun, and still no idea
    what kind of thing it is.

    Worth saying and not worth blocking - a company can establish its category
    through a mechanism instead of a noun, and a gate that blocked on
    vocabulary would fail the concrete drafts it exists to protect.
    """
    body = _ANONYMOUS.replace("Point it at", "Point Notewright at")
    report = clarity_gate(_email(body), _NOTEWRIGHT)

    assert [issue.severity for issue in report.issues] == [GateSeverity.ADVISORY]
    assert "developer tooling" in report.issues[0].detail


def test_a_company_with_no_distinctive_name_is_not_checked():
    """The word "group" turning up in a sentence is not the company being
    named, and a check that cannot tell the difference is worse than none."""
    assert clarity_gate(_email(_ANONYMOUS), BusinessProfile()).issues == []
    assert (
        clarity_gate(_email(_ANONYMOUS), BusinessProfile(company_name="The Software Group")).issues
        == []
    )


# ---------------------------------------------------------- the cold reader


def _read(understood: bool, pull: int) -> PanelRead:
    return PanelRead(
        reads=[
            BlindRead(
                understood=understood, opens_in_100=40, clicks_in_100=clicks_for(pull)
            )
        ]
    )


def test_a_reader_who_could_not_say_what_it_is_has_not_clicked():
    """Comprehension is a precondition of `landed`, not a term in it.

    A click estimate on an email the reader could not parse is not a low
    score - it answers a different question - and letting it clear the floor
    ships copy whose own reader could not say what it was for.
    """
    assert _read(True, 9).landed
    assert not _read(False, 9).landed


def test_the_panel_needs_a_majority_to_have_understood_it():
    """One reader in three who missed it is what copy that works looks like.
    Two is a draft with a real problem - the same rule `landed` uses."""

    def panel(*flags: bool) -> PanelRead:
        return PanelRead(reads=[BlindRead(understood=flag) for flag in flags])

    assert panel(True, True, False).understood
    assert not panel(True, False, False).understood
    assert PanelRead().understood, "nobody read it, which is no verdict rather than a bad one"


def test_a_draft_nobody_understood_loses_to_one_they_did_at_any_score():
    """The comparison the loop was missing.

    Without it, a beautifully written paragraph that never says what the
    product is beats a plainer draft that does, on a click estimate neither
    number is about.
    """
    clear = EmailVersion(
        attempt=2, email=_email(_ANONYMOUS), gates=GateReport(), read=_read(True, 4)
    )
    murky = EmailVersion(
        attempt=1, email=_email(_ANONYMOUS), gates=GateReport(), read=_read(False, 9)
    )

    assert better_of(murky, clear) is clear
    assert better_of(clear, murky) is clear
    assert clear.measured > murky.measured


def test_the_rewrite_is_handed_the_guess_and_not_a_count():
    """"One reader thought it was an agency retainer" names the distance
    between what the email implied and what the product is. A writer can close
    a named distance; it cannot close a number."""
    panel = PanelRead(
        reads=[
            BlindRead(persona="a staff engineer", understood=True, what_it_sells="release notes"),
            BlindRead(
                persona="a founder with no engineer",
                understood=False,
                what_it_sells="some kind of agency retainer?",
            ),
        ]
    )
    note = _comprehension_failure(panel)

    assert "1 of the 2 readers" in note
    assert "some kind of agency retainer?" in note
    assert "a founder with no engineer" in note
    assert _comprehension_failure(_read(True, 8)) == "", "nothing to say when they got it"


@pytest.mark.asyncio
async def test_a_draft_the_reader_could_not_decode_is_rewritten_and_says_so(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    """End to end: the reader cannot say what it is, the loop does not ship
    it, and the rewrite is told why in the reader's own words."""
    provider.set_default("strategist", campaign_brief(1))
    provider.push(
        "blind_reader",
        blind_read(
            pull=8,
            understood=False,
            what_it_sells="honestly no idea - some sort of consultancy?",
        ),
        blind_read(pull=8),
    )
    provider.push(
        "email_writer",
        email_draft(subject="The 4pm Friday paragraph", body=_ANONYMOUS),
        email_draft(subject="Notewright reads the branch you merged"),
    )

    pipeline, _ = build(provider, refine_only(max_revisions=1))
    result = await pipeline.run(one_email(request_fixture))

    outcome = result.outcomes[0]
    assert len(outcome.versions) == 2, "a draft nobody could decode does not ship"
    assert outcome.best.attempt == 2

    rewrite = provider.requests_for("email_writer")[1].messages[-1].content
    assert "could not tell what this is" in rewrite.lower()
    assert "some sort of consultancy?" in rewrite

    assert result.report.emails[0].understood
    assert result.report.clear
