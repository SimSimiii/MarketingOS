"""The closed-world, deterministic boundary around relevance dossiers."""

import asyncio
from uuid import uuid4

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.knowledge.artifacts import BusinessProfile, KnowledgeArtifacts
from app.knowledge.ledger import Evidence, EvidenceKind, EvidenceLedger
from app.knowledge.store import ArtifactScope, ArtifactStore
from app.market.audience_research import AudienceProblem, AudienceResearch
from app.market.capabilities import CapabilityProfileDraft, ScopeBoundary
from app.market.claims import ClaimAxis
from app.market.positioning import AxisReading, PositioningMap, Territory
from app.market.radar import MarketSnapshot
from app.market.relevance import (
    DossierState,
    FitVerdict,
    ObjectionProposal,
    ProblemFitProposal,
    RankedRelevanceProposal,
    RelevanceAnalyst,
    RelevanceBand,
    RelevanceProposal,
    RelevanceValidationError,
    SilenceProposal,
    normalize_dossier,
)
from app.market.store import MarketStore
from app.models.brand import Brand
from app.services import market_service
from app.services.market_service import JobStatus, MarketService
from tests.market.conftest import ScriptedProvider


def ledger() -> EvidenceLedger:
    return EvidenceLedger(
        entries=[
            Evidence(
                id="E1",
                kind=EvidenceKind.METRIC,
                claim="Cuts warranty triage from 40 minutes to 9 seconds",
                verbatim="Warranty triage fell from 40 minutes to 9 seconds.",
                source="product case study",
            ),
            Evidence(
                id="E2",
                kind=EvidenceKind.INTEGRATION,
                claim="Connects to the shared inbox over an API",
                verbatim="Connect the shared inbox over our API.",
                source="product docs",
            ),
            Evidence(
                id="E3",
                kind=EvidenceKind.PRICE,
                claim="$29 per month",
                verbatim="Team is $29 per month.",
                source="pricing",
            ),
        ]
    )


def research() -> AudienceResearch:
    return AudienceResearch(
        audience_name="Repair shops answering warranty requests",
        candidate_kind="adjacent",
        problems=[
            AudienceProblem(
                id="P1",
                statement="Repeat warranty questions consume the first hour of the day.",
                cost="one hour every morning",
            ),
            AudienceProblem(
                id="P2",
                statement="Customers cannot see repair status without calling.",
            ),
        ],
    )


def positioning() -> PositioningMap:
    return PositioningMap(
        readings=[
            AxisReading(axis=ClaimAxis.SPEED, territory=Territory.OPEN),
            AxisReading(axis=ClaimAxis.BREADTH, territory=Territory.TABLE_STAKES),
            AxisReading(axis=ClaimAxis.PRICE, territory=Territory.CONTESTED),
        ],
        rivals_profiled=2,
    )


def normalize(
    proposal: RelevanceProposal,
    *,
    capability_ids: set[str] | None = None,
    constraint_ids: set[str] | None = None,
):
    return normalize_dossier(
        proposal,
        ledger=ledger(),
        research=research(),
        positioning=positioning(),
        knowledge_id=uuid4(),
        knowledge_version=3,
        research_id=uuid4(),
        research_version=2,
        market_scan_id=uuid4(),
        market_scan_version=4,
        capability_ids=capability_ids,
        constraint_ids=constraint_ids,
    )


def test_unknown_and_duplicate_rankings_are_normalized_without_touching_the_ledger():
    complete = ledger()
    proposal = RelevanceProposal(
        ranked_relevance=[
            RankedRelevanceProposal(
                evidence_id="unknown", band=RelevanceBand.LEAD, why="Sounds good"
            ),
            RankedRelevanceProposal(
                evidence_id="E1",
                band=RelevanceBand.WITHHOLD,
                why="The proof is real but this buyer sees the setup claim as a distraction",
                problem_ids=["P1", "made-up"],
            ),
            RankedRelevanceProposal(
                evidence_id="E1", band=RelevanceBand.LEAD, why="A conflicting second band"
            ),
        ]
    )

    dossier = normalize_dossier(
        proposal,
        ledger=complete,
        research=research(),
        positioning=positioning(),
        knowledge_id=uuid4(),
        knowledge_version=1,
        research_id=uuid4(),
        research_version=1,
        market_scan_id=uuid4(),
        market_scan_version=1,
    )

    assert [(item.evidence_id, item.band) for item in dossier.ranked_relevance] == [
        ("E1", RelevanceBand.WITHHOLD)
    ]
    assert dossier.ranked_relevance[0].problem_ids == ["P1"]
    assert dossier.ranked_relevance[0].territory is Territory.OPEN
    assert dossier.validation_counts.dropped_items == 2
    assert dossier.validation_counts.normalized_items >= 1
    assert complete.ids == {"E1", "E2", "E3"}, "WITHHOLD is not a licensing mutation"


