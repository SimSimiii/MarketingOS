"""The deterministic checks - especially the one that makes an invented
statistic impossible rather than merely discouraged."""

import pytest

from app.knowledge.artifacts import CallToAction, OfferSheet
from app.knowledge.ledger import Evidence, EvidenceIndex, EvidenceKind, EvidenceLedger
from app.marketing.briefs import EmailBrief
from app.marketing.email_copy import Email
from app.marketing.gates import (
    call_to_action_gate,
    capability_scope_gate,
    evidence_gate,
    overlap_gate,
    placeholder_gate,
    planned_call_to_action_gate,
    repeated_call_to_action_gate,
    repeated_sign_off_gate,
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
    assert evidence_gate(
        "You are running in 10 minutes, for $29/month, billed annually.", index
    ).passed


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


# -------------------------------------------------------- capability scope


def test_non_verified_voice_product_claim_is_blocked():
    report = capability_scope_gate(
        "orqAgent supports voice and telephony calls.",
        ["voice_telephony"],
    )

    assert not report.passed
    assert "voice_telephony" in report.render()


def test_audience_voice_context_is_not_a_product_claim():
    report = capability_scope_gate(
        "Your receptionist answers phone calls all day.",
        ["voice_telephony"],
    )

    assert report.passed


def test_non_verified_full_backend_replacement_claim_is_blocked():
    report = capability_scope_gate(
        "We replace your entire backend.",
        ["full_saas_backend"],
    )

    assert not report.passed
    assert "full_saas_backend" in report.render()


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
    assert spam_gate(
        email("We are SOC2 compliant and support SMTP.\n\nReview the DPIA before deployment.\n\nThird.")
    ).passed


def test_canonical_uppercase_brand_is_not_shouting_but_other_caps_still_are():
    assert spam_gate(email("CABAIA makes work bags."), company_name="CABAIA").passed
    report = spam_gate(email("CABAIA makes AMAZING bags."), company_name="CABAIA")
    assert "AMAZING" in report.render()
    assert "CABAIA" not in report.render()


def test_brand_exemption_requires_exact_spelling_and_word_boundaries():
    assert not spam_gate(email("PAPIER planners."), company_name="Papier").passed
    assert not spam_gate(email("CABAIASTORE bags."), company_name="CABAIA").passed
    assert not spam_gate(email("BAGS are useful."), company_name="CABAIA BAGS").passed


@pytest.mark.parametrize("method", ["POST", "PATCH", "HEAD", "OPTIONS", "DELETE", "TRACE", "CONNECT"])
def test_documented_http_methods_are_vocabulary_not_shouting(method):
    assert spam_gate(email(f"The endpoint accepts an HTTP {method} request.\n\nInspect the JSON example.")).passed


def test_click_here_link_text_is_flagged():
    report = spam_gate(email("A body.\n\nSecond.\n\nThird.", call_to_action="Click here"))
    assert not report.passed
    assert "tells the reader nothing" in report.render()


def test_generic_signup_label_is_blocked_when_the_plan_points_to_documentation():
    report = planned_call_to_action_gate(
        email("A body.\n\nSecond.\n\nThird.", call_to_action="Get started"),
        EmailBrief(
            call_to_action=(
                "Review the official documentation: "
                "https://docs.example.test/knowledge-base/quotas"
            )
        ),
    )
    assert not report.passed
    assert "official documentation" in report.render()


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


@pytest.mark.parametrize("disclosure", [
    "Je suis partenaire affilié indépendant de systeme.io et je ne représente pas la marque.",
    "Je suis partenaire affilié indépendant de systeme.io. Je ne représente pas systeme.io.",
    "I am an independent affiliate of systeme.io and I do not represent the company.",
    "Je suis partenaire affilié indépendant de systeme.io, sans appartenir à la marque. Je peux bénéficier de cette relation d’affiliation si vous passez par mes recommandations.",
    "Je suis partenaire affilié indépendant de systeme.io. Je peux être rémunéré si vous passez ultérieurement par un lien affilié.",
    "I am an independent affiliate of systeme.io. I may earn a commission if you buy through my affiliate link.",
])
def test_affiliation_disclosure_can_recur_without_repeating_the_pitch(disclosure):
    first = email("Découvrez les produits physiques.\n\n" + disclosure, subject="Products")
    second = email("Construisez votre liste de lecteurs.\n\n" + disclosure,
                   subject="Readers", position=2)
    assert overlap_gate(second, [first], company_name="systeme.io").passed
    assert not overlap_gate(second, [first], company_name="Another brand").passed
    promise = " Votre prochain lancement devient simple avec tous ces outils réunis."
    first.body += promise
    second.body += promise
    assert not overlap_gate(second, [first], company_name="systeme.io").passed


def test_disclosure_does_not_hide_repeated_promises_or_subjects():
    paragraph = ("Je suis partenaire affilié indépendant de systeme.io. "
                 "Votre prochain lancement devient simple avec tous ces outils réunis.")
    first = email("Une gamme de livres.\n\n" + paragraph, subject="Products")
    second = email("Une liste de lecteurs.\n\n" + paragraph, subject="Readers", position=2)
    assert not overlap_gate(second, [first], company_name="systeme.io").passed
    second.body = "Je suis partenaire affilié indépendant de systeme.io.\n\nAutre message."
    second.subject = first.subject
    assert "subject repeats" in overlap_gate(second, [first], company_name="systeme.io").render()


@pytest.mark.parametrize("phrase,blocks", [
    ("Découvrez les fonctionnalités détaillées maintenant", False),
    ("Découvrez toutes les fonctionnalités détaillées maintenant", True),
])
def test_overlap_counts_accented_words_without_splitting_them(phrase, blocks):
    first = email("Première proposition. " + phrase + ".\n\nUne autre idée.", subject="First")
    second = email("Nouvel argument. " + phrase + ".\n\nDécidez autrement.",
                   subject="Second", position=2)
    assert bool(overlap_gate(second, [first]).blocking) is blocks


def test_nonrepresentation_clause_does_not_hide_marketing_in_the_same_sentence():
    common = ("Je suis partenaire affilié indépendant de systeme.io et je ne représente pas "
              "la marque qui vous permet de gérer toutes vos ventes sans effort.")
    first = email("Des produits physiques. " + common, subject="First")
    second = email("Une liste de lecteurs. " + common, subject="Second", position=2)
    assert overlap_gate(second, [first], company_name="systeme.io").blocking


def test_captured_affiliate_sender_clause_does_not_leave_false_overlap():
    disclosure = "Je vous écris comme partenaire affilié indépendant de systeme.io, et non au nom de la marque."
    first = email("Une gamme de livres.\n\n" + disclosure, subject="Products")
    second = email("Une liste de lecteurs.\n\n" + disclosure, subject="Readers", position=2)
    assert overlap_gate(second, [first], company_name="systeme.io").passed
    repeated = " Votre prochain lancement devient simple avec tous ces outils réunis."
    first.body += repeated
    second.body += repeated
    assert not overlap_gate(second, [first], company_name="systeme.io").passed


@pytest.mark.asyncio
async def test_sequence_review_uses_the_same_disclosure_rule():
    from app.marketing.briefs import CampaignBrief
    from app.marketing.sequence import SequenceReviewer
    from tests.marketing.conftest import RoleScriptedProvider, make_session

    disclosure = "Je suis partenaire affilié indépendant de systeme.io."
    first = email("Découvrez les produits physiques.\n\n" + disclosure, subject="Products")
    second = email("Construisez votre liste de lecteurs.\n\n" + disclosure,
                   subject="Readers", position=2)
    provider = RoleScriptedProvider()
    report = await SequenceReviewer(make_session(provider)).review(
        [first, second], CampaignBrief(), arc_read=False, company_name="systeme.io",
    )
    assert report.passed
    assert not provider.requests


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


@pytest.mark.parametrize("label,accepted", [
    ("See the RSS workflow", True),
    ("See the CRM workflow", False),
    ("Book an RSS demo", False),
    ("See RSS pricing", False),
])
def test_documentation_action_must_still_match_its_licensed_destination(label, accepted):
    offer = OfferSheet(calls_to_action=[CallToAction(label="Sign up")])
    brief = EmailBrief(
        call_to_action="Review the official documentation: https://docs.example.com/rss-to-email",
        destination_kind="web", next_step_url="https://docs.example.com/rss-to-email",
        next_step_value="Documents RSS-to-email automation.",
    )
    report = call_to_action_gate(email("A.\n\nB.\n\nC.", call_to_action=label), offer, brief)
    assert (not report.issues) is accepted


def test_a_standalone_body_line_must_not_repeat_the_rendered_cta():
    report = repeated_call_to_action_gate(
        email(
            "First paragraph.\n\nSign up for free\n\nLast paragraph.",
            call_to_action="Sign up for free",
        )
    )

    assert not report.passed
    assert report.blocking[0].gate == "duplicate-call-to-action"
    assert "rendered separately" in report.blocking[0].detail


def test_a_cta_phrase_inside_a_real_sentence_is_not_a_duplicate_block():
    report = repeated_call_to_action_gate(
        email(
            "You can sign up for free and inspect the dashboard before setup.\n\nNext step.\n\nDone.",
            call_to_action="Sign up for free",
        )
    )

    assert report.passed


def test_trailing_cta_arrow_and_sign_off_are_blocked_before_assembly():
    draft = email(
        "Plan this week's posts.\n\nCompare plans →\n\n- The team",
        call_to_action="Compare plans",
    )

    assert repeated_call_to_action_gate(draft).blocking[0].gate == "duplicate-call-to-action"
    assert repeated_sign_off_gate(draft).blocking[0].gate == "duplicate-sign-off"
