"""Cross-product regressions captured by the root-URL functional audit."""

from datetime import UTC, date, datetime
from uuid import uuid4

import pytest

from app.knowledge.artifacts import BusinessProfile, KnowledgeArtifacts, OfferSheet, Plan
from app.knowledge.corpus import Document, SourceCorpus
from app.knowledge.ledger import Evidence, EvidenceContext, EvidenceLedger
from app.market.audience_research import (
    AudienceProblem,
    AudienceResearch,
    EvidenceReference,
    SourceReference,
    review_research_interpretations,
)
from app.market.capabilities import (
    CapabilityEvidence,
    ProductCapability,
    ProductCapabilityProfile,
    derive_capability_profile,
    licenses,
    normalize_capability_profile,
)
from app.market.radar import MarketSnapshot
from app.market.rivals import RivalLead, RivalScout
from app.market.scanner import MarketScanner
from app.market.source_dates import publication_date
from app.models.campaign_execution import CampaignExecution
from app.models.enums import ExecutionStatus
from app.models.market import ProductCapabilityProfileRow
from app.schemas.market import CapabilityProfileRead
from tests.market.conftest import ScriptedCrawler
from tests.market.test_rivals import HOME_PAGE, profile_payload


def test_catalogue_is_product_specific_and_does_not_promote_third_party_integration():
    entries = [Evidence(id="E1", kind="feature", claim="Widget counts visits without cookies",
                        verbatim="Widget counts visits without cookies.",
                        context=EvidenceContext(subject="Widget", claim_scope="capability")),
               Evidence(id="E2", kind="integration", claim="HelpDocs offers a knowledge base",
                        verbatim="Native integration for your knowledge base",
                        context=EvidenceContext(subject="HelpDocs", source_kind="third_party")),
               Evidence(id="E3", kind="feature", claim="Oven schedules dough fermentation",
                        verbatim="Schedule dough fermentation in the oven.",
                        context=EvidenceContext(subject="Oven", claim_scope="capability")),
               Evidence(id="E4", kind="feature", claim="A shop accepts bank transfers",
                        verbatim="Our shop accepts bank transfers.",
                        context=EvidenceContext(subject="Our shop", claim_scope="capability"))]
    profile = derive_capability_profile(EvidenceLedger(entries=entries), knowledge_id=uuid4(), knowledge_version=1)
    assert {cap.label for cap in profile.capabilities} == {entries[i].claim for i in (0, 2, 3)}
    assert profile.capability("knowledge_base") is None
    assert profile.capability("agent_api_keys") is None
    cap = profile.capabilities[0]
    assert licenses(entries[0], cap)
    assert not licenses(entries[0], cap.model_copy(update={"label": "Supports every privacy law"}))
    assert "claims" not in profile.discovery_context()


def test_legacy_generated_profile_is_revalidated_for_api_and_retired_on_rebuild():
    fact = Evidence(id="E1", kind="integration", claim="HelpDocs knowledge base integration",
                    verbatim="Native integration for your knowledge base",
                    context=EvidenceContext(source_kind="third_party", subject="HelpDocs"))
    ledger = EvidenceLedger(entries=[fact])
    old = ProductCapabilityProfile(knowledge_id=uuid4(), knowledge_version=1,
        capabilities=[ProductCapability(id="knowledge_base", label="Knowledge base", state="verified",
            evidence=[CapabilityEvidence(evidence_id=fact.id, claim=fact.claim, quote=fact.verbatim)],
            note="Verified by the current Evidence Ledger.")])
    checked = normalize_capability_profile(old, ledger=ledger, knowledge_id=old.knowledge_id, knowledge_version=1)
    row = ProductCapabilityProfileRow(brand_id=uuid4(), knowledge_id=old.knowledge_id,
        knowledge_version=1, version=1, schema_version=2, payload=old.model_dump(mode="json"))
    dto = CapabilityProfileRead.of(row, checked)
    assert dto.capabilities[0].state == "unknown"
    assert row.payload['capabilities'][0]['state'] == 'verified'
    rebuilt = derive_capability_profile(ledger, knowledge_id=old.knowledge_id, knowledge_version=1, previous=checked)
    assert rebuilt.capability("knowledge_base") is None
    old.capabilities[0].state = "unsupported"
    maintained = derive_capability_profile(ledger, knowledge_id=old.knowledge_id, knowledge_version=1, previous=old)
    assert maintained.capability("knowledge_base").state == "unsupported"


def test_profile_digest_retains_commercial_sections_after_long_feature_introduction():
    text = "# Example\n" + "Feature description with many details. " * 1000
    text += "\n## Starter\n$9/month\n## Growth\n$14/month\n## Business\n$19/month\n"
    corpus = SourceCorpus.from_documents([Document(id="home", title="Home", content=text)])
    digest = corpus.digest(3000)
    assert all(price in digest for price in ("$9", "$14", "$19"))


