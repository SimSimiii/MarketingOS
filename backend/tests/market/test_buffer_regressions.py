"""Failure mechanisms observed in the Buffer homepage audit, without models."""

from uuid import uuid4

from app.knowledge.artifacts import KnowledgeArtifacts, OfferSheet
from app.knowledge.ledger import Evidence, EvidenceContext, EvidenceLedger
from app.market.capabilities import (
    derive_capability_profile,
    licenses,
    normalize_capability_profile,
)
from app.market.claims import Claim, ClaimAxis, ClaimSet, comparable_claim, is_own_assertion
from app.market.positioning import AxisReading, PositioningMap, axis_for_evidence
from app.market.rivals import RivalProfile, review_rationale


def fact(identifier, claim, *, subject="Buffer", scope="capability", category="product"):
    return Evidence(id=identifier, kind="feature", claim=claim, verbatim=claim,
                    category=category, context=EvidenceContext(
                        subject=subject, claim_scope=scope, source_kind="official_documentation"))


def test_offer_guarantees_use_quotations_not_a_compilers_inverted_summary():
    actual = fact("E238", "If you upgrade to a paid plan, you pay for every connected channel, "
                  "including channels previously on the Free plan.", scope="offer")
    forged = actual.model_copy(update={"claim": "Keep your three free channels if you upgrade"})
    raw = {"offer": {"guarantees": [forged.claim]},
           "evidence": EvidenceLedger(entries=[forged]).model_dump(mode="json")}
    checked = KnowledgeArtifacts.model_validate(raw)
    assert checked.offer.guarantees == []
    assert "omitted" in checked.notes[-1]
    assert raw["offer"]["guarantees"] == [forged.claim]
    assert checked.evidence.entries[0].verbatim == actual.verbatim


def test_a_licensed_clause_keeps_the_full_exception_and_is_idempotent():
    actual = fact("G", "Cancel any time, but annual payments are non-refundable.", scope="offer")
    actual.context.conditions = "Refunds require approval."
    artifacts = KnowledgeArtifacts(offer=OfferSheet(guarantees=["Cancel any time"]),
                                   evidence=EvidenceLedger(entries=[actual]))
    assert artifacts.offer.guarantees == [actual.verbatim + "; Refunds require approval."]
    reread = KnowledgeArtifacts.model_validate(artifacts.model_dump(mode="json"))
    assert reread.offer == artifacts.offer
    assert reread.notes == artifacts.notes


def test_ordinary_offer_paraphrase_is_replaced_with_the_actual_conditional_quote():
    actual = fact("G", "Yes, we offer a 14-day free trial for our paid plans. "
                  "After the trial you must select a plan.", scope="offer")
    artifacts = KnowledgeArtifacts(offer=OfferSheet(guarantees=["14-day free trial on paid plans"]),
                                   evidence=EvidenceLedger(entries=[actual]))
    assert artifacts.offer.guarantees == [actual.verbatim]
    assert "After the trial" in artifacts.offer.guarantees[0]
    invalid = KnowledgeArtifacts(offer=OfferSheet(guarantees=["140-day free trial on paid plans"]),
                                 evidence=EvidenceLedger(entries=[actual]))
    assert invalid.offer.guarantees == []


