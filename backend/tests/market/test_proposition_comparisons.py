"""Synthetic contrasting offers: category overlap is not proposition equivalence."""

import pytest

from app.knowledge.artifacts import KnowledgeArtifacts
from app.knowledge.ledger import Evidence, EvidenceContext, EvidenceKind, EvidenceLedger
from app.market.claims import Claim, ClaimAxis, ClaimSet, compare_claims, same_claim
from app.market.positioning import (
    AxisReading,
    PositioningMap,
    Territory,
    build,
    claims_from_knowledge,
    rebuild,
)
from app.market.radar import MarketSnapshot, diff
from app.market.rivals import RivalProfile
from app.market.sameness import check
from app.schemas.market import PositioningRead


def _claim(text: str, axis: ClaimAxis, **kwargs) -> Claim:
    return Claim(text=text, verbatim=text, axis=axis, **kwargs)


def _rival(name: str, *claims: Claim) -> RivalProfile:
    return RivalProfile(name=name, verified=True, claims=ClaimSet(claims=list(claims)))


def test_proposition_and_source_scope_survive_the_api_adapter():
    ours = _claim("Pro plan is $29 per user per month", ClaimAxis.PRICE,
                  context=EvidenceContext(subject="Pro subscription", conditions="billed annually"))
    other = _claim("Pro plan is $29 per user per year", ClaimAxis.PRICE)
    wire = PositioningRead.of(build(ClaimSet(claims=[ours]), [_rival("Alternative", other)])).model_dump(mode="json")
    reading = next(row for row in wire["readings"] if row["ours"])
    assert reading["proposition"]
    assert reading["comparison_status"] == "potential_difference"
    assert reading["comparisons"]["Alternative"] == "potential_difference"
    assert reading["comparison_notes"]
    assert reading["ours"][0]["context"]["conditions"] == "billed annually"


@pytest.mark.parametrize(("axis", "ours", "theirs"), [
    (ClaimAxis.PRICE, "Free shipping on orders over $40", "Pro plan costs $29 per user per month"),
    (ClaimAxis.PRICE, "Website analytics costs $15 per month", "Session replay costs $20 per month"),
    (ClaimAxis.PRICE, "Website analytics costs $15 per month", "Feature flags cost $10 per month"),
    (ClaimAxis.PRICE, "Analytics plan includes 50 sites for $15/month", "Analytics plan includes extra users at $20/month"),
    (ClaimAxis.PRICE, "Extra sites cost $15/month", "Extra users cost $15/month"),
    (ClaimAxis.QUALITY, "99.9% API uptime", "Proofreading detects spelling errors"),
    (ClaimAxis.PROOF, "Atelier saved 30 minutes processing invoices", "Clinic doubled patient referrals"),
    (ClaimAxis.CONTROL, "Export invoice data as CSV", "Self-hosted in your own VPC"),
    (ClaimAxis.OTHER, "Reschedule recurring appointments", "Send tax records to the accountant"),
])
def test_common_category_with_different_propositions_is_not_parity(axis, ours, theirs):
    own, other = _claim(ours, axis), _claim(theirs, axis)
    result = build(ClaimSet(claims=[own]), [_rival("Alternative", other)])

    reading = next(row for row in result.readings if row.ours)
    assert reading.territory is Territory.OPEN
    assert reading.comparison_status == "unknown"
    assert not reading.theirs
    assert not same_claim(own, other)
    missing = next(row for row in result.readings if not row.ours)
    assert missing.comparison_status == "unknown"
    rendered = result.render_for_strategy()
    assert "capability remains unknown" in rendered
    assert "field is ahead" not in rendered
    assert "Do not infer a missing capability or competitor superiority" in rendered


@pytest.mark.parametrize(("left", "right", "reason"), [
    ("Pro plan is $29 per user per month", "Pro plan is €29 per user per month", "currency"),
    ("Pro plan is $29 per user per month", "Pro plan is $29 per user per year", "period"),
    ("Pro plan is $29 per user per month", "Pro plan is $29 per workspace per month", "unit"),
    ("Pro plan is $29 per user per month", "Business plan is $29 per user per month", "plan"),
    ("Pro plan is $29 per user per month, billed annually",
     "Pro plan is $29 per user per month, billed monthly", "conditions"),
])
def test_incompatible_price_scope_never_counts_as_equivalent(left, right, reason):
    own, other = _claim(left, ClaimAxis.PRICE), _claim(right, ClaimAxis.PRICE)
    status, explanation = compare_claims(own, other)
    assert status == "potential_difference"
    assert reason in explanation
    assert not same_claim(own, other)
    result = build(ClaimSet(claims=[own]), [_rival("A", other), _rival("B", other)])
    reading = next(row for row in result.readings if row.ours)
    assert reading.territory is Territory.CONTESTED
    assert reading.comparison_status == "potential_difference"


def test_different_amount_on_matching_explicit_terms_is_a_documented_difference():
    own = _claim("Pro plan is $29 per user per month, billed annually", ClaimAxis.PRICE)
    other = _claim("Pro plan is $39 per user per month, billed annually", ClaimAxis.PRICE)
    status, reason = compare_claims(own, other)
    assert status == "documented_difference"
    assert "no value ranking" in reason
    assert not same_claim(own, other)


