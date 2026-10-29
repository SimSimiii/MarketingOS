"""Failures captured during the homepage-only Plausible audit; no live calls."""

import json
from uuid import uuid4

import pytest

from app.knowledge.artifacts import KnowledgeArtifacts, OfferSheet, Plan, Provenance
from app.knowledge.decision_context import select_evidence
from app.knowledge.ledger import Evidence, EvidenceContext, EvidenceKind, EvidenceLedger
from app.market.audience_research import AudienceResearch
from app.market.capabilities import (
    CapabilityEvidence,
    ProductCapability,
    ProductCapabilityProfile,
    derive_capability_profile,
)
from app.market.positioning import PositioningMap
from app.market.relevance import (
    RankedRelevanceProposal,
    RelevanceProposal,
    _product_context,
    _short_sentence,
    normalize_dossier,
)


@pytest.mark.parametrize("query,claim", [
    ("Capture readers into a list for direct sales", "Chaque inscription au tunnel ajoute automatiquement le contact à la liste."),
    ("Vente de livres physiques avec paiement", "Sell physical books with payment collection."),
])
def test_cross_language_mechanism_competes_under_the_same_retrieval_budget(query, claim):
    relevant = Evidence(id="Z", kind=EvidenceKind.FEATURE, claim=claim, verbatim=claim,
                        context=EvidenceContext(claim_scope="capability", source_kind="official_documentation"))
    distractors = [Evidence(id=f"A{i}", kind=EvidenceKind.FEATURE,
                           claim="A branded direct reader page", verbatim="A branded direct reader page") for i in range(12)]
    selected = select_evidence(EvidenceLedger(entries=[*distractors, relevant]), query, cap=3)
    assert "Z" in selected.ledger.ids and len(selected.ledger.entries) == 3
    assert selected.ledger.get("Z").verbatim == claim


def test_mandatory_conditions_do_not_hide_the_list_capture_mechanism():
    assigned = Evidence(id="REQUIRED", kind=EvidenceKind.FEATURE, claim="Product catalogue",
                        verbatim="Product catalogue", source="docs",
                        context=EvidenceContext(subject="Platform"))
    limits = [Evidence(id=f"LIMIT{i}", kind=EvidenceKind.FEATURE, claim=f"Boundary {i}",
                       verbatim=f"Boundary {i}", source="docs",
                       context=EvidenceContext(subject="Platform", limitations="Keep this limit")) for i in range(5)]
    capture = Evidence(id="CAPTURE", kind=EvidenceKind.FEATURE,
                       claim="Une personne inscrite via un tunnel est automatiquement ajoutée à la liste email.",
                       verbatim="Une personne inscrite via un tunnel est automatiquement ajoutée à la liste email.",
                       context=EvidenceContext(claim_scope="capability", source_kind="official_documentation"))
    selected = select_evidence(EvidenceLedger(entries=[assigned, *limits, capture]),
                               "Build an owned reader list", preferred_ids=["REQUIRED"], cap=3)
    assert {"REQUIRED", "CAPTURE", *(entry.id for entry in limits)} <= selected.ledger.ids


def test_review_payload_can_inform_a_decision_without_becoming_the_publishers_hardware():
    assigned = Evidence(id="REQUIRED", kind=EvidenceKind.FEATURE, claim="Publisher comparison table",
                        verbatim="Publisher comparison table", source="docs",
                        context=EvidenceContext(subject="Review publisher"))
    limits = [Evidence(id=f"LIMIT{i}", kind=EvidenceKind.FEATURE, claim=f"Boundary {i}",
                       verbatim=f"Boundary {i}", source="docs",
                       context=EvidenceContext(subject="Review publisher", limitations="Keep the boundary")) for i in range(5)]
    review = Evidence(id="ROOM", kind=EvidenceKind.FEATURE,
                      claim="The reviewed Model A has stronger daytime glare than Model B in a bright room.",
                      verbatim="Model A has stronger daytime glare than Model B in a bright room.",
                      context=EvidenceContext(subject="Model A", source_kind="third_party", claim_scope="comparison"))
    ledger = EvidenceLedger(entries=[assigned, *limits, review])
    selected = select_evidence(ledger, "TV shopping", preferred_ids=["REQUIRED"], cap=3,
                               problem_queries=["Compare bright room glare before choosing a television"])
    assert "ROOM" in selected.ledger.ids
    assert selected.ledger.get("ROOM").context.subject == "Model A"
    profile = derive_capability_profile(ledger, knowledge_id=uuid4(), knowledge_version=1,
                                        company_name="Review publisher")
    assert not any(ref.evidence_id == "ROOM" for item in profile.capabilities for ref in item.evidence)


def test_an_integration_page_does_not_make_every_other_integrations_limits_mandatory():
    facts = [Evidence(
        id=f"E{i:02}", kind=EvidenceKind.INTEGRATION,
        claim=f"Integration with tool {i}", verbatim=f"Connect tool {i}",
        source="https://example.com/integrations",
        context=EvidenceContext(subject=f"tool {i}", limitations="Community maintained"),
    ) for i in range(60)]
    selected = select_evidence(EvidenceLedger(entries=facts), "integration", preferred_ids=["E00"], cap=5)
    assert len(selected.ledger.entries) == 5
    assert "E00" in selected.ledger.ids


