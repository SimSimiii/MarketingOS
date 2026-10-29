"""Positioning must not turn missing extraction or limitations into advantages."""

import pytest

from app.knowledge.artifacts import KnowledgeArtifacts
from app.knowledge.ledger import Evidence, EvidenceKind, EvidenceLedger
from app.market.claims import Claim, ClaimAxis, ClaimSet
from app.market.positioning import (
    AxisReading,
    PositioningMap,
    Territory,
    axis_for_evidence,
    build,
    claims_from_knowledge,
    rebuild,
)
from app.market.rivals import RivalProfile


def _claim(text: str, axis: ClaimAxis) -> Claim:
    return Claim(text=text, verbatim=text, axis=axis, specific=False, source="https://example.com")


def _rival(*claims: Claim, verified: bool = True) -> RivalProfile:
    return RivalProfile(name="Alternative", verified=verified, claims=ClaimSet(claims=list(claims)))


@pytest.mark.parametrize("quote", [
    "After finalizing your email, choose either to 'Copy' the text for use elsewhere.",
    "Send emails with our tool, or export to your own ESP.",
    "Export emails as HTML to your existing sending tool.",
])
def test_verified_portability_counts_even_when_extraction_labels_it_effort(quote: str):
    ours = ClaimSet(claims=[_claim("Export emails as HTML", ClaimAxis.CONTROL)])
    original = _claim(quote, ClaimAxis.EFFORT)
    rival = _rival(original)

    result = build(ours, [rival])

    control = next(row for row in result.readings if row.axis is ClaimAxis.CONTROL)
    assert control.territory is not Territory.OPEN
    assert control.theirs["Alternative"][0].verbatim == quote
    assert control.theirs["Alternative"][0].source == original.source
    assert original.axis is ClaimAxis.EFFORT, "Do not rewrite the saved extraction"


@pytest.mark.parametrize("quote", [
    "Generate email copy from a product brief.",
    "Copy text from elsewhere to get started.",
    "We cannot export emails to your own ESP.",
    "We do not support export to your own ESP.",
])
def test_copywriting_import_and_unsupported_export_do_not_establish_portability(quote: str):
    ours = ClaimSet(claims=[_claim("Export emails as HTML", ClaimAxis.CONTROL)])
    result = build(ours, [_rival(_claim(quote, ClaimAxis.EFFORT))])
    control = next(row for row in result.readings if row.axis is ClaimAxis.CONTROL)
    assert control.rivals_claiming == 0


def test_unverified_portability_is_still_excluded():
    ours = ClaimSet(claims=[_claim("Export emails as HTML", ClaimAxis.CONTROL)])
    result = build(ours, [_rival(_claim("Export emails as HTML", ClaimAxis.EFFORT), verified=False)])
    assert result.is_empty


@pytest.mark.parametrize(("text", "kind"), [
    ("A generation can take several minutes.", EvidenceKind.FEATURE),
    ("Quality for every sector has not been established.", EvidenceKind.FEATURE),
    ("It does not guarantee opens, clicks or revenue.", EvidenceKind.GUARANTEE),
    (
        (
            "MarketingOS does not send emails, publish campaigns, or guarantee opens, clicks, "
            "revenue or conversions."
        ),
        EvidenceKind.GUARANTEE,
    ),
    ("No public subscription price is established.", EvidenceKind.PRICE),
])
def test_limitations_remain_in_knowledge_but_do_not_become_positive_market_claims(text, kind):
    artifacts = KnowledgeArtifacts(evidence=EvidenceLedger(entries=[
        Evidence(id="E1", claim=text, verbatim=text, kind=kind),
    ]))
    assert not claims_from_knowledge(artifacts).claims
    assert artifacts.evidence.entries[0].verbatim == text


@pytest.mark.parametrize("text", [
    "No monthly fees.",
    "We do not charge monthly fees and offer a 30-day money-back guarantee.",
    "No data leaves your VPC.",
    "30-day money-back guarantee.",
    "First result in under five minutes.",
])
def test_supported_negative_wording_and_specific_benefits_are_kept(text: str):
    artifacts = KnowledgeArtifacts(evidence=EvidenceLedger(entries=[
        Evidence(id="E1", claim=text, verbatim=text, kind=EvidenceKind.FEATURE),
    ]))
    assert [item.text for item in claims_from_knowledge(artifacts).claims] == [text]


def test_open_ground_is_explicitly_a_capture_hypothesis_not_exclusivity():
    result = build(
        ClaimSet(claims=[_claim("Export emails as HTML", ClaimAxis.CONTROL)]),
        [_rival(_claim("Fast setup", ClaimAxis.SPEED))],
    )
    rendered = result.render_for_strategy()
    assert "hypothesis to verify" in rendered
    assert "extraction omissions remain unknown" in rendered
    assert "nobody else claims it" not in rendered
    assert "no competing claim captured" in rendered


def test_empty_claim_extraction_does_not_prove_a_field_has_no_capabilities():
    rendered = build(ClaimSet(), [_rival()]).render_for_strategy()
    assert "No comparable claims were captured" in rendered
    assert "Nobody in this field makes a checkable claim" not in rendered


def test_saved_claims_can_be_recomputed_without_mutating_the_historical_map():
    ours = _claim("Export emails as HTML", ClaimAxis.CONTROL)
    old = PositioningMap(rivals_profiled=1, readings=[
        AxisReading(axis=ClaimAxis.CONTROL, territory=Territory.OPEN, ours=[ours]),
    ], notes=["Original capture note"])
    original = old.model_dump(mode="json")

    updated = rebuild(old, [_rival(_claim("Export emails as HTML", ClaimAxis.EFFORT))])

    control = next(row for row in updated.readings if row.axis is ClaimAxis.CONTROL)
    assert control.territory is not Territory.OPEN
    assert updated.notes == ["Original capture note"]
    assert old.model_dump(mode="json") == original


def test_multi_axis_quotes_are_not_duplicated_when_rebuilding_twice():
    quote = "Export emails as HTML"
    original = build(ClaimSet(claims=[_claim(quote, ClaimAxis.EFFORT)]), [_rival()])
    updated = rebuild(original, [_rival()])
    control = next(row for row in updated.readings if row.axis is ClaimAxis.CONTROL)
    assert len(control.ours) == 1


@pytest.mark.parametrize("claim", [
    "20,000 creators, SaaS companies and freelancers use Example.",
    "Over 50,000 businesses trust Example.",
])
def test_adoption_count_does_not_inherit_speed_from_vendor_tagline(claim):
    entry = Evidence(id="E1", kind=EvidenceKind.METRIC, claim=claim,
                     verbatim=claim + " They are growing faster with us.")
    assert axis_for_evidence(entry) is ClaimAxis.PROOF


def test_timed_multi_user_capability_is_still_speed():
    entry = Evidence(id="E1", kind=EvidenceKind.METRIC,
                     claim="20 users can get a report in 10 seconds.",
                     verbatim="20 users can get a report in 10 seconds.")
    assert axis_for_evidence(entry) is ClaimAxis.SPEED


def test_category_vocabulary_excludes_bare_counts_but_keeps_named_standards():
    first = _rival(_claim("SOC2 certified. 500 customers. 000+ 600 reports.", ClaimAxis.SECURITY))
    second = first.model_copy(update={"name": "Another"})
    result = build(ClaimSet(), [first, second])
    assert "soc2" in result.crowd_words
    assert not {"500", "000+", "600"}.intersection(result.crowd_words)
