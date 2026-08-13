"""Claim extraction: what counts as something the copy has to back up."""

import pytest

from app.knowledge.ledger import ClaimKind, extract_claims


def kinds(text: str) -> set[ClaimKind]:
    return {claim.kind for claim in extract_claims(text)}


def normalized(text: str) -> set[str]:
    return {claim.normalized for claim in extract_claims(text)}


@pytest.mark.parametrize(
    ("text", "kind"),
    [
        ("It costs $29 a month", ClaimKind.MONEY),
        ("Cuts review time by 40%", ClaimKind.PERCENT),
        ("Three times faster - a 3x speedup", ClaimKind.MULTIPLIER),
        ("Set up in 10 minutes", ClaimKind.DURATION),
        ("Connects 25 tools", ClaimKind.QUANTITY),
        ("Read more at https://example.com/x", ClaimKind.URL),
    ],
)
def test_quantified_claims_are_extracted(text: str, kind: ClaimKind):
    assert kind in kinds(text)


def test_a_bare_single_digit_is_not_a_claim():
    """"3 reasons to switch" is rhetoric. Demanding evidence for it would make
    the gate noise, and a gate that gets ignored protects nothing."""
    assert extract_claims("There are 3 reasons to switch.") == []


def test_units_and_separators_normalize_to_one_form():
    assert normalized("10 mins") == normalized("10 minutes")
    assert normalized("1,500 credits") == normalized("1500 credits")


def test_a_typed_claim_is_not_double_counted_as_a_bare_quantity():
    claims = extract_claims("It costs $29 a month")
    assert len(claims) == 1
    assert claims[0].kind is ClaimKind.MONEY


def test_a_long_quoted_passage_is_treated_as_an_attributed_quotation():
    claims = extract_claims('She said "this cut our release process down to almost nothing".')
    assert ClaimKind.QUOTE in {claim.kind for claim in claims}


def test_a_short_quoted_phrase_is_not_a_testimonial():
    assert ClaimKind.QUOTE not in kinds('We call it "the boring part".')


def test_two_contractions_in_one_sentence_are_not_a_quotation():
    """A bare apostrophe is not a quote delimiter - it's what every
    contraction uses. Two of them in one sentence must not bound a span the
    gate mistakes for a fabricated testimonial."""
    text = (
        "What you're actually buying isn't model access - it's the RAG, "
        "guardrails, and hosted REST endpoint you'd otherwise spend three "
        "months building yourself."
    )
    assert ClaimKind.QUOTE not in kinds(text)