def test_blank_price_recovery_preserves_conditions_and_does_not_price_inherited_plan():
    fact = Evidence(id="P", kind="price", claim="Business costs $19/month",
                    verbatim="Business $19/month. Includes everything in Growth.",
                    source="https://example.com/pricing",
                    context=EvidenceContext(claim_scope="offer", conditions="Up to 10k monthly pageviews",
                                            temporal_scope="Annual billing only"))
    artifacts = KnowledgeArtifacts(offer=OfferSheet(plans=[Plan(name="Business"), Plan(name="Growth")]),
                                   evidence=EvidenceLedger(entries=[fact]))
    assert artifacts.offer.plans[0].price == "$19/month (Up to 10k monthly pageviews; Annual billing only)"
    assert artifacts.offer.plans[0].provenance.evidence_id == "P"
    assert artifacts.offer.plans[1].price == ""
    conflicting = fact.model_copy(update={"id": "P2", "verbatim": "Business $49/month"})
    assert OfferSheet(plans=[Plan(name="Business")]).recover_prices(
        EvidenceLedger(entries=[fact, conflicting])).plans[0].price == ""


def test_source_publication_metadata_wins_and_copyright_is_not_a_publication_date():
    when = date(2026, 10, 18)
    assert publication_date('<meta property="article:published_time" content="2023-03-27T12:00:00Z">',
                            "https://example.com/2022/01/01/post", when) == (date(2023, 3, 27), "page_publication_metadata")
    assert publication_date('<script type="application/ld+json">{"dateModified":"2026-10-17"}</script>Copyright 2026',
                            "https://example.com/post", when) == (None, "unknown")
    assert publication_date("<p>Post</p>", "https://example.com/2023/03/27/post", when)[0] == date(2023, 3, 27)
    assert publication_date('<script type="application/ld+json">{"related":{"datePublished":"2026-10-17"}}</script>',
                            "https://example.com/post", when) == (None, "unknown")


def test_old_single_article_cannot_look_like_five_current_independent_problems():
    research = AudienceResearch(audience_name="Public teams", candidate_kind="core",
        researched_at=datetime(2026, 10, 18, tzinfo=UTC),
        sources=[SourceReference(id="S1", requested_url="https://example.com/2023/03/27/article",
                                 final_url="https://example.com/2023/03/27/article", tier=1,
                                 fetched_at=datetime(2026, 10, 18, tzinfo=UTC), content_hash="same")],
        problems=[AudienceProblem(id=f"P{i}", statement="A reported problem", corroboration=5,
                                  evidence=[EvidenceReference(source_id="S1", quote="A reported problem")])
                  for i in range(5)])
    reviewed = review_research_interpretations(research)
    assert research.sources[0].published_date is None  # historical row unchanged
    assert reviewed.sources[0].published_date == date(2023, 3, 27)
    assert all(p.source_count == p.corroboration == 1 for p in reviewed.problems)
    assert any("All 5 problems" in note for note in reviewed.interpretation_warnings)
    assert all(any("Historical" in note for note in p.review_notes) for p in reviewed.problems)
    assert review_research_interpretations(reviewed).model_dump() == reviewed.model_dump()


def test_finished_process_with_low_quality_report_has_explicit_degraded_outcome():
    execution = CampaignExecution(campaign_id=uuid4(), status=ExecutionStatus.COMPLETED,
        result={"run_status": "completed", "report": {"delivered": 1, "promised": 1,
                "emails": [{"landed": False, "clean": True}]}})
    assert execution.needs_review
    assert execution.outcome_status == "degraded"
    assert execution.review_reasons
    execution.result['report']['emails'][0]['unresolved'] = ['Argument needs review']
    assert not any('automatic' in reason for reason in execution.review_reasons)
    assert any('strategy or review' in reason for reason in execution.review_reasons)


@pytest.mark.asyncio
async def test_identical_rival_pages_reuse_extraction_but_changed_pages_buy_a_new_call(provider, session):
    provider.push("rival_profile", profile_payload())
    lead = RivalLead(name="Alpha", url="https://alpha.example")
    crawler = ScriptedCrawler({lead.url: [(lead.url, HOME_PAGE)]})
    scout = RivalScout(session, crawler=crawler)
    first = await scout.profile(lead)
    second = await scout.profile(lead, previous=first)
    assert second.reused and len(provider.requests) == 1
    provider.push("rival_profile", profile_payload())
    changed = RivalScout(session, crawler=ScriptedCrawler({lead.url: [(lead.url, HOME_PAGE + "\nA new feature.")]}))
    third = await changed.profile(lead, previous=first)
    assert not third.reused and len(provider.requests) == 2

    # Same pages must not reuse a result extracted with obsolete instructions.
    provider.push("rival_profile", profile_payload())
    session.template_fingerprint = lambda template: "changed-template"
    fourth = await scout.profile(lead, previous=first)
    assert not fourth.reused and len(provider.requests) == 3


