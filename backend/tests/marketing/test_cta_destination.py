"""A signup button uses the selected source URL, not a generic homepage."""

import pytest

from app.knowledge.artifacts import (
    AudienceModel,
    BusinessProfile,
    CallToAction,
    KnowledgeArtifacts,
    OfferSheet,
    Segment,
)
from app.knowledge.ledger import Evidence, EvidenceKind, EvidenceLedger, EvidenceStrength
from app.marketing.briefs import ArgumentOption, CampaignBrief, EmailBrief
from app.marketing.contract import parse_contract
from app.marketing.email_copy import Email
from app.marketing.render_html import BrandStyle, EmailTier, render_html, style_for_action
from app.marketing.strategist import Strategist, _recovered_next_step

SIGNUP = "https://app.example.test/sign-up"
HOMEPAGE = "https://example.test/"
OFFER = OfferSheet(calls_to_action=[CallToAction(label="Start free", url=SIGNUP)])


@pytest.mark.parametrize("proof_order", [["R1", "R2"], ["R2", "R1"]])
def test_selected_cta_keeps_any_cited_official_destination(proof_order):
    overview = "https://docs.vendor.test/overview"
    example = "https://docs.vendor.test/request-example"
    artifacts = KnowledgeArtifacts(evidence=EvidenceLedger(entries=[
        Evidence(id="R1", kind=EvidenceKind.FEATURE, claim="The API emits test events.",
                 verbatim="The API emits test events.", source=overview),
        Evidence(id="R2", kind=EvidenceKind.FEATURE, claim="The guide has a complete request.",
                 verbatim="The guide has a complete request.", source=example),
    ]))
    action = f"Inspect the example request: {example}"
    payoff = "Compare the complete request with the inputs your application can supply."

    assert _recovered_next_step(
        artifacts=artifacts, evidence_ids=["R1", "R2"],
        next_step_evidence_ids=proof_order, call_to_action=action, next_step_value=payoff,
    ) == (action, payoff)


@pytest.mark.parametrize("action", [
    "https://docs.vendor.test/overview or https://docs.vendor.test/request-example",
    "https://docs.vendor.test/request-example or https://unverified.test/",
    "https://unverified.test/",
    "https://docs.vendor.test/background",
])
def test_recovered_cta_still_replaces_ambiguous_or_unsupported_destination(action):
    overview = "https://docs.vendor.test/overview"
    artifacts = KnowledgeArtifacts(evidence=EvidenceLedger(entries=[
        Evidence(id="R1", kind=EvidenceKind.FEATURE, claim="The API emits test events.",
                 verbatim="The API emits test events.", source=overview),
        Evidence(id="R2", kind=EvidenceKind.FEATURE, claim="The guide has a complete request.",
                 verbatim="The guide has a complete request.",
                 source="https://docs.vendor.test/request-example"),
        Evidence(id="R3", kind=EvidenceKind.FEATURE, claim="Unrelated background.",
                 verbatim="Unrelated background.", source="https://docs.vendor.test/background"),
    ]))

    corrected_action, corrected_payoff = _recovered_next_step(
        artifacts=artifacts, evidence_ids=["R1", "R2", "R3"],
        next_step_evidence_ids=["R1", "R2"], call_to_action=action,
        next_step_value="A payoff that needs a supported destination.",
    )

    assert corrected_action == f"Review the official documentation: {overview}"
    assert "The API emits test events" in corrected_payoff


def test_known_destination_in_brief_reaches_the_rendered_button():
    style = style_for_action(
        BrandStyle(cta_url=HOMEPAGE), explicit_url=None,
        planned_action=f"Essayez gratuitement ({SIGNUP}).", offer=OFFER,
    )
    rendered = render_html(
        Email(position=1, subject="Essayez le produit", preview_text="Un premier essai",
              greeting="Bonjour,", body="Créez votre premier agent.",
              call_to_action="Créer mon compte", sign_off="L'équipe"),
        EmailTier.BRANDED, style,
    )
    assert f'href="{SIGNUP}"' in rendered
    assert f'href="{HOMEPAGE}"' not in rendered


def test_user_destination_wins_over_the_brief():
    custom = "https://example.test/launch"
    style = style_for_action(
        BrandStyle(cta_url=HOMEPAGE), explicit_url=custom,
        planned_action=SIGNUP, offer=OFFER,
    )
    assert style.cta_url == custom


def test_verified_evidence_source_can_be_the_pre_signup_destination():
    guide = "https://docs.example.test/smtp"
    style = style_for_action(
        BrandStyle(cta_url=HOMEPAGE), explicit_url=None,
        planned_action=f"Review the setup guide: {guide}", offer=OFFER,
        licensed_urls=[guide],
    )
    assert style.cta_url == guide


