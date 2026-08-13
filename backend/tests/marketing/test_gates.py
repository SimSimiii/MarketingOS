"""The deterministic checks - especially the one that makes an invented
statistic impossible rather than merely discouraged."""

import pytest

from app.knowledge.artifacts import CallToAction, OfferSheet
from app.knowledge.ledger import Evidence, EvidenceIndex, EvidenceKind, EvidenceLedger
from app.marketing.email_copy import Email
from app.marketing.gates import (
    call_to_action_gate,
    evidence_gate,
    overlap_gate,
    placeholder_gate,
    spam_gate,
    stock_phrase_gate,
)


@pytest.fixture
def index() -> EvidenceIndex:
    ledger = EvidenceLedger(
        entries=[
            Evidence(
                id="E1",
                kind=EvidenceKind.METRIC,
                claim="sets up in 10 minutes",
                verbatim="Most teams are running their first report in 10 minutes.",
            ),
            Evidence(
                id="E2",
                kind=EvidenceKind.PRICE,
                claim="$29 per month",
                verbatim="The Team plan is $29/month, billed annually.",
            ),
        ]
    )
    return EvidenceIndex(ledger, source_text="We connect 25 models across 9 providers.")


def email(body: str, **overrides) -> Email:
    fields = {
        "position": 1,
        "subject": "A subject that fits",
        "preview_text": "a preview that extends it",
        "greeting": "Hi there,",
        "body": body,
        "call_to_action": "Start the trial",
        "sign_off": "- The team",
    }
    fields.update(overrides)
    return Email(**fields)


# ------------------------------------------------------------------ evidence


def test_a_figure_that_matches_the_ledger_passes(index: EvidenceIndex):
    assert evidence_gate("You are running in 10 minutes, for $29/month.", index).passed


def test_a_figure_the_ledger_contradicts_is_blocked(index: EvidenceIndex):
    """The worked example from the redesign: the site says ten minutes and the
    draft says eight. No model is asked - the claim simply is not licensed."""
    report = evidence_gate("Set up in 8 minutes.", index)
    assert not report.passed
    assert '"8 minutes"' in report.render()


def test_formatting_differences_do_not_count_as_lies(index: EvidenceIndex):
    """'10 mins' and '10 minutes' are the same claim - a gate that fired here
    would be firing on the writer's formatting, not on its honesty."""
    assert evidence_gate("Running in 10 mins.", index).passed


def test_a_true_detail_from_the_source_licenses_the_claim(index: EvidenceIndex):
    """The compiler did not promote it to the ledger, but the user's own page
    says it - the writer should not be blocked for reading carefully."""
    assert evidence_gate("It covers 25 models today.", index).passed


def test_a_fabricated_testimonial_is_blocked(index: EvidenceIndex):
    report = evidence_gate(
        'As one customer put it: "this saved my team an entire week of work every month".',
        index,
    )
    assert not report.passed
    assert "presented as something a real person said" in report.render()


def test_an_invented_url_is_blocked(index: EvidenceIndex):
    report = evidence_gate("Read more at https://example.com/case-studies/acme", index)
    assert not report.passed
    assert "never invent a URL" in report.render()


def test_small_bare_numbers_are_rhetoric_not_claims(index: EvidenceIndex):
    """Blocking "three reasons to switch" would make the gate noise, and a
    gate that gets ignored protects nothing."""
    assert evidence_gate("There are 3 reasons teams switch, and one of them matters.", index).passed


# -------------------------------------------------------------- placeholders


def test_an_unfilled_placeholder_blocks():
    report = placeholder_gate("Hi [First Name], welcome to [Product].")
    assert not report.passed
    assert "[First Name]" in report.render()


def test_a_configured_merge_field_is_personalization_not_a_placeholder():
    """The old system banned every bracketed token, which also banned real
    ESP personalization. Merge fields are configured, not forbidden."""
    assert placeholder_gate("Hi {{first_name}},", merge_fields=["first_name"]).passed


def test_a_merge_field_this_campaign_cannot_fill_still_blocks():
    report = placeholder_gate("Hi {{ceo_name}},", merge_fields=["first_name"])
    assert not report.passed
    assert "not a merge field this campaign can fill" in report.render()


def test_stock_phrasing_is_named_exactly():
    report = stock_phrase_gate("In today's fast-paced world, we're excited to announce our tool.")
    assert not report.passed
    assert "in today's fast-paced world" in report.render()


# ------------------------------------------------------------------ delivery


def test_spam_vocabulary_blocks():
    report = spam_gate(email("Act now and get started.\n\nSecond block.\n\nThird block."))
    assert not report.passed
    assert "act now" in report.render()


def test_shouting_and_punctuation_abuse_block():
    report = spam_gate(
        email("This is URGENT and IMPORTANT!!\n\nSecond block.\n\nThird block.")
    )
    assert not report.passed
    assert "capitals" in report.render()


def test_known_acronyms_are_not_shouting():
    assert spam_gate(email("We are SOC2 compliant.\n\nSecond.\n\nThird.")).passed


def test_click_here_link_text_is_flagged():
    report = spam_gate(email("A body.\n\nSecond.\n\nThird.", call_to_action="Click here"))
    assert not report.passed
    assert "tells the reader nothing" in report.render()


# ------------------------------------------------------------------- overlap


def test_a_reused_phrase_across_the_sequence_is_caught():
    """Every writing prompt asked for this and nothing ever verified it."""
    shared = "the same release note three times last month and nobody read it"
    first = email(f"{shared}\n\nSecond block here.\n\nThird block here.", position=1)
    second = email(f"{shared}\n\nA different second.\n\nA different third.", position=2)

    report = overlap_gate(second, [first])
    assert not report.passed
    assert "already appears in email 1" in report.render()


def test_a_repeated_opening_move_is_caught():
    first = email("You wrote the same note again last week.\n\nB.\n\nC.", position=1)
    second = email("You wrote the same note again last month, oddly.\n\nB2.\n\nC2.", position=2)

    report = overlap_gate(second, [first])
    assert "opens exactly like email 1" in report.render()


def test_the_first_email_can_never_overlap():
    assert overlap_gate(email("Anything at all.\n\nB.\n\nC."), []).passed


# ----------------------------------------------------------------------- ask


def test_asking_for_something_the_product_does_not_offer_is_advisory():
    """Advisory, not blocking: the writer legitimately rephrases an action,
    and blocking on wording would fail every draft."""
    offer = OfferSheet(calls_to_action=[CallToAction(label="Start the trial")])
    report = call_to_action_gate(email("B.\n\nB.\n\nC.", call_to_action="Book a demo"), offer)

    assert report.passed
    assert report.advisory
    assert "not one of the actions this product supports" in report.render()


def test_a_rephrased_but_real_action_is_accepted():
    offer = OfferSheet(calls_to_action=[CallToAction(label="Start the trial")])
    assert not call_to_action_gate(
        email("B.\n\nB.\n\nC.", call_to_action="Start the trial"), offer
    ).issues