@pytest.mark.parametrize(("left", "right"), [
    ("Pro is $29 per month", "Pro is $29 per month"),
    ("Document export is included in the Pro plan at $29 per user per month",
     "Document export costs $29 per user per month on the Pro plan"),
])
def test_missing_price_scope_and_included_feature_are_not_equivalent_prices(left, right):
    assert compare_claims(_claim(left, ClaimAxis.PRICE), _claim(right, ClaimAxis.PRICE))[0] == "potential_difference"


def test_equivalent_explicit_prices_can_be_shared_without_deduction_of_superiority():
    text = "Pro plan is $29 per user per month, billed annually"
    own = _claim(text, ClaimAxis.PRICE)
    other = _claim(text, ClaimAxis.PRICE)
    assert same_claim(own, other)
    result = build(ClaimSet(claims=[own]), [_rival("A", other), _rival("B", other)])
    reading = next(row for row in result.readings if row.ours)
    assert reading.territory is Territory.TABLE_STAKES
    assert reading.comparison_status == "equivalent"


def test_exporting_different_objects_or_formats_is_not_the_same_proposition():
    email = _claim("Export emails as HTML", ClaimAxis.CONTROL)
    contacts = _claim("Export contacts as CSV", ClaimAxis.CONTROL)
    plain = _claim("Copy email text for use elsewhere", ClaimAxis.CONTROL)
    assert not same_claim(email, contacts)
    assert not same_claim(email, plain)


def test_opposite_assertions_with_the_same_vocabulary_are_not_equivalent():
    own = _claim("No data leaves your VPC", ClaimAxis.SECURITY)
    other = _claim("Data leaves your VPC", ClaimAxis.SECURITY)
    status, reason = compare_claims(own, other)
    assert status == "potential_difference"
    assert "polarity" in reason


def test_two_prices_in_one_excerpt_do_not_license_a_first_amount_comparison():
    own = _claim("Pro plan is $29 per user per month", ClaimAxis.PRICE)
    other = own.model_copy(update={
        "verbatim": "Pro plan is $29 per user per month; Business plan is $49 per user per month.",
    })
    assert not same_claim(own, other)
    assert compare_claims(own, other)[0] == "potential_difference"


def test_vendor_comparison_is_attributed_even_when_quote_and_scope_match():
    own = _claim("Pro plan is $29 per user per month", ClaimAxis.PRICE)
    other = own.model_copy(update={"context": EvidenceContext(
        source_kind="vendor_comparison", claim_scope="comparison", subject="Another vendor",
    )})
    status, reason = compare_claims(own, other)
    assert status == "potential_difference"
    assert "attributed" in reason
    assert "not independently established" in other.render()


def test_knowledge_context_and_distinct_price_conditions_survive_map_and_rebuild():
    entries = [Evidence(
        id=f"E{index}", kind=EvidenceKind.PRICE,
        claim=text, verbatim=text, source="pricing",
        context=EvidenceContext(source_kind="official_documentation", claim_scope="offer",
                                temporal_scope="Published 2026", conditions=condition),
    ) for index, (text, condition) in enumerate([
        ("Pro plan is $29 per user per month, billed annually", "annual commitment"),
        ("Pro plan is $29 per user per month, billed monthly", "monthly billing"),
    ])]
    ours = claims_from_knowledge(KnowledgeArtifacts(evidence=EvidenceLedger(entries=entries)))
    assert len(ours.claims) == 2
    assert ours.claims[0].context.temporal_scope == "Published 2026"
    rival = _rival("A", _claim("Export invoices as CSV", ClaimAxis.CONTROL))
    original = build(ours, [rival])
    updated = rebuild(original, [rival])
    assert [row.model_dump() for row in updated.readings] == [row.model_dump() for row in original.readings]


def test_shared_category_nouns_do_not_make_a_functional_explanation_generic():
    text = "Filter invoices by status, export matching records as CSV and send the file to accounting."
    own = _claim(text, ClaimAxis.OTHER)
    positioning = build(ClaimSet(claims=[own]), [_rival("A", own), _rival("B", own)])
    assert next(row for row in positioning.readings if row.ours).territory is Territory.TABLE_STAKES
    report = check(subject="Export the invoices", preview="", body=text, positioning=positioning)
    assert report.passed
    assert not report.advisory
    assert "%" not in report.summary()


def test_multiple_propositions_on_one_axis_do_not_overwrite_radar_history():
    price = _claim("Pro plan is $29 per user per month", ClaimAxis.PRICE)
    returns = _claim("Free shipping on orders over $40", ClaimAxis.PRICE)
    ours = ClaimSet(claims=[price, returns])
    rivals = [_rival("A", price)]
    result = build(ours, rivals)
    assert len([row for row in result.readings if row.axis is ClaimAxis.PRICE]) == 2
    snapshot = MarketSnapshot(positioning=result, rivals=rivals)
    assert diff(snapshot, snapshot) == []


def test_legacy_category_map_without_profiles_cannot_preserve_a_parity_verdict():
    legacy = PositioningMap(rivals_profiled=3, readings=[AxisReading(
        axis=ClaimAxis.PRICE, territory=Territory.TABLE_STAKES,
        ours=[_claim("Free shipping over $40", ClaimAxis.PRICE)],
    )])
    result = rebuild(legacy, [])
    assert result.readings[0].comparison_status == "unknown"
    assert result.readings[0].territory is Territory.CONTESTED
    assert "Rescan" in " ".join(result.notes)
    assert legacy.readings[0].territory is Territory.TABLE_STAKES
