"""Recorded Tally retest plus explicitly synthetic cross-brand regressions."""

import json
from pathlib import Path

import pytest

from app.knowledge.artifacts import BusinessProfile, KnowledgeArtifacts
from app.knowledge.ledger import Evidence, EvidenceContext, EvidenceKind, EvidenceLedger
from app.market.claims import Claim, ClaimAxis, ClaimSet, compare_claims
from app.market.positioning import (
    MAX_STRATEGY_CHARS,
    AxisReading,
    PositioningMap,
    Territory,
    axis_for_evidence,
    build,
    build_current,
    claims_from_knowledge,
    rebuild,
)
from app.market.radar import MarketSnapshot


@pytest.fixture
def recorded_tally() -> tuple[KnowledgeArtifacts, MarketSnapshot]:
    payload = json.loads((Path(__file__).parent / "fixtures/tally_positioning_retest.json").read_text(encoding="utf-8"))
    return (KnowledgeArtifacts.model_validate(payload["knowledge"]),
            MarketSnapshot.model_validate(payload["snapshot"]))


def test_recorded_control_facts_survive_selection_and_comparison(recorded_tally):
    artifacts, saved = recorded_tally
    original = saved.model_dump(mode="json")
    result = build_current(artifacts, saved.rivals, we_have_proof=True)
    controls = [row for row in result.readings if row.axis is ClaimAxis.CONTROL and row.ours]
    assert controls
    assert any("custom domain" in claim.text.lower() for row in controls for claim in row.ours)
    assert any("branding" in claim.text.lower() for row in controls for claim in row.ours)
    assert all(any(claim.verbatim for claim in row.ours) for row in controls)
    assert "saved competitor pages" in " ".join(result.notes)
    assert saved.model_dump(mode="json") == original


def test_recorded_legacy_rival_prices_cannot_become_our_open_ground(recorded_tally):
    _, saved = recorded_tally
    current = rebuild(saved.positioning, saved.rivals)
    assert not [row.proposition for row in current.readings if row.ours and
                row.proposition.startswith(("Typeform ", "Jotform ", "Google Forms "))]


def test_recorded_current_claims_exclude_comparison_pages(recorded_tally):
    artifacts, saved = recorded_tally
    current = build_current(artifacts, saved.rivals)
    own = [claim for row in current.readings for claim in row.ours]
    assert own
    assert not any("/help/compare" in claim.source for claim in own)
    assert len(current.render_for_strategy("Web studios delivering white label forms on custom domains")) <= MAX_STRATEGY_CHARS


@pytest.mark.parametrize("brand", ["StudioForm", "LedgerWave"])
@pytest.mark.parametrize("text", [
    "Use a custom domain for your forms.",
    "Remove provider branding on the Pro plan.",
    "Publish reports under your own domain.",
    "White-label dashboards for your clients.",
    "Transfer ownership of a workspace to your client.",
])
def test_synthetic_control_concepts_are_not_product_specific(brand, text):
    entry = Evidence(id="E1", kind=EvidenceKind.FEATURE, claim=text, verbatim=text)
    artifacts = KnowledgeArtifacts(business=BusinessProfile(company_name=brand),
                                   evidence=EvidenceLedger(entries=[entry]))
    assert axis_for_evidence(entry) is ClaimAxis.CONTROL
    assert claims_from_knowledge(artifacts).claims[0].axis is ClaimAxis.CONTROL


@pytest.mark.parametrize("text", [
    "We do not support custom domains.",
    "You cannot remove provider branding.",
    "Custom domains are not supported.",
])
def test_synthetic_unsupported_control_is_not_promoted_from_another_axis(text):
    from app.market.rivals import RivalProfile

    own = Claim(text="Custom domains for forms", verbatim="Custom domains for forms", axis=ClaimAxis.CONTROL)
    rival = RivalProfile(name="Alternative", verified=True, claims=ClaimSet(claims=[
        Claim(text=text, verbatim=text, axis=ClaimAxis.EFFORT),
    ]))
    result = build(ClaimSet(claims=[own]), [rival])
    control = next(row for row in result.readings if row.axis is ClaimAxis.CONTROL and row.ours)
    assert not control.theirs