def test_fit_verdicts_are_mechanical_not_persuasive():
    dossier = normalize(
        RelevanceProposal(
            problem_fits=[
                ProblemFitProposal(
                    problem_id="P1",
                    verdict=FitVerdict.SOLVED,
                    evidence_ids=["E2"],
                    why="This sounds completely solved",
                ),
                ProblemFitProposal(
                    problem_id="P2",
                    verdict=FitVerdict.PARTIAL,
                    evidence_ids=["E2"],
                    caveat="",
                ),
                ProblemFitProposal(
                    problem_id="P1",
                    verdict=FitVerdict.UNSUPPORTED,
                    evidence_ids=["E1"],
                ),
                ProblemFitProposal(
                    problem_id="P2",
                    verdict=FitVerdict.IMMATERIAL,
                    evidence_ids=["E2"],
                    materiality_basis="The model says it is minor",
                ),
                ProblemFitProposal(
                    problem_id="P2",
                    verdict=FitVerdict.ADDRESSED,
                    capability_ids=["C1"],
                ),
                ProblemFitProposal(
                    problem_id="P2",
                    verdict=FitVerdict.OFF_LIMITS,
                    blocked_by=["X1"],
                ),
            ],
            silences=[SilenceProposal(problem_id="P2", reason="No verified bridge exists")],
        )
    )

    # SOLVED, PARTIAL, IMMATERIAL, ADDRESSED and OFF_LIMITS all fail their
    # actual structural requirements. UNSUPPORTED survives with references cleared.
    assert [(fit.problem_id, fit.verdict) for fit in dossier.problem_fits] == [
        ("P1", FitVerdict.UNSUPPORTED)
    ]
    assert dossier.problem_fits[0].evidence_ids == []
    assert dossier.validation_counts.dropped_items == 5
    assert dossier.validation_counts.normalized_items == 2


def test_positive_fit_requirements_and_catalog_ids_are_enforced():
    dossier = normalize(
        RelevanceProposal(
            problem_fits=[
                ProblemFitProposal(
                    problem_id="P1",
                    verdict=FitVerdict.SOLVED,
                    evidence_ids=["E1"],
                ),
                ProblemFitProposal(
                    problem_id="P2",
                    verdict=FitVerdict.PARTIAL,
                    evidence_ids=["E2"],
                    caveat="It can expose status but the material proves no customer result",
                ),
                ProblemFitProposal(
                    problem_id="P1",
                    verdict=FitVerdict.IMMATERIAL,
                    evidence_ids=["E3"],
                    materiality_basis="The researched cost is only one hour every morning",
                ),
                ProblemFitProposal(
                    problem_id="P2",
                    verdict=FitVerdict.ADDRESSED,
                    capability_ids=["bad"],
                ),
                ProblemFitProposal(
                    problem_id="P2",
                    verdict=FitVerdict.OFF_LIMITS,
                    blocked_by=["bad"],
                ),
            ]
        ),
        capability_ids={"C1"},
        constraint_ids={"X1"},
    )

    # The first verdict per problem wins; invalid catalogue references never
    # become stable ids merely because a catalogue exists.
    assert [(fit.problem_id, fit.verdict) for fit in dossier.problem_fits] == [
        ("P1", FitVerdict.SOLVED),
        ("P2", FitVerdict.PARTIAL),
    ]
    assert dossier.validation_counts.dropped_items == 3


def test_invalid_capability_and_constraint_ids_are_rejected_when_catalogues_exist():
    dossier = normalize(
        RelevanceProposal(
            problem_fits=[
                ProblemFitProposal(
                    problem_id="P1",
                    verdict=FitVerdict.ADDRESSED,
                    capability_ids=["made-up-capability"],
                ),
                ProblemFitProposal(
                    problem_id="P2",
                    verdict=FitVerdict.OFF_LIMITS,
                    blocked_by=["made-up-constraint"],
                ),
            ],
            silences=[SilenceProposal(problem_id="P2", reason="No supported fit remains")],
        ),
        capability_ids={"C1"},
        constraint_ids={"X1"},
    )

    assert dossier.problem_fits == []
    assert dossier.validation_counts.dropped_items == 2