def test_product_catalogue_requires_the_product_owner_and_a_capability_scope():
    entries = [
        fact("ok", "Buffer schedules posts across social channels."),
        fact("integration", "Buffer API connects to external publishing workflows.", subject="Buffer API"),
        fact("company", "Buffer has a CEO in Chicago.", category="company"),
        fact("unknown", "Buffer can probably automate publishing.", scope="unknown"),
        fact("third", "WriteStack schedules Substack Notes using Buffer.", subject="WriteStack"),
        fact("outcome", "A customer doubled sales using Buffer.", scope="customer_outcome"),
    ]
    ledger = EvidenceLedger(entries=entries)
    profile = derive_capability_profile(ledger, knowledge_id=uuid4(), knowledge_version=1,
                                        company_name="Buffer")
    assert {c.evidence[0].evidence_id for c in profile.capabilities} == {"ok", "integration"}

    # Old snapshots remain unchanged, while read-time validation demotes a
    # formerly admitted fact when the product owner is known.
    third = derive_capability_profile(EvidenceLedger(entries=[entries[4]]),
                                      knowledge_id=uuid4(), knowledge_version=1)
    original = third.model_dump(mode="json")
    checked = normalize_capability_profile(third, ledger=ledger, knowledge_id=third.knowledge_id,
                                           knowledge_version=1, company_name="Buffer")
    assert checked.capabilities[0].state == "unknown"
    assert not checked.capabilities[0].evidence
    assert third.model_dump(mode="json") == original
    renamed = third.capabilities[0].model_copy(update={"id": "manual_workflow", "origin": "maintained"})
    assert not licenses(entries[4], renamed, company_name="Buffer")


def test_customer_revenue_cannot_be_compared_to_a_monthly_subscription():
    revenue = fact("revenue", "WriteStack earns $9,300 in monthly recurring revenue.",
                   subject="WriteStack", scope="customer_outcome", category="proof")
    assert axis_for_evidence(revenue) is ClaimAxis.PROOF
    price = Claim(text="Pro plan costs $9,300 per month", axis="price")
    wrongly_tagged = Claim(text=revenue.claim, verbatim=revenue.verbatim,
                          axis="price", context=revenue.context)
    assert not comparable_claim(wrongly_tagged, price)
    assert not comparable_claim(wrongly_tagged, wrongly_tagged)
    legacy = Claim(text="A customer generated $2 million in sales per year", axis="price")
    assert not comparable_claim(legacy, price)


def test_api_rate_limits_describe_capacity_instead_of_execution_speed():
    limit = fact("limit", "Buffer API has a 15-minute rate limit of 100 requests.")
    assert axis_for_evidence(limit) is ClaimAxis.BREADTH
    latency = fact("latency", "Buffer publishes the request in 2 seconds.")
    assert axis_for_evidence(latency) is ClaimAxis.SPEED


def test_third_party_workflows_do_not_become_our_positioning_promises():
    third = fact("third", "WriteStack handles publishing using Buffer.", subject="WriteStack")
    claim = Claim(text=third.claim, verbatim=third.verbatim, context=third.context)
    assert not is_own_assertion(claim, company_name="Buffer")
    owned = claim.model_copy(update={"context": EvidenceContext(
        subject="Buffer API", claim_scope="capability")})
    assert is_own_assertion(owned, company_name="Buffer")


def test_unmatched_captures_do_not_become_open_ground_in_the_summary():
    result = PositioningMap(rivals_profiled=2, readings=[AxisReading(axis="price", territory="open")])
    assert "0 documented difference(s)" in result.summary()
    assert "need verification" in result.summary()
    assert "potential open ground" not in result.summary()


def test_synthesized_rival_price_range_cannot_hide_an_entry_plan():
    profile = RivalProfile(name="Rival", verified=True, why="Rival costs $199–$399 per seat.",
                           rationale_status="source_linked_hypothesis", claims=ClaimSet(claims=[
        Claim(text="Essentials costs $79", verbatim="Essentials $79 per seat/month", axis="price"),
        Claim(text="Standard costs $199", verbatim="Standard $199 per seat/month", axis="price"),
        Claim(text="Advanced costs $399", verbatim="Advanced $399 per seat/month", axis="price"),
    ]))
    checked = review_rationale(profile)
    assert checked.why == ""
    assert checked.rationale_status == "unverified"
    assert "price range" in checked.note
    assert profile.why == "Rival costs $199–$399 per seat."
    explicit = profile.model_copy(update={"claims": ClaimSet(claims=[
        Claim(text="Range", verbatim="Higher plans range from $199–$399 per seat.", axis="price"),
    ])})
    assert review_rationale(explicit).why == explicit.why
