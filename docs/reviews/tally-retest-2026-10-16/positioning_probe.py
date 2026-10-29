"""Read-only acceptance probes for the external Tally review.

Synthetic cases reproduce named symptoms; saved-data cases use the exact
exported Tally snapshot. Failing assertions intentionally remain outside the
normal test suite. No product code, database or model calls are changed.

From backend/: .venv/Scripts/python.exe -m pytest \
    ../docs/reviews/tally-retest-2026-10-16/positioning_probe.py -q
"""

import json
import sys
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT / "backend"))

# Resolve settings to the scripted test environment before app imports.
import tests.conftest  # noqa: E402, F401
from app.knowledge.artifacts import BusinessProfile, KnowledgeArtifacts  # noqa: E402
from app.knowledge.ledger import Evidence, EvidenceContext, EvidenceKind, EvidenceLedger  # noqa: E402
from app.market.claims import Claim, ClaimAxis, ClaimSet, compare_claims  # noqa: E402
from app.market.positioning import Territory, build, claims_from_knowledge, rebuild  # noqa: E402
from app.market.radar import MarketSnapshot  # noqa: E402
from app.market.rivals import RivalProfile  # noqa: E402
from app.market.sameness import check  # noqa: E402


def own(text: str, axis: ClaimAxis) -> Claim:
    return Claim(text=text, verbatim=text, axis=axis)


def rival(name: str, *claims: Claim) -> RivalProfile:
    return RivalProfile(name=name, verified=True, claims=ClaimSet(claims=list(claims)))


def knowledge() -> KnowledgeArtifacts:
    rows = json.loads((Path(__file__).parent / "inputs/knowledgeartifactset.json").read_text(encoding="utf-8"))
    return KnowledgeArtifacts.model_validate(rows[0]["payload"])


def snapshot() -> MarketSnapshot:
    rows = json.loads((Path(__file__).parent / "inputs/marketscan.json").read_text(encoding="utf-8"))
    return MarketSnapshot.model_validate(rows[0]["payload"])


def test_synthetic_different_customer_results_are_not_equivalent_proof():
    ours = own("Creator achieved 30% feedback response rates for a web clipper", ClaimAxis.PROOF)
    theirs = own("A hospital reduced patient intake time by 40%", ClaimAxis.PROOF)
    result = build(ClaimSet(claims=[ours]), [rival("Alternative", theirs)])
    row = next(item for item in result.readings if item.ours)
    assert row.territory is Territory.OPEN
    assert row.comparison_status == "unknown"
    assert not row.theirs


@pytest.mark.parametrize("alternative", [
    "Pro plan costs €29 per user per month",
    "Pro plan costs $29 per user per year",
    "Pro plan costs $29 per workspace per month",
])
def test_synthetic_incompatible_explicit_price_terms_are_not_equivalent(alternative):
    ours = own("Pro plan costs $29 per user per month", ClaimAxis.PRICE)
    theirs = own(alternative, ClaimAxis.PRICE)
    assert compare_claims(ours, theirs)[0] == "potential_difference"


def test_synthetic_captured_absence_is_not_rendered_as_competitor_superiority():
    result = build(ClaimSet(), [rival("Alternative", own("White label branding", ClaimAxis.CONTROL))])
    text = result.render_for_strategy()
    assert "Where the field is ahead" not in text
    assert "Do not infer a missing capability or competitor superiority" in text


def test_synthetic_normal_form_vocabulary_does_not_trigger_a_rewrite_advisory():
    text = "Collect form submissions, send the data through integrations and keep the form free."
    claim = own(text, ClaimAxis.BREADTH)
    positioning = build(ClaimSet(claims=[claim]), [rival("A", claim), rival("B", claim)])
    report = check(subject="Connect your form", preview="", body=text, positioning=positioning)
    assert report.passed
    assert not report.advisory


def test_saved_proof_category_parity_and_field_ahead_wording_are_removed():
    saved = snapshot()
    current = rebuild(saved.positioning, saved.rivals)
    assert not any(row.axis is ClaimAxis.PROOF and row.ours and row.territory is Territory.TABLE_STAKES
                   for row in current.readings)
    assert "Where the field is ahead" not in current.render_for_strategy()


@pytest.mark.parametrize("text", [
    "Use a custom domain for your forms.",
    "Remove Tally branding on the Pro plan.",
])
def test_synthetic_same_documented_brand_control_capability_is_not_reported_missing(text):
    entry = Evidence(id="E1", kind=EvidenceKind.FEATURE, claim=text, verbatim=text)
    artifacts = KnowledgeArtifacts(evidence=EvidenceLedger(entries=[entry]))
    result = build(claims_from_knowledge(artifacts), [rival("Alternative", own(text, ClaimAxis.CONTROL))])
    matches = [row for row in result.readings if row.axis is ClaimAxis.CONTROL and row.ours]
    assert matches, "Our documented control capability is placed in OTHER while the identical rival claim is CONTROL/exposed."


def test_saved_brand_control_facts_are_represented_in_the_current_positioning():
    artifacts = knowledge()
    assert any(entry.id == "E296" and "Remove Tally branding" in entry.verbatim for entry in artifacts.evidence.entries)
    assert any(entry.id == "E297" and "Custom domains" in entry.verbatim for entry in artifacts.evidence.entries)
    saved = snapshot()
    current = build(claims_from_knowledge(artifacts), saved.rivals)
    assert any(row.axis is ClaimAxis.CONTROL and row.ours for row in current.readings), (
        "Existing facts E296/E297 classify OTHER and miss the top-30 cap; six rival CONTROL rows still have no own claim."
    )


@pytest.mark.parametrize("condition", [
    "billed yearly", "annual payment required", "facturé annuellement",
])
def test_synthetic_explicit_annual_commitment_is_not_equivalent_to_unknown_commitment(condition):
    text = "Pro plan costs $29 per user per month"
    ours = own(text, ClaimAxis.PRICE).model_copy(update={"verbatim": text + ", " + condition})
    theirs = own(text, ClaimAxis.PRICE)
    assert compare_claims(ours, theirs)[0] == "potential_difference", (
        "The price condition exists in the quote but is ignored unless it uses a recognised literal."
    )


def test_synthetic_explicit_rival_comparison_is_not_selected_as_our_own_open_ground():
    entry = Evidence(
        id="E1", kind=EvidenceKind.PRICE,
        claim="Typeform charges $39 per month for unlimited responses",
        verbatim="Typeform charges $39 per month for unlimited responses.",
        source="https://tally.so/help/compare",
        context=EvidenceContext(subject="Typeform", source_kind="vendor_comparison", claim_scope="comparison"),
    )
    artifacts = KnowledgeArtifacts(business=BusinessProfile(company_name="Tally"),
                                   evidence=EvidenceLedger(entries=[entry]))
    result = build(claims_from_knowledge(artifacts), [rival("Alternative")])
    assert not any(row.ours and "Typeform charges" in row.proposition for row in result.readings), (
        "Even explicit competitor subject + vendor_comparison context is selected as our own proposition."
    )


def test_saved_rival_prices_are_not_selected_as_our_own_open_ground():
    saved = snapshot()
    current = rebuild(saved.positioning, saved.rivals)
    misplaced = [row.proposition for row in current.readings if row.ours and
                 row.proposition.startswith(("Typeform ", "Jotform ", "Google Forms "))]
    assert not misplaced, f"Competitor prices from Tally's comparison page occupy our positioning: {misplaced}"
