"""Regression cases for evidence surviving refreshes without changing its meaning."""

from uuid import uuid4

import pytest
from sqlmodel import Session

from app.knowledge.artifacts import (
    AudienceModel,
    Fact,
    Grounding,
    KnowledgeArtifacts,
    Objection,
    Provenance,
    Segment,
)
from app.knowledge.ledger import Evidence, EvidenceKind, EvidenceLedger
from app.market.audience_discovery import current_map, merge_research_evidence, rank_assessment
from app.market.audience_research import SourceTier
from app.market.capabilities import (
    CapabilityEvidence,
    CapabilityProfileDraft,
    CapabilityState,
    ProductCapability,
    ProductCapabilityProfile,
    normalize_capability_profile,
)
from app.market.demand import (
    DemandMap,
    MapAssessment,
    MapEvidence,
    MapOptions,
    audience_fingerprint,
)
from app.market.store import MarketStore
from app.models.knowledge_artifacts import KnowledgeArtifactSet
from tests.market.test_audience_discovery import (
    PAGES,
    candidate,
    profile,
    research,
    run_map,
    unreported,
)
from tests.market.test_audience_research import database


@pytest.mark.asyncio
async def test_literal_report_links_need_no_recovery_model(provider, session):
    answer = unreported(reading="Read [these pages](" + PAGES[0].final_url + ").\n"
                        + "\n".join(item.final_url for item in PAGES[1:]))
    result = await run_map(provider, session, answer=answer)
    assert provider.calls["audience_map_sources"] == 0
    assert len(result.segments[0].assessment.evidence) == 3


@pytest.mark.asyncio
async def test_recovery_cannot_turn_an_unfetched_page_into_evidence(provider, session):
    provider.push("audience_map_sources", {"source_urls": ["https://missing.example/post"]})
    result = await run_map(provider, session, answer=unreported())
    assert not result.segments[0].assessment.evidence
    assert provider.calls["audience_map_validate"] == 0
    assert "could be read" in result.validation_note


@pytest.mark.parametrize("changes", [
    {"workflow": "Wholesale inventory purchasing"},
    {"organization": "Hospitals"},
    {"need": "Schedule patient appointments"},
    {"who": "A different buying situation"},
])
def test_same_name_never_transfers_research_to_a_changed_situation(changes):
    result = merge_research_evidence(
        DemandMap(segments=[candidate(**changes)]),
        {candidate().name.casefold(): research()}, profile(),
    )
    assert not result.segments[0].assessment.evidence
    assert "different or unverified" in " ".join(result.segments[0].assessment.unknowns)


def test_fingerprint_ignores_display_name_but_tracks_membership():
    original = candidate()
    assert audience_fingerprint(original) == audience_fingerprint(candidate(name="New label"))
    changed = candidate()
    changed.definition.max_team_size = 3
    assert audience_fingerprint(original) != audience_fingerprint(changed)


def test_legacy_research_needs_its_original_definition_and_scope():
    engine, brand_id = database()
    with Session(engine) as session:
        store = MarketStore(session)
        original = store.save_map(brand_id, DemandMap(segments=[candidate()]))
        saved = store.save_research(
            brand_id, research(audience_fingerprint="", definition=candidate().definition), original,
        )
        assert store.latest_map(brand_id).segments[0].assessment.evidence
        assert store.latest_research(brand_id, candidate().name) is not None
        assert not saved.payload["audience_fingerprint"]  # read-only legacy upgrade
        store.save_map(brand_id, DemandMap(segments=[candidate(workflow="Another workflow")]))
        assert not store.latest_map(brand_id).segments[0].assessment.evidence
        assert store.latest_research(brand_id, candidate().name) is None
        store.save_map(brand_id, DemandMap(segments=[candidate()], options=MapOptions(geography="France")))
        assert not store.latest_map(brand_id).segments[0].assessment.evidence


def test_untraceable_legacy_research_does_not_raise_the_map_rank():
    engine, brand_id = database()
    with Session(engine) as session:
        store = MarketStore(session)
        store.save_map(brand_id, DemandMap(segments=[candidate()]))
        store.save_research(brand_id, research(audience_fingerprint=""), None)
        result = store.latest_map(brand_id)
        assert not result.segments[0].assessment.evidence


def test_research_does_not_count_interpretation_as_a_second_buyer_voice():
    found = research()
    found.sources[1].tier = SourceTier.INTERPRETATION
    result = merge_research_evidence(
        DemandMap(segments=[candidate()]), {candidate().name.casefold(): found}, profile(),
    )
    assert result.segments[0].assessment.evidence_strength == "limited"


def assessed_with_counterevidence(impact, reason):
    segment = candidate(assessment=MapAssessment(compatibility="supported", evidence=[
        MapEvidence(claim="Need", quote=page.content, url=page.final_url,
                    kind="access" if index == 2 else "need")
        for index, page in enumerate(PAGES)
    ]))
    segment.assessment.evidence.append(MapEvidence(
        claim="Existing systems impose a switching cost", quote="Switching takes a full month.",
        url="https://buyers.example/switching", kind="counterevidence",
        impact=impact, impact_reason=reason,
    ))
    rank_assessment(segment)
    return segment


@pytest.mark.parametrize("impact,reason,priority", [
    ("minor", "A documented, optional training step", "explore_first"),
    ("minor", "", "review_first"),
    ("material", "Migration is longer than the buying deadline", "review_first"),
    ("unknown", "", "review_first"),
])
def test_counterevidence_distinguishes_minor_from_material_without_excluding(impact, reason, priority):
    segment = assessed_with_counterevidence(impact, reason)
    assert segment.assessment.priority == priority
    assert segment.assessment.compatibility == "supported"
    assert segment.assessment.counterevidence == 1


