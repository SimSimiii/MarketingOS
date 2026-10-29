"""Synthetic prices and customer results: identical numbers are not identical claims."""

import pytest

from app.knowledge.ledger import (
    Evidence,
    EvidenceContext,
    EvidenceIndex,
    EvidenceKind,
    EvidenceLedger,
)
from app.marketing.gates import evidence_gate


@pytest.mark.parametrize("source,draft", [
    ("Pro is $29 per year.", "Pro is $29 per month."),
    ("Pro is $29 per seat per month.", "Pro is $29 per account per month."),
    ("Pro is $29 per month.", "Exports cost $29 per month."),
    ("Pro is $29 per month, billed annually.", "Pro is $29 per month."),
    ("Pro is $29 per month excluding VAT.", "Pro is $29 per month."),
    ("The press costs $390.", "You save $390."),
])
def test_same_amount_does_not_license_incompatible_scope_or_missing_terms(source, draft):
    index = EvidenceIndex(EvidenceLedger(), source)
    report = evidence_gate(draft, index)
    assert not report.passed
    assert "documented" in report.render()


def test_price_is_matched_against_one_compatible_offer_not_mixed_across_plans():
    index = EvidenceIndex(EvidenceLedger(),
                          "Pro is $29 per seat per month. Solo is $29 per account per year.")
    assert not evidence_gate("Solo is $29 per account per month.", index).passed
    assert evidence_gate("Solo is $29 per account per year.", index).passed
    assert evidence_gate("Pro is $29 per seat per month.", index).passed


def test_explicit_context_preserves_plan_price_when_quote_does_not_name_it():
    index = EvidenceIndex(EvidenceLedger(entries=[Evidence(
        id="E1", kind=EvidenceKind.PRICE, claim="Pro includes exports",
        verbatim="$29 per month, billed annually.",
        context=EvidenceContext(subject="Pro plan", claim_scope="offer"),
    )]))
    assert not evidence_gate("Exports cost $29 per month, billed annually.", index).passed
    assert evidence_gate("Pro is $29 per month, billed annually.", index).passed


@pytest.mark.parametrize("name", ["Pro Standard", "pro standard", "PRO STANDARD"])
def test_multiword_plan_name_matches_its_full_pricing_provenance(name):
    index = EvidenceIndex(EvidenceLedger(entries=[Evidence(
        id="E1", kind=EvidenceKind.PRICE, claim="Pro Standard is $19/year",
        verbatim="This is the mid-tier Pro plan. At $19 / year it includes forms.",
        context=EvidenceContext(subject="Pro Standard plan", claim_scope="offer"),
    )]))
    assert evidence_gate(f"{name} costs **$19 per year**.", index).passed
    assert not evidence_gate("Basic Standard costs $19 per year.", index).passed
    assert not evidence_gate("Pro Standard is available. Basic Standard costs $19 per year.", index).passed
    assert not evidence_gate("Pro Standard costs $19 per month.", index).passed


@pytest.mark.parametrize("duration", ["7-day", "7‐day", "7‑day", "7 days"])
def test_hyphenated_trial_duration_matches_a_spaced_source_without_licensing_other_durations(duration):
    index = EvidenceIndex(EvidenceLedger(), "Test Pro free for 7 days with no credit card required.")
    assert evidence_gate(f"Start your {duration} Pro trial.", index).passed
    assert not evidence_gate(f"Start your {duration.replace('7', '8')} Pro trial.", index).passed


def test_individual_result_generalization_is_explained_without_a_taste_veto():
    index = EvidenceIndex(EvidenceLedger(entries=[Evidence(
        id="E1", kind=EvidenceKind.METRIC,
        claim="Pilot bakery reduced waste by 20%",
        verbatim="The pilot bakery reduced waste by 20% during May.",
        context=EvidenceContext(subject="Pilot bakery", claim_scope="customer_outcome",
                                conditions="one bakery during May"),
    )]))
    generalized = evidence_gate("You will reduce waste by 20%.", index)
    assert generalized.passed
    assert "attributed customer result" in generalized.advisory[0].detail
    assert not evidence_gate("The pilot bakery reduced waste by 20% during May.", index).advisory


def test_documented_capability_does_not_establish_a_recent_launch():
    index = EvidenceIndex(EvidenceLedger(entries=[Evidence(
        id="E1", kind=EvidenceKind.FEATURE, claim="CSV export",
        verbatim="The app exports invoices as CSV.",
        context=EvidenceContext(claim_scope="capability", source_kind="official_documentation"),
    )]))
    report = evidence_gate("We just launched our new feature: CSV export.", index)
    assert report.passed
    assert "dated launch evidence" in report.advisory[0].detail
    assert not evidence_gate("The app exports invoices as CSV.", index).advisory


def test_new_customer_phrase_does_not_claim_a_product_launch():
    assert not evidence_gate("For new customers: see our plans.", EvidenceIndex(EvidenceLedger())).issues


@pytest.mark.parametrize("draft", [
    "Starter costs $29 per month.",
    "**Starter** costs **$29 per month**.",
    "Our Starter plan costs $29 per month.",
    "Acme Starter costs $29 per month.",
    "Your form keeps working — and Starter is **$29/month**, cancel anytime.",
    "Your form keeps working, and the Starter plan costs $29 per month.",
    "Your form keeps working; Starter costs $29 per month.",
    "Votre formulaire reste disponible — et Starter coûte $29 par mois.",
])
def test_short_plan_name_is_licensed_by_its_actual_quoted_price_heading(draft):
    index = EvidenceIndex(EvidenceLedger(entries=[Evidence(
        id="E1", kind=EvidenceKind.PRICE, claim="Acme Starter costs $29/month",
        verbatim="### Starter $29/month Cancel anytime",
        context=EvidenceContext(subject="Acme Starter plan", claim_scope="offer"),
    )]))
    assert evidence_gate(draft, index).passed
    for wrong in [
        "Basic Starter costs $29 per month.", "**Basic Starter** costs $29 per month.",
        "Starter costs $29 per year.", "Starter costs $29 per month. Basic Starter costs $29 per month.",
        "Your form keeps working — and Basic Starter costs $29 per month.",
        "Your form keeps working, and the Basic Starter plan costs $29 per month.",
        "Your form keeps working — and Starter costs $29 per year.",
    ]:
        assert not evidence_gate(wrong, index).passed


def test_short_price_alias_requires_a_unique_explicit_heading_and_keeps_conditions():
    def item(id, subject, quote):
        return Evidence(id=id, kind=EvidenceKind.PRICE, claim="Paid offer", verbatim=quote,
                        context=EvidenceContext(subject=subject, claim_scope="offer"))
    no_heading = EvidenceIndex(EvidenceLedger(entries=[item("E1", "Acme Starter", "$29/month, billed annually")]))
    assert not evidence_gate("Starter costs $29/month, billed annually.", no_heading).passed
    annual = EvidenceIndex(EvidenceLedger(entries=[item("E1", "Acme Starter", "### Starter $29/month, billed annually")]))
    assert evidence_gate("Starter costs $29/month, billed annually.", annual).passed
    assert not evidence_gate("Starter costs $29/month.", annual).passed
    ambiguous = EvidenceIndex(EvidenceLedger(entries=[
        item("E1", "Acme Starter", "### Starter $29/month"),
        item("E2", "Rival Starter", "### Starter $29/month"),
    ]))
    assert not evidence_gate("Starter costs $29/month.", ambiguous).passed