def test_immaterial_requires_and_keeps_researched_materiality_basis():
    dossier = normalize(
        RelevanceProposal(
            problem_fits=[
                ProblemFitProposal(
                    problem_id="P1",
                    verdict=FitVerdict.IMMATERIAL,
                    evidence_ids=["E3"],
                    materiality_basis="The sourced cost is limited to one hour every morning",
                )
            ]
        )
    )

    assert dossier.problem_fits[0].verdict is FitVerdict.IMMATERIAL
    assert dossier.problem_fits[0].evidence_ids == ["E3"]
    assert dossier.problem_fits[0].materiality_basis


def test_objections_and_silences_resolve_every_reference():
    dossier = normalize(
        RelevanceProposal(
            segment_objections=[
                ObjectionProposal(
                    objection="We cannot change the shared inbox this quarter",
                    answer="The API means nothing has to change",
                    evidence_ids=["unknown"],
                ),
                ObjectionProposal(
                    objection="The API will be hard to integrate",
                    answer="It connects directly to the shared inbox",
                    evidence_ids=["E2", "unknown"],
                ),
            ],
            silences=[
                SilenceProposal(problem_id="unknown", reason="Made up"),
                SilenceProposal(
                    problem_id="P2",
                    reason="The ledger proves integration but no customer-facing status view",
                    question="Can you provide proof that customers can see repair status",
                ),
            ],
        )
    )

    assert dossier.segment_objections[0].answer == ""
    assert dossier.segment_objections[0].evidence_ids == []
    assert dossier.segment_objections[1].evidence_ids == ["E2"]
    assert [silence.problem_id for silence in dossier.silences] == ["P2"]
    assert {item.id for item in dossier.evidence} == {"E2"}


def test_a_completely_unusable_proposal_is_not_persistable():
    with pytest.raises(RelevanceValidationError, match="No dossier was saved"):
        normalize(
            RelevanceProposal(
                ranked_relevance=[
                    RankedRelevanceProposal(
                        evidence_id="unknown",
                        band=RelevanceBand.LEAD,
                        why="Invented",
                    )
                ]
            )
        )


@pytest.mark.asyncio
async def test_one_deep_closed_world_call_gets_only_the_three_persisted_inputs(
    provider: ScriptedProvider, session
):
    provider.push(
        "relevance_dossier",
        {
            "orientation": "A shared-inbox triage tool for repair shops.",
            "ranked_relevance": [
                {
                    "evidence_id": "E1",
                    "band": "LEAD",
                    "why": "It addresses the researched daily time cost with measured proof.",
                    "problem_ids": ["P1"],
                }
            ],
        },
    )
    artifacts = KnowledgeArtifacts(
        business=BusinessProfile(
            company_name="Helpdesk", what_it_does="triages shared inbox requests"
        ),
        evidence=ledger(),
    )
    knowledge_id, research_id, scan_id = uuid4(), uuid4(), uuid4()

    dossier = await RelevanceAnalyst(session).analyse(
        artifacts=artifacts,
        knowledge_id=knowledge_id,
        knowledge_version=3,
        research=research(),
        research_id=research_id,
        research_version=2,
        positioning=positioning(),
        market_scan_id=scan_id,
        market_scan_version=4,
    )

    assert provider.calls["relevance_dossier"] == 1
    request = provider.requests[0]
    assert request.role == "relevance_analyst"
    assert request.tools == []
    assert request.model == "opus", "the relevance role is deep-tier"
    prompt = (request.system_prompt or "") + request.messages[0].content
    assert str(knowledge_id) in prompt and str(research_id) in prompt and str(scan_id) in prompt
    assert "complete_evidence_ledger" in prompt
    assert "positioning_map" in prompt
    for forbidden in (
        "SECRET CAMPAIGN REQUEST",
        "SECRET CAMPAIGN BRIEF",
        "SECRET EMAIL DRAFT",
        "SECRET BLIND READER",
    ):
        assert forbidden not in prompt
    assert dossier.ranked_relevance[0].evidence_id == "E1"


def database():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        brand = Brand(name="Helpdesk")
        session.add(brand)
        session.commit()
        session.refresh(brand)
        artifacts = KnowledgeArtifacts(
            business=BusinessProfile(
                company_name="Helpdesk", what_it_does="triages shared inbox requests"
            ),
            evidence=ledger(),
        )
        ArtifactStore(session).save(
            ArtifactScope(brand_id=brand.id), artifacts, "knowledge-fingerprint"
        )
        store = MarketStore(session)
        store.save_research(brand.id, research(), None)
        store.save_scan(
            brand.id, MarketSnapshot(positioning=positioning())
        )
        return engine, brand.id