@pytest.mark.parametrize("action", [
    "Create an account", "https://invented.test/signup", SIGNUP + "-invented",
    f"{SIGNUP} or https://example.test/demo", "javascript:alert(1)",
])
def test_unknown_or_ambiguous_destination_preserves_fallback(action):
    style = style_for_action(
        BrandStyle(cta_url=HOMEPAGE), explicit_url=None, planned_action=action, offer=OFFER,
    )
    assert style.cta_url == HOMEPAGE


@pytest.mark.parametrize("explicit_usage", [False, True])
def test_inferred_audience_stack_does_not_establish_recipient_usage(explicit_usage):
    guide = "https://docs.vendor.test/send-with-platformx"
    artifacts = KnowledgeArtifacts(
        business=BusinessProfile(company_name="Vendor", what_it_does="Sends email"),
        audience=AudienceModel(segments=[Segment(
            name="Backend engineer", situation="Often maintains PlatformX email setup",
        )]),
        evidence=EvidenceLedger(entries=[Evidence(
            id="R1", kind=EvidenceKind.INTEGRATION,
            claim="PlatformX can connect to Vendor using SMTP.",
            verbatim="Connect PlatformX to Vendor using SMTP.",
            source=guide, strength=EvidenceStrength.STRONG,
        )]),
    )
    user_context = "Announce Vendor to PlatformX users" if explicit_usage else "Announce Vendor"
    brief = CampaignBrief(
        reader_segment="Backend engineer",
        emails=[EmailBrief(position=1, single_idea="A documented integration",
                           evidence_ids=["R1"], call_to_action="Read the guide")],
    )

    normalized = Strategist(None)._normalize(
        brief, parse_contract("Write exactly one email"), artifacts, None, user_context,
    )
    constraints = " ".join(normalized.emails[0].must_not_say)
    assert ("If you use Platformx" in constraints) is (not explicit_usage)
    assert normalized.emails[0].call_to_action.endswith(guide)


@pytest.mark.parametrize("explicit_usage", [False, True])
def test_niche_integration_cannot_win_broad_audience_bakeoff(explicit_usage):
    artifacts = KnowledgeArtifacts(
        business=BusinessProfile(company_name="Vendor", what_it_does="Sends email"),
        audience=AudienceModel(segments=[Segment(
            name="Backend engineer", situation="Owns product email",
        )]),
        evidence=EvidenceLedger(entries=[Evidence(
            id="R1", kind=EvidenceKind.INTEGRATION,
            claim="PlatformX can connect to Vendor using SMTP.",
            verbatim="Connect PlatformX to Vendor using SMTP.",
            source="https://docs.vendor.test/send-with-platformx",
            strength=EvidenceStrength.STRONG,
        )]),
    )
    brief = CampaignBrief(reader_segment="Backend engineer", emails=[EmailBrief(
        position=1, single_idea="Send transactional product email",
        alternative_arguments=[ArgumentOption(
            single_idea="Use Vendor for PlatformX Auth email",
            evidence_ids=["R1"],
            call_to_action="Read the PlatformX guide",
        )],
    )])
    context = "Launch for PlatformX users" if explicit_usage else "Launch for backend engineers"

    normalized = Strategist(None)._normalize(
        brief, parse_contract("Write exactly one email"), artifacts, None, context,
    )

    assert len(normalized.emails[0].alternative_arguments) == int(explicit_usage)


@pytest.mark.parametrize("surface", ["Dashboard", "Console", "Logs"])
def test_product_ui_is_not_an_unestablished_integration(surface):
    artifacts = KnowledgeArtifacts(
        business=BusinessProfile(company_name="Vendor", what_it_does="Sends email"),
        evidence=EvidenceLedger(entries=[Evidence(
            id="R1", kind=EvidenceKind.FEATURE,
            claim=f"Sent messages can be inspected in the {surface}.",
            verbatim=f"Inspect your sent messages in the {surface}.",
            source=f"https://docs.vendor.test/{surface.lower()}/emails/introduction",
            strength=EvidenceStrength.STRONG,
        )]),
    )
    brief = CampaignBrief(emails=[EmailBrief(
        position=1, single_idea=f"Inspect sent messages in the {surface}",
        evidence_ids=["R1"],
        alternative_arguments=[ArgumentOption(
            single_idea=f"Review a test message in the {surface}",
            evidence_ids=["R1"], call_to_action="Read the guide",
        )],
    )])

    normalized = Strategist(None)._normalize(
        brief, parse_contract("Write exactly one email"), artifacts, None,
        "Introduce Vendor to backend engineers",
    )

    email = normalized.emails[0]
    assert not any("Present this integration conditionally" in c for c in email.must_not_say)
    assert len(email.alternative_arguments) == 1
    assert not any(
        "Present this integration conditionally" in c
        for c in email.alternative_arguments[0].must_not_say
    )