@pytest.mark.parametrize("condition", [
    "billed yearly", "annual payment required", "facturé annuellement",
    "engagement annuel", "a prepayment covering twelve months is mandatory",
])
def test_synthetic_annual_or_unparsed_terms_cannot_equal_unknown_terms(condition):
    text = "Pro plan costs $29 per user per month"
    ours = Claim(text=text, verbatim=text + ", " + condition, axis=ClaimAxis.PRICE)
    theirs = Claim(text=text, verbatim=text, axis=ClaimAxis.PRICE)
    assert compare_claims(ours, theirs)[0] == "potential_difference"


@pytest.mark.parametrize("context", [
    EvidenceContext(subject="ExternalCo", source_kind="vendor_comparison", claim_scope="comparison"),
    None,
])
def test_synthetic_foreign_comparison_is_never_an_own_product_claim(context):
    entry = Evidence(id="E1", kind=EvidenceKind.PRICE,
                     claim="ExternalCo charges $39 per month for unlimited records",
                     verbatim="ExternalCo charges $39 per month for unlimited records.",
                     source="https://firstvendor.example/help/compare", context=context)
    artifacts = KnowledgeArtifacts(business=BusinessProfile(company_name="FirstVendor"),
                                   evidence=EvidenceLedger(entries=[entry]))
    assert not claims_from_knowledge(artifacts).claims


def test_synthetic_explicit_foreign_subject_is_excluded_even_on_an_ordinary_source():
    entry = Evidence(id="E1", kind=EvidenceKind.PRICE,
                     claim="ExternalCo charges $39 per month for unlimited records",
                     verbatim="ExternalCo charges $39 per month for unlimited records.",
                     source="https://firstvendor.example/pricing")
    artifacts = KnowledgeArtifacts(business=BusinessProfile(company_name="FirstVendor"),
                                   evidence=EvidenceLedger(entries=[entry]))
    assert not claims_from_knowledge(artifacts).claims


def test_synthetic_many_prices_do_not_hide_documented_control():
    entries = [Evidence(id=f"P{i}", kind=EvidenceKind.PRICE,
                        claim=f"Pro plan includes {i + 1} credits for ${i + 10} per month",
                        verbatim=f"Pro plan includes {i + 1} credits for ${i + 10} per month")
               for i in range(45)]
    entries.append(Evidence(id="C1", kind=EvidenceKind.FEATURE,
                            claim="Publish reports on a custom domain",
                            verbatim="Publish reports on a custom domain"))
    artifacts = KnowledgeArtifacts(evidence=EvidenceLedger(entries=entries))
    claims = claims_from_knowledge(artifacts).claims
    assert len(claims) <= 30
    assert any(claim.axis is ClaimAxis.CONTROL for claim in claims)


def test_synthetic_large_map_has_a_bounded_audience_prioritised_strategy():
    rows = [AxisReading(axis=ClaimAxis.PRICE, territory=Territory.OPEN,
                        proposition=f"Offer {i} costs ${i + 10} per account per month",
                        ours=[Claim(text=f"Offer {i} costs ${i + 10} per account per month", axis=ClaimAxis.PRICE)])
            for i in range(180)]
    rows.append(AxisReading(axis=ClaimAxis.CONTROL, territory=Territory.OPEN,
                           proposition="Transfer client workspace ownership on a custom domain",
                           ours=[Claim(text="Transfer client workspace ownership on a custom domain", axis=ClaimAxis.CONTROL)]))
    positioning = PositioningMap(readings=rows, rivals_profiled=6)
    brief = positioning.render_for_strategy("Client workspace transfer custom domain")
    assert len(brief) <= MAX_STRATEGY_CHARS
    assert brief.index("Transfer client workspace") < brief.index("Offer 0")
    assert "additional captured propositions remain in the full map" in brief
    assert len(positioning.readings) == 181


def test_synthetic_unbounded_condition_text_cannot_break_strategy_limit():
    claim = Claim(text="A supported export", axis=ClaimAxis.CONTROL,
                  context=EvidenceContext(conditions="Only in a documented environment. " * 1000))
    positioning = PositioningMap(rivals_profiled=2, readings=[AxisReading(
        axis=ClaimAxis.CONTROL, territory=Territory.OPEN, proposition=claim.text, ours=[claim],
    )], notes=["Capture note. " * 1000] * 4)
    assert len(positioning.render_for_strategy()) <= MAX_STRATEGY_CHARS