def save_current_dossier(engine, brand_id):
    with Session(engine) as session:
        service = MarketService(session)
        inputs = service._relevance_inputs(brand_id, research().audience_name)
        dossier = normalize_dossier(
            RelevanceProposal(
                ranked_relevance=[
                    RankedRelevanceProposal(
                        evidence_id="E1",
                        band=RelevanceBand.LEAD,
                        why="Measured proof addresses the audience's daily time cost",
                        problem_ids=["P1"],
                    )
                ]
            ),
            ledger=inputs.artifacts.evidence,
            research=inputs.research,
            positioning=inputs.snapshot.positioning,
            knowledge_id=inputs.knowledge_row.id,
            knowledge_version=inputs.knowledge_row.version,
            research_id=inputs.research_row.id,
            research_version=inputs.research_row.version,
            market_scan_id=inputs.market_scan_row.id,
            market_scan_version=inputs.market_scan_row.version,
        )
        return service.store.save_dossier(brand_id, dossier)


def save_current_v2_dossier(engine, brand_id):
    with Session(engine) as session:
        service = MarketService(session)
        inputs = service._relevance_inputs(brand_id, research().audience_name)
        dossier = normalize_dossier(
            RelevanceProposal(
                ranked_relevance=[
                    RankedRelevanceProposal(
                        evidence_id="E1",
                        band=RelevanceBand.LEAD,
                        why="Measured proof addresses the audience's daily time cost",
                        problem_ids=["P1"],
                    )
                ],
                problem_fits=[
                    ProblemFitProposal(
                        problem_id="P1",
                        verdict=FitVerdict.SOLVED,
                        evidence_ids=["E1"],
                    )
                ],
            ),
            ledger=inputs.artifacts.evidence,
            research=inputs.research,
            positioning=inputs.snapshot.positioning,
            knowledge_id=inputs.knowledge_row.id,
            knowledge_version=inputs.knowledge_row.version,
            research_id=inputs.research_row.id,
            research_version=inputs.research_row.version,
            market_scan_id=inputs.market_scan_row.id,
            market_scan_version=inputs.market_scan_row.version,
            capability_profile=inputs.capability_profile,
            capability_profile_id=inputs.capability_profile_row.id,
            capability_profile_version=inputs.capability_profile_row.version,
            company_qualifications=inputs.company_qualifications,
            qualification_fingerprint=inputs.qualification_fingerprint,
        )
        return service.store.save_dossier(brand_id, dossier)


def test_dossier_rows_keep_the_exact_triple_and_rebuild_history():
    engine, brand_id = database()
    first = save_current_dossier(engine, brand_id)
    second = save_current_dossier(engine, brand_id)

    with Session(engine) as session:
        store = MarketStore(session)
        history = store.dossier_history(brand_id, research().audience_name)
        exact = store.dossier_for_triple(
            brand_id,
            research().audience_name,
            knowledge_id=second.knowledge_id,
            knowledge_version=second.knowledge_version,
            research_id=second.audience_research_id,
            research_version=second.audience_research_version,
            market_scan_id=second.market_scan_id,
            market_scan_version=second.market_scan_version,
        )

    assert second.generation_version == first.generation_version + 1
    assert [row.id for row in history] == [second.id, first.id]
    assert exact is not None and exact.id == second.id
    assert all(
        (
            row.knowledge_id,
            row.audience_research_id,
            row.market_scan_id,
        )
        == (
            first.knowledge_id,
            first.audience_research_id,
            first.market_scan_id,
        )
        for row in history
    )


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ("knowledge", "knowledge_changed"),
        ("audience", "audience_research_changed"),
        ("market", "market_scan_changed"),
    ],
)
def test_version_pointer_changes_mark_but_do_not_delete_a_dossier(change, reason):
    engine, brand_id = database()
    saved = save_current_dossier(engine, brand_id)

    with Session(engine) as session:
        if change == "knowledge":
            ArtifactStore(session).save(
                ArtifactScope(brand_id=brand_id),
                KnowledgeArtifacts(
                    business=BusinessProfile(what_it_does="triages requests"),
                    evidence=ledger(),
                ),
                "changed-fingerprint",
            )
        elif change == "audience":
            MarketStore(session).save_research(brand_id, research(), None)
        else:
            MarketStore(session).save_scan(
                brand_id, MarketSnapshot(positioning=positioning())
            )
        status = MarketService(session).relevance_status(
            brand_id, research().audience_name
        )
        old = session.get(type(saved), saved.id)

    assert status.status is DossierState.STALE
    assert status.stale_reasons == [reason]
    assert status.dossier_id == saved.id
    assert status.dossier is not None
    assert old is not None, "staleness never deletes the old dossier"