def test_profile_correction_unblocks_prior_exclusion_and_clears_stale_messages():
    segment = assessed_with_counterevidence("minor", "An optional onboarding step")
    old = current_map(DemandMap(segments=[segment]), profile(CapabilityState.UNSUPPORTED))
    assert old.segments[0].assessment.priority == "incompatible"
    fixed = current_map(old, profile())
    assert fixed.segments[0].assessment.priority == "explore_first"
    assert not any("unsupported:" in item for item in fixed.segments[0].assessment.reasons)
    assert old.segments[0].assessment.priority == "incompatible"


def test_copied_quotes_on_different_domains_do_not_create_corroboration():
    segment = assessed_with_counterevidence("minor", "Manageable")
    segment.assessment.evidence[1].quote = segment.assessment.evidence[0].quote
    rank_assessment(segment)
    assert segment.assessment.evidence_strength == "limited"


def capability_with_quote(quote, claim="Guardrails", **changes):
    capability = ProductCapability(
        id="guardrails", label="Guardrails", state="verified",
        evidence=[CapabilityEvidence(evidence_id="E1", claim=claim, quote=quote)],
        **changes,
    )
    ledger = EvidenceLedger(entries=[Evidence(
        id="E1", kind=EvidenceKind.FEATURE, claim=claim, verbatim=quote, source="product.md",
    )])
    return capability, ledger


@pytest.mark.parametrize("quote", [
    "We promise 99.9% uptime.",
    "Guardrails are not supported.",
    "Guardrails are coming soon.",
    "No guardrails are included.",
])
def test_capability_name_in_paraphrase_or_negative_quote_does_not_license_support(quote):
    capability, ledger = capability_with_quote(quote)
    result = normalize_capability_profile(
        CapabilityProfileDraft(capabilities=[capability]), ledger=ledger,
        knowledge_id=uuid4(), knowledge_version=1,
    )
    assert result.state_of("guardrails") is CapabilityState.UNKNOWN
    again = normalize_capability_profile(
        result, ledger=ledger, knowledge_id=result.knowledge_id, knowledge_version=1,
    )
    assert again == result
    assert again.capability("guardrails").unlicensed_evidence_ids == ["E1"]


def test_explicit_aliases_allow_a_product_to_use_its_own_language():
    capability, ledger = capability_with_quote("Protection anti-injection sur chaque appel.",
                                              aliases=["protection anti-injection"])
    result = normalize_capability_profile(
        CapabilityProfileDraft(capabilities=[capability]), ledger=ledger,
        knowledge_id=uuid4(), knowledge_version=1,
    )
    assert result.state_of("guardrails") is CapabilityState.VERIFIED


def test_without_setup_is_not_misread_as_without_the_capability():
    capability, ledger = capability_with_quote("Guardrails run without extra setup.")
    result = normalize_capability_profile(
        CapabilityProfileDraft(capabilities=[capability]), ledger=ledger,
        knowledge_id=uuid4(), knowledge_version=1,
    )
    assert result.state_of("guardrails") is CapabilityState.VERIFIED


def test_existing_profile_is_checked_on_both_read_paths_without_rewriting_it():
    engine, brand_id = database()
    with Session(engine) as session:
        capability, ledger = capability_with_quote("We promise 99.9% uptime.")
        knowledge = KnowledgeArtifactSet(
            brand_id=brand_id, payload=KnowledgeArtifacts(evidence=ledger).model_dump(mode="json"),
        )
        session.add(knowledge)
        session.commit()
        store = MarketStore(session)
        stored = store.save_capability_profile(brand_id, ProductCapabilityProfile(
            knowledge_id=knowledge.id, knowledge_version=1, capabilities=[capability],
        ))
        for result in [store.latest_capability_profile(brand_id), store.capability_profile_for_knowledge(
            brand_id, knowledge_id=knowledge.id, knowledge_version=1,
        )]:
            assert result[1].state_of("guardrails") is CapabilityState.UNKNOWN
        session.refresh(stored)
        assert stored.payload["capabilities"][0]["state"] == "verified"


@pytest.mark.parametrize("kind,source_kind,expected", [
    (EvidenceKind.TESTIMONIAL, "unknown", Grounding.GROUNDED),
    (EvidenceKind.CUSTOMER, "case_study", Grounding.GROUNDED),
    (EvidenceKind.FEATURE, "customer_voice", Grounding.VENDOR_CLAIM),
])
def test_hosting_does_not_override_the_actual_origin_of_a_quote(kind, source_kind, expected):
    quote = "Our team used to spend every Friday answering warranty emails."
    ref = Provenance(source="https://vendor.example/", quote=quote, source_kind=source_kind)
    audience = AudienceModel(segments=[Segment(name="Repair shops", pains=[Fact(
        statement="Repeated warranty questions consume Fridays", grounding=Grounding.GROUNDED,
        provenance=ref,
    )])], objections=[Objection(
        objection="We cannot spare the training time", grounding=Grounding.GROUNDED,
        evidence_ids=["E1"],  # an answer is not proof of this objection
    )])
    artifacts = KnowledgeArtifacts(audience=audience, evidence=EvidenceLedger(entries=[Evidence(
        id="E1", kind=kind, claim="A customer describes their workflow", verbatim=quote,
        source="https://vendor.example/",
    )]))
    assert artifacts.audience.segments[0].pains[0].grounding is expected
    assert artifacts.audience.objections[0].grounding is Grounding.INFERRED
    assert audience.objections[0].grounding is Grounding.GROUNDED  # no mutation of input
    assert KnowledgeArtifacts.model_validate(artifacts.model_dump()) == artifacts