def test_same_subject_limits_remain_mandatory_even_beyond_budget():
    facts = [Evidence(id="E1", kind=EvidenceKind.FEATURE, claim="Export records",
                      verbatim="Export records", source="docs",
                      context=EvidenceContext(subject="Exports")),
             Evidence(id="E2", kind=EvidenceKind.FEATURE, claim="Only new records",
                      verbatim="Only new records", source="docs",
                      context=EvidenceContext(subject="Exports", limitations="No history"))]
    selected = select_evidence(EvidenceLedger(entries=facts), "exports", preferred_ids=["E1"], cap=1)
    assert selected.ledger.ids == {"E1", "E2"}


def test_late_lead_and_withheld_fact_survive_background_rankings():
    facts = [Evidence(id=f"E{i}", kind=EvidenceKind.FEATURE, claim=f"Fact {i}",
                      verbatim=f"Fact {i}") for i in range(34)]
    proposal = RelevanceProposal(ranked_relevance=[
        RankedRelevanceProposal(evidence_id=e.id, band=("LEAD" if i == 32 else
                                "WITHHOLD" if i == 33 else "CONTEXT"), why="Relevant fact")
        for i, e in enumerate(facts)
    ])
    dossier = normalize_dossier(
        proposal, ledger=EvidenceLedger(entries=facts),
        research=AudienceResearch(audience_name="Public web teams", candidate_kind="core"),
        positioning=PositioningMap(), knowledge_id=uuid4(), knowledge_version=1,
        research_id=uuid4(), research_version=1, market_scan_id=uuid4(), market_scan_version=1,
    )
    assert len(dossier.ranked_relevance) == 30
    assert {"E32", "E33"} <= {r.evidence_id for r in dossier.ranked_relevance}
    assert dossier.ranked_relevance[0].evidence_id == "E32"


def test_explanation_is_not_silently_cut_mid_clause():
    text = "Enterprise limits are custom and must be scoped with the vendor before comparing the reporting workload to any published plan capacity."
    actual, _ = _short_sentence(text, limit=80)
    assert actual == text


@pytest.mark.parametrize("reverse", [False, True])
def test_full_capability_catalogue_leaves_room_for_the_audiences_plan_price(reverse):
    facts = [Evidence(id=f"E{i:02}", kind=EvidenceKind.FEATURE,
                      claim=f"Export archive format {i}", verbatim=f"Export archive format {i}")
             for i in range(70)]
    facts += [Evidence(id="REQUIRED", kind=EvidenceKind.INTEGRATION,
                       claim="Signup forms send emails to an existing list",
                       verbatim="Signup forms send emails to an existing list"),
              Evidence(id="PRICE", kind=EvidenceKind.PRICE,
                       claim="Standard signup forms cost $19 per year",
                       verbatim="Standard signup forms cost $19 per year")]
    capabilities = [ProductCapability(
        id=f"cap_{entry.id.lower()}", label=entry.claim,
        evidence=[CapabilityEvidence(evidence_id=entry.id, claim=entry.claim, quote=entry.verbatim)],
    ) for entry in facts if entry.kind != EvidenceKind.PRICE]
    if reverse:
        facts.reverse()
        capabilities.reverse()
    profile = ProductCapabilityProfile(knowledge_id=uuid4(), knowledge_version=1,
                                       capabilities=capabilities)
    context = json.loads(_product_context(
        KnowledgeArtifacts(evidence=EvidenceLedger(entries=facts)), profile.knowledge_id, 1,
        capability_profile=profile, required_capability_ids=["cap_required"],
        query="Signup forms for an affordable email list launch page",
    ))
    selected = {entry["id"] for entry in context["selected_evidence_ledger"]}
    assert len(selected) == 48
    assert {"REQUIRED", "PRICE"} <= selected
    assert "24 others remain" in context["evidence_selection"]


@pytest.mark.parametrize("verified", [True, False])
@pytest.mark.parametrize("ellipsis", ["", "...", "…"])
def test_ancillary_price_does_not_displace_a_verified_offer_plan(verified, ellipsis):
    quote = "$19/month Up to 100,000 monthly pageviews"
    facts = [Evidence(id=f"F{i}", kind=EvidenceKind.FEATURE,
                      claim="Analytics agencies need simple site reports",
                      verbatim="Analytics agencies need simple site reports") for i in range(65)]
    facts += [Evidence(id="AGENCY", kind=EvidenceKind.PRICE,
                       claim="Analytics agencies pay an additional fee for site reports",
                       verbatim="Analytics agencies pay an additional fee for site reports"),
              Evidence(id="BASE", kind=EvidenceKind.PRICE, claim="Starter plan",
                       verbatim=quote, source="https://example.com/pricing")]
    artifacts = KnowledgeArtifacts(evidence=EvidenceLedger(entries=facts), offer=OfferSheet(plans=[
        Plan(name="Starter", price="$19/month", provenance=Provenance(
            source="https://example.com/pricing",
            quote=(quote if verified else "$99/month for every site")
                  + (f" {ellipsis} Another selected-plan summary" if ellipsis else ""),
        )),
    ]))
    context = json.loads(_product_context(artifacts, uuid4(), 1,
        query="Analytics agencies need simple site reports"))
    selected = {entry["id"] for entry in context["selected_evidence_ledger"]}
    assert len(selected) == 48
    assert "AGENCY" in selected
    assert ("BASE" in selected) is verified