def test_an_exact_current_triple_is_reused_before_a_model_call():
    engine, brand_id = database()
    saved = save_current_dossier(engine, brand_id)
    provider = ScriptedProvider()

    with Session(engine) as session:
        brand = session.get(Brand, brand_id)
        assert brand is not None
        status = MarketService(session).launch_relevance_dossier(
            brand,
            provider,
            engine,
            segment=research().audience_name,
        )

    assert status.state == "done"
    assert status.calls == 0
    assert f"v{saved.generation_version}" in status.summary
    assert provider.requests == []


def test_an_exact_v2_input_set_is_reused_before_a_model_call():
    engine, brand_id = database()
    saved = save_current_v2_dossier(engine, brand_id)
    provider = ScriptedProvider()

    with Session(engine) as session:
        brand = session.get(Brand, brand_id)
        assert brand is not None
        status = MarketService(session).launch_relevance_dossier(
            brand,
            provider,
            engine,
            segment=research().audience_name,
        )

    assert saved.schema_version == 2
    assert status.state == "done"
    assert status.calls == 0
    assert provider.requests == []


@pytest.mark.asyncio
async def test_editing_the_capability_profile_invalidates_v2_reuse_identity():
    engine, brand_id = database()
    first = save_current_v2_dossier(engine, brand_id)
    provider = ScriptedProvider().push(
        "relevance_dossier",
        {
            "ranked_relevance": [
                {
                    "evidence_id": "E1",
                    "band": "LEAD",
                    "why": "Measured proof addresses the audience's daily time cost",
                    "problem_ids": ["P1"],
                }
            ]
        },
    )

    with Session(engine) as session:
        service = MarketService(session)
        current = service.capability_profile(brand_id)
        assert current is not None
        _, profile = current
        service.save_capability_profile(
            brand_id,
            CapabilityProfileDraft(
                capabilities=profile.capabilities,
                constraints=[
                    *profile.constraints,
                    ScopeBoundary(
                        id="manual_boundary",
                        statement="Do not describe a text agent as a full operating system.",
                    ),
                ],
                claims=profile.claims,
            ),
        )
        brand = session.get(Brand, brand_id)
        assert brand is not None
        status = service.launch_relevance_dossier(
            brand,
            provider,
            engine,
            segment=research().audience_name,
        )

    while status.state == "running":
        await asyncio.sleep(0)

    assert status.state == "done"
    assert status.calls == 1
    assert provider.calls["relevance_dossier"] == 1
    with Session(engine) as session:
        history = MarketStore(session).dossier_history(
            brand_id, research().audience_name
        )
    assert history[0].capability_profile_id != first.capability_profile_id


@pytest.mark.asyncio
async def test_background_generation_persists_only_after_one_valid_call():
    engine, brand_id = database()
    provider = ScriptedProvider().push(
        "relevance_dossier",
        {
            "ranked_relevance": [
                {
                    "evidence_id": "E1",
                    "band": "LEAD",
                    "why": "Measured proof addresses the researched daily time cost",
                    "problem_ids": ["P1"],
                }
            ]
        },
    )
    status = JobStatus(kind="relevance_dossier", brand_id=brand_id)

    await market_service._run_relevance_dossier(
        brand_id,
        provider,
        engine,
        status,
        segment=research().audience_name,
    )

    with Session(engine) as session:
        stored = MarketStore(session).latest_dossier(
            brand_id, research().audience_name
        )
    assert status.state == "done"
    assert status.calls == 1
    assert provider.calls["relevance_dossier"] == 1
    assert stored is not None


@pytest.mark.asyncio
async def test_failed_model_generation_persists_no_successful_row():
    engine, brand_id = database()
    provider = ScriptedProvider()
    status = JobStatus(kind="relevance_dossier", brand_id=brand_id)

    await market_service._run_relevance_dossier(
        brand_id,
        provider,
        engine,
        status,
        segment=research().audience_name,
    )

    with Session(engine) as session:
        stored = MarketStore(session).latest_dossier_row(
            brand_id, research().audience_name
        )
    assert status.state == "failed"
    assert stored is None