@pytest.mark.asyncio
async def test_rival_comparison_retrieves_the_hypothesis_and_all_offer_price_conditions(provider, session):
    facts = [Evidence(id=f"E{i:02}", kind="feature", claim="Privacy analytics reporting",
                      verbatim="Privacy analytics reporting for your website.") for i in range(20)]
    facts.append(Evidence(id="FUNNELS", kind="feature", claim="Funnels and segmentation",
                          verbatim="Funnels and segmentation are supported."))
    for name, amount in (("Starter", 9), ("Growth", 14), ("Business", 19)):
        facts.append(Evidence(id=name, kind="price", claim=f"{name} price",
                     verbatim=f"{name} ${amount}/month", source="https://ours.example/pricing",
                     context=EvidenceContext(claim_scope="offer", conditions="Up to 10k pageviews")))
    own = KnowledgeArtifacts(business=BusinessProfile(what_it_does="Privacy analytics reporting"),
        offer=OfferSheet(plans=[Plan(name=name) for name in ("Starter", "Growth", "Business")]),
        evidence=EvidenceLedger(entries=facts))
    provider.push("rival_profile", profile_payload())
    lead = RivalLead(name="Alpha", url="https://alpha.example", why="Funnels and segmentation")
    await RivalScout(session, crawler=ScriptedCrawler({lead.url: [(lead.url, HOME_PAGE)]})).profile(lead, artifacts=own)
    prompt = provider.requests[0].system_prompt
    assert '"id": "FUNNELS"' in prompt
    assert all(f'"id": "{name}"' in prompt for name in ("Starter", "Growth", "Business"))
    assert "Up to 10k pageviews" in prompt


@pytest.mark.asyncio
async def test_unreadable_app_can_use_discovered_public_page_and_rationale_needs_both_sources(provider, session):
    public = "https://alpha.example/about"
    payload = profile_payload(why="Both products cover this workflow", why_sources=[public], our_evidence_ids=["E1"])
    payload['claims'][1]['source'] = public
    provider.push("rival_profile", payload)
    lead = RivalLead(name="Alpha", url="https://app.alpha.example", why="An unverified contrast", public_urls=[public])
    scout = RivalScout(session, crawler=ScriptedCrawler({public: [(public, HOME_PAGE)]}))
    own = KnowledgeArtifacts(evidence=EvidenceLedger(entries=[Evidence(id="E1", kind="feature",
                             claim="Our product covers this workflow", verbatim="Our product covers this workflow.",
                             source="https://ours.example/docs")]))
    profile = await scout.profile(lead, artifacts=own)
    assert profile.verified
    assert profile.rationale_status == "source_linked_hypothesis"
    assert profile.discovery_reason == lead.why
    assert profile.why != lead.why
    provider.push("rival_profile", {**payload, "our_evidence_ids": ["UNKNOWN"]})
    unchecked = await scout.profile(lead, artifacts=own)
    assert unchecked.why == "" and unchecked.rationale_status == "unverified"
    assert "references to both products" in unchecked.note

    provider.push("rival_profile", {**payload, "why_sources": [public, "https://ours.example/docs"]})
    both = await scout.profile(lead, artifacts=own)
    assert both.rationale_status == "source_linked_hypothesis"
    for urls in (["https://ours.example/docs"], [public, "https://invented.example"]):
        provider.push("rival_profile", {**payload, "why_sources": urls})
        rejected = await scout.profile(lead, artifacts=own)
        assert rejected.why == "" and rejected.rationale_status == "unverified"


@pytest.mark.asyncio
async def test_existing_unreadable_rival_gets_fallback_in_same_discovery_call(provider, session):
    from app.market.rivals import RivalProfile

    public = "https://alpha.example/about"
    provider.push("rival_scan", {"leads": [], "public_pages": {"Alpha": [public]}})
    payload = profile_payload()
    payload['claims'][1]['source'] = public
    provider.push("rival_profile", payload)
    lead = RivalLead(name="Alpha", url="https://app.alpha.example")
    scout = RivalScout(session, crawler=ScriptedCrawler({public: [(public, HOME_PAGE)]}))
    previous = MarketSnapshot(rivals=[RivalProfile(name=lead.name, url=lead.url, verified=False)])
    result = await MarketScanner(session, scout=scout).scan(artifacts=KnowledgeArtifacts(),
                                                          known=[lead], previous=previous)
    assert result.snapshot.rivals[0].verified
    assert provider.calls['rival_scan'] == provider.calls['rival_profile'] == 1
