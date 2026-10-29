"""Persisted audience intelligence reaches strategy, and nowhere else."""

import json
from uuid import uuid4

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.knowledge.artifacts import (
    AudienceModel,
    CallToAction,
    Fact,
    Grounding,
    KnowledgeArtifacts,
    Objection,
    OfferSheet,
    Plan,
    Provenance,
    Segment,
    Sophistication,
)
from app.knowledge.corpus import SourceCorpus
from app.knowledge.ledger import Evidence, EvidenceKind, EvidenceLedger, EvidenceStrength
from app.knowledge.store import ArtifactScope, ArtifactStore, fingerprint_documents
from app.market.audience_research import (
    AudienceProblem,
    AudienceResearch,
    BuyerPhrase,
    BuyerPhraseKind,
    EvidenceReference,
    SourcedObservation,
)
from app.market.demand import AudienceSegment, DemandMap
from app.market.radar import MarketSnapshot
from app.market.relevance import (
    INTERPRETATION_VERSION,
    CampaignReadiness,
    CampaignRecommendation,
    ClaimContract,
    DossierSilence,
    DossierState,
    FitVerdict,
    ProblemFit,
    RankedRelevanceItem,
    RecommendationState,
    RelevanceBand,
    RelevanceDossier,
    RelevanceStatus,
)
from app.market.store import MarketStore
from app.marketing.briefs import ArgumentOption
from app.marketing.contract import parse_contract
from app.marketing.intelligence import (
    AudienceResolution,
    CampaignIntelligence,
    CampaignIntelligenceBundle,
    DossierPosture,
    adapt_researched_audience,
    build_campaign_intelligence,
    resolve_audience_research,
)
from app.marketing.pipeline import EmailCampaignPipeline
from app.marketing.policy import PRESETS
from app.marketing.reader import personas_for
from app.marketing.request import CampaignRequest
from app.marketing.strategist import MAX_EVIDENCE_PER_EMAIL, Strategist
from app.marketing.writer import EmailWriter
from app.models.brand import Brand
from app.models.campaign import Campaign
from app.models.execution_log import ExecutionLog
from app.models.market import AudienceResearchRow
from app.orchestration.campaign_orchestrator import (
    CampaignOrchestrator,
    _DbKnowledgeGateway,
)
from app.repositories.knowledge_artifact_repository import KnowledgeArtifactRepository
from tests.marketing.conftest import (
    FakeKnowledgeGateway,
    RoleScriptedProvider,
    artifacts_fixture,
    campaign_brief,
    default_answers,
    make_session,
)

SOURCE_BODY_SENTINEL = "FULL FETCHED SOURCE PAGE BODY MUST NEVER REACH STRATEGY"


def ledger() -> EvidenceLedger:
    return EvidenceLedger(
        entries=[
            Evidence(
                id=f"E{index}",
                kind=EvidenceKind.METRIC if index == 1 else EvidenceKind.FEATURE,
                claim=f"licensed product fact {index}",
                verbatim=f"Licensed product fact {index}.",
            )
            for index in range(1, 7)
        ]
    )


def research(name: str = "Repair shops answering warranty requests") -> AudienceResearch:
    quoted = EvidenceReference(source_id="S1", quote="the first hour disappears into repeats")
    return AudienceResearch(
        audience_name=name,
        candidate_kind="adjacent",
        situation=SourcedObservation(
            text="A repair-shop owner opens the shared inbox before starting repairs.",
            grounding=Grounding.GROUNDED,
            evidence=[quoted],
            inference_basis=SOURCE_BODY_SENTINEL,
        ),
        incumbent_behaviour=[
            SourcedObservation(
                text="They answer repeat warranty questions by hand from the shared inbox.",
                grounding=Grounding.GROUNDED,
                evidence=[quoted],
            )
        ],
        sophistication=Sophistication.SOLUTION_AWARE,
        problems=[
            AudienceProblem(
                id="P1",
                statement="Repeat warranty questions consume the first hour of the day.",
                grounding=Grounding.GROUNDED,
                evidence=[quoted],
                corroboration=3,
                cost="the first hour of the day",
            ),
            AudienceProblem(
                id="P2",
                statement="Customers cannot see repair status without calling.",
                grounding=Grounding.GROUNDED,
                evidence=[quoted],
                corroboration=2,
            ),
        ],
        buyer_phrases=[
            BuyerPhrase(
                text="the first hour disappears into repeats",
                kind=BuyerPhraseKind.COMPLAINT,
                evidence=quoted,
            )
        ],
        triggers=[
            SourcedObservation(
                text="A seasonal warranty spike doubles the shared inbox.",
                grounding=Grounding.GROUNDED,
                evidence=[quoted],
            )
        ],
        desired_outcomes=[
            SourcedObservation(
                text="Start repair work without first clearing repeat questions.",
                grounding=Grounding.GROUNDED,
                evidence=[quoted],
            )
        ],
        signals=[
            SourcedObservation(
                text="Publishes a warranty intake form.", grounding=Grounding.GROUNDED
            )
        ],
        where=[
            SourcedObservation(
                text="Independent repair association member directory.",
                grounding=Grounding.GROUNDED,
            )
        ],
    )


def research_row(
    name: str = "Repair shops answering warranty requests",
    *,
    brand_id=None,
    version: int = 2,
) -> AudienceResearchRow:
    return AudienceResearchRow(
        brand_id=brand_id or uuid4(),
        audience_key=" ".join(name.casefold().split()),
        audience_name=name,
        version=version,
        payload=research(name).model_dump(mode="json"),
    )


def dossier_status(
    row: AudienceResearchRow,
    *,
    state: DossierState = DossierState.CURRENT,
    stale_reasons: list[str] | None = None,
) -> RelevanceStatus:
    dossier_id = uuid4()
    dossier = RelevanceDossier(
        interpretation_version=INTERPRETATION_VERSION,
        audience_research_id=row.id,
        audience_name=row.audience_name,
        audience_research_version=row.version,
        knowledge_id=uuid4(),
        knowledge_version=4,
        market_scan_id=uuid4(),
        market_scan_version=3,
        orientation="A shared-inbox triage tool for repair shops.",
        ranked_relevance=[
            RankedRelevanceItem(
                evidence_id="E1", band=RelevanceBand.LEAD, why="Measured time proof", problem_ids=["P1"]
            ),
            RankedRelevanceItem(
                evidence_id="E2", band=RelevanceBand.SUPPORT, why="Explains the mechanism"
            ),
            RankedRelevanceItem(
                evidence_id="E3", band=RelevanceBand.CONTEXT, why="Category context"
            ),
            RankedRelevanceItem(
                evidence_id="E4", band=RelevanceBand.WITHHOLD, why="Distracts this audience"
            ),
        ],
        problem_fits=[
            ProblemFit(
                problem_id="P1",
                verdict=FitVerdict.PARTIAL,
                evidence_ids=["E1"],
                caveat="It reduces repeat triage; it does not eliminate every warranty question.",
            ),
            ProblemFit(problem_id="P2", verdict=FitVerdict.UNSUPPORTED),
        ],
        segment_objections=[
            Objection(
                objection="Changing the shared inbox will disrupt repair work.",
                answer="The existing inbox remains in place.",
                evidence_ids=["E2"],
            )
        ],
        silences=[
            DossierSilence(
                problem_id="P2", reason="No ledger fact proves a customer status view."
            )
        ],
        validation_warnings=["One low-value ranking was normalized."],
    )
    return RelevanceStatus(
        audience_name=row.audience_name,
        status=state,
        stale_reasons=stale_reasons or [],
        dossier_id=dossier_id,
        generation_version=5,
        dossier=dossier,
    )


def context(
    *, state: DossierState = DossierState.CURRENT
) -> tuple[CampaignIntelligence, AudienceResearchRow]:
    row = research_row()
    match = resolve_audience_research(row.audience_name, [row])
    status = dossier_status(
        row,
        state=state,
        stale_reasons=["market_scan_changed"] if state is DossierState.STALE else [],
    )
    return (
        build_campaign_intelligence(
            selected_audience=row.audience_name,
            match=match,
            dossier_status=status,
            ledger=ledger(),
        ),
        row,
    )


def test_strong_official_recovery_extends_the_stale_dossier_boundary():
    intelligence, _ = context(state=DossierState.STALE)
    intelligence.trace.dossier_schema_version = 2
    intelligence.recommendation_state = RecommendationState.RECOMMENDED_NARROW
    intelligence.claim_contract = ClaimContract()
    current = ledger()
    current.entries.append(
        Evidence(
            id="R1",
            kind=EvidenceKind.INTEGRATION,
            claim="The documented SMTP route uses port 587.",
            verbatim="Configure the SMTP route using port 587.",
            source="https://docs.example.test/smtp",
            strength=EvidenceStrength.STRONG,
        )
    )

    intelligence.admit_automatically_recovered(current)
    intelligence.validate_against(current)

    assert "R1" in intelligence.allowed_evidence_ids
    assert "The documented SMTP route uses port 587." in intelligence.allowed_claims
    assert intelligence.claim_contract is not None
    assert "R1" in intelligence.claim_contract.allowed_evidence_ids


def test_knowledge_change_discards_old_claim_ids_before_strategy():
    row = research_row()
    status = dossier_status(
        row, state=DossierState.STALE, stale_reasons=["knowledge_changed"],
    )
    status.dossier.schema_version = 2
    status.dossier.recommendation = CampaignRecommendation(
        state=RecommendationState.RECOMMENDED_NARROW,
        readiness=CampaignReadiness.GO_NARROW,
        allowed_claims=["An old claim now mapped to another ledger entry."],
        allowed_evidence_ids=["E1"],
    )

    intelligence = build_campaign_intelligence(
        selected_audience=row.audience_name,
        match=resolve_audience_research(row.audience_name, [row]),
        dossier_status=status,
        ledger=ledger(),
    )

    assert intelligence.trace.dossier_status is DossierPosture.STALE
    assert "knowledge_changed" in intelligence.render_for_strategy()
    assert not intelligence.v2_claim_boundary
    assert intelligence.allowed_evidence_ids == []
    assert intelligence.allowed_claims == []
    assert intelligence.ranked_evidence == []
    assert intelligence.problem_fits == []


@pytest.mark.asyncio
async def test_strategy_can_use_new_ledger_id_after_knowledge_change():
    row = research_row()
    status = dossier_status(
        row, state=DossierState.STALE, stale_reasons=["knowledge_changed"],
    )
    status.dossier.schema_version = 2
    status.dossier.recommendation = CampaignRecommendation(
        state=RecommendationState.RECOMMENDED_NARROW,
        readiness=CampaignReadiness.GO_NARROW,
        allowed_evidence_ids=["E1"],
    )
    intelligence = build_campaign_intelligence(
        selected_audience=row.audience_name,
        match=resolve_audience_research(row.audience_name, [row]),
        dossier_status=status,
        ledger=ledger(),
    )
    provider = RoleScriptedProvider({"strategist": strategist_answer(evidence=["E2"])})

    brief = await Strategist(make_session(provider)).build(
        request=request(),
        artifacts=adapt_researched_audience(artifacts(), research(), intelligence),
        corpus=SourceCorpus(),
        contract=parse_contract(request().request),
        intelligence=intelligence,
    )

    assert brief.emails[0].evidence_ids == ["E2"]
    assert provider.calls_by_role == {"strategist": 2}, "One bounded proposition repair preserves the new ledger fact; a stale dossier must not license its old problem bridge."


def artifacts() -> KnowledgeArtifacts:
    found = artifacts_fixture()
    found.evidence = ledger()
    found.audience = AudienceModel(
        segments=[
            Segment(
                name="Repair shops answering warranty requests",
                situation="A discovery hypothesis about repair shops.",
                job_to_be_done="Legacy product relevance",
            ),
            Segment(name="Software teams writing release notes", situation="Ships weekly."),
        ],
        objections=[Objection(objection="A legacy objection")],
    )
    return found


def request() -> CampaignRequest:
    return CampaignRequest(
        name="Launch",
        request="Write me 1 email for repair shops",
        product_description="Shared-inbox triage",
    )


def strategist_answer(*, orientation: str = "Model-authored orientation", evidence=None) -> str:
    return campaign_brief(
        1,
        reader="a repair-shop owner at the shared inbox",
        reader_segment="Repair shops answering warranty requests",
        orientation=orientation,
        emails=[
            {
                "position": 1,
                "job": "Make the morning cost concrete",
                "single_idea": "Repeat triage steals repair time",
                "felt_need": "A product-derived problem that research did not verify",
                "status_quo": "They probably use a spreadsheet",
                "evidence_ids": evidence or ["E1"],
                "must_not_say": [],
                "objection": "Changing the shared inbox will disrupt repair work.",
                "call_to_action": "Start the trial",
            }
        ],
    )


class IntelligenceGateway(FakeKnowledgeGateway):
    def __init__(self, bundle: CampaignIntelligenceBundle | None):
        super().__init__(compiled=artifacts(), audience_choice="Repair shops answering warranty requests")
        self._bundle = bundle

    def campaign_intelligence(self, current: KnowledgeArtifacts):
        return self._bundle


def test_resolution_prefers_exact_then_allows_only_one_specific_forgiving_match():
    exact = research_row("Repair shops answering warranty requests")
    other = research_row("Dental practices handling insurance requests")

    matched = resolve_audience_research("  REPAIR SHOPS answering warranty requests ", [exact, other])
    forgiving = resolve_audience_research("Repair shops answering warranty requests in Leeds", [exact, other])

    assert matched.status is AudienceResolution.LOADED and matched.row is exact
    assert forgiving.status is AudienceResolution.LOADED and forgiving.row is exact


def test_forgiving_resolution_refuses_ambiguity_and_generic_category_words():
    first = research_row("Repair shops answering warranty requests")
    second = research_row("Shops answering warranty requests in Leeds")
    generic = research_row("Developer teams shipping mobile apps")

    ambiguous = resolve_audience_research("Repair shops answering warranty requests in Leeds", [first, second])
    category_only = resolve_audience_research("Developers", [generic])

    assert ambiguous.status is AudienceResolution.AMBIGUOUS
    assert category_only.status is AudienceResolution.MISSING


def test_researched_segment_replaces_only_the_selected_primary_and_drives_personas():
    intelligence, _ = context()
    adapted = adapt_researched_audience(artifacts(), research(), intelligence)
    selected = adapted.audience.primary()

    assert selected is not None
    assert selected.situation == "A repair-shop owner opens the shared inbox before starting repairs."
    assert selected.job_to_be_done == "Start repair work without first clearing repeat questions."
    assert selected.trigger == "A seasonal warranty spike doubles the shared inbox."
    assert selected.sophistication is Sophistication.SOLUTION_AWARE
    assert [pain.statement for pain in selected.pains] == [
        "Repeat warranty questions consume the first hour of the day.",
        "Customers cannot see repair status without calling.",
    ]
    assert adapted.audience.segments[1].name == "Software teams writing release notes"
    assert adapted.audience.objections[0].evidence_ids == ["E2"]
    assert adapted.audience.objections[-1].objection == "A legacy objection"
    assert "opens the shared inbox before starting repairs" in personas_for(
        adapted.audience, selected, panel=False
    )[0]


def test_selected_audience_survives_research_without_promoting_a_discovery_method():
    row = research_row()
    need = "Collect recorded repair results for the public portfolio."
    intelligence = build_campaign_intelligence(
        selected_audience=row.audience_name,
        selected_need=need,
        match=resolve_audience_research(row.audience_name, [row]),
        dossier_status=dossier_status(row),
        ledger=ledger(),
    )
    original = artifacts()
    adapted = adapt_researched_audience(original, research(), intelligence)
    selected = adapted.audience.primary()

    assert selected.name == intelligence.selected_audience
    assert selected.job_to_be_done == research().desired_outcomes[0].text
    assert selected.situation == research().situation.text
    assert selected.situation_grounding is Grounding.GROUNDED
    assert selected.situation_provenance
    assert intelligence.desired_outcomes[0].text != need
    assert original.audience.primary().job_to_be_done == "Legacy product relevance"
    rendered = intelligence.render_for_strategy()
    assert need in rendered
    assert "not an additional campaign requirement" in rendered
    assert intelligence.desired_outcomes[0].text in rendered


@pytest.mark.parametrize("ambiguous", [False, True])
def test_selected_job_without_resolved_research_carries_no_borrowed_observations(ambiguous):
    name = "Repair shops answering warranty requests in Leeds"
    rows = [research_row(), research_row("Shops answering warranty requests in Leeds")] if ambiguous else []
    intelligence = build_campaign_intelligence(
        selected_audience=name,
        selected_need="Collect recorded repair results.",
        match=resolve_audience_research(name, rows),
        dossier_status=None,
        ledger=ledger(),
    )

    assert intelligence.selected_need == "Collect recorded repair results."
    assert intelligence.trace.audience_resolution_status is (
        AudienceResolution.AMBIGUOUS if ambiguous else AudienceResolution.MISSING
    )
    assert intelligence.situation is None
    assert intelligence.problems == intelligence.desired_outcomes == []
    assert intelligence.selected_need in intelligence.render_for_strategy()


@pytest.mark.asyncio
async def test_discovery_hypothesis_reaches_strategy_without_becoming_writer_biography():
    intelligence, _ = context()
    intelligence.selected_need = "Collect recorded repair results for the public portfolio."
    adapted = adapt_researched_audience(artifacts(), research(), intelligence)
    provider = RoleScriptedProvider({"strategist": strategist_answer()})

    await Strategist(make_session(provider)).build(
        request=request(), artifacts=adapted, corpus=SourceCorpus(),
        contract=parse_contract(request().request), intelligence=intelligence,
    )

    strategy = next(item for item in provider.requests if item.template == "strategist")
    assert intelligence.selected_need in strategy.system_prompt
    assert intelligence.selected_audience in adapted.audience.primary().render_for_writing()
    assert intelligence.selected_need not in adapted.audience.primary().render_for_writing()
    assert provider.calls_by_role == {"strategist": 1}


@pytest.mark.asyncio
async def test_target_assignment_is_pinned_in_the_brief_and_survives_argument_switch():
    intelligence, _ = context()
    intelligence.selected_need = "Collect recorded repair results for the public portfolio."
    answer = json.loads(strategist_answer())
    answer["emails"][0]["target_audience"] = "An invented replacement job"
    provider = RoleScriptedProvider({"strategist": json.dumps(answer)})

    brief = await Strategist(make_session(provider)).build(
        request=request(), artifacts=artifacts(), corpus=SourceCorpus(),
        contract=parse_contract(request().request), intelligence=intelligence,
    )
    selected = brief.emails[0]
    alternative = selected.with_argument(ArgumentOption(single_idea="Another supported route"))

    assert selected.target_audience == alternative.target_audience == intelligence.selected_audience
    for item in (selected, alternative):
        rendered = item.render()
        assert rendered.index(intelligence.selected_audience) < rendered.index("The one idea it owns")
        assert intelligence.selected_need not in rendered
        assert "An invented replacement job" not in rendered
        assert "campaign target, not observed biography" in rendered


@pytest.mark.asyncio
@pytest.mark.parametrize("allowed", [True, False])
async def test_closed_boundary_covers_strategy_and_writer_summaries_not_only_explicit_bans(allowed):
    current = artifacts()
    current.business.what_it_does = "SUMMARY_PRODUCT_SENTINEL"
    current.business.business_model = "SUMMARY_MODEL_SENTINEL"
    current.business.facts = [Fact(statement="SUMMARY_BUSINESS_SENTINEL")]
    current.audience.objections[0].answer = "SUMMARY_OBJECTION_ANSWER_SENTINEL"
    current.offer = OfferSheet(
        plans=[Plan(name="Starter", price="SUMMARY_PRICE_SENTINEL", includes=["SUMMARY_PLAN_SENTINEL"])],
        free_entry="SUMMARY_FREE_ENTRY_SENTINEL",
        guarantees=["SUMMARY_GUARANTEE_SENTINEL"],
        purchase_motion="SUMMARY_MOTION_SENTINEL",
        calls_to_action=[CallToAction(label="Start trial", url="https://product.example/signup")],
    )
    current.evidence.entries.append(Evidence(
        id="E7", kind=EvidenceKind.FEATURE,
        claim="UNRANKED_LEDGER_SENTINEL", verbatim="UNRANKED_LEDGER_SENTINEL",
    ))
    row = research_row()
    status = dossier_status(row)
    status.dossier.schema_version = 2
    status.dossier.recommendation = CampaignRecommendation(
        state=RecommendationState.RECOMMENDED_NARROW,
        readiness=CampaignReadiness.GO_NARROW,
        allowed_claims=["licensed product fact 1"] if allowed else [],
        allowed_evidence_ids=["E1"] if allowed else [],
        forbidden_evidence_ids=["E4"],
    )
    intelligence = build_campaign_intelligence(
        selected_audience=row.audience_name,
        match=resolve_audience_research(row.audience_name, [row]),
        dossier_status=status, ledger=current.evidence,
    )
    before = current.model_dump()
    provider = RoleScriptedProvider(default_answers())
    provider.set_default("strategist", strategist_answer(evidence=["E1"] if allowed else []))
    brief = await Strategist(make_session(provider)).build(
        request=request(), artifacts=current, corpus=SourceCorpus(),
        contract=parse_contract(request().request), intelligence=intelligence,
    )
    await EmailWriter(make_session(provider)).draft(
        brief=brief.emails[0], campaign=brief, request=request(), artifacts=current, previous=[],
    )

    for role in ("strategist", "email_writer"):
        prompt = provider.requests_for(role)[0].system_prompt
        assert "SUMMARY_" not in prompt
        assert "UNRANKED_LEDGER_SENTINEL" not in prompt
        assert "https://product.example/signup" in prompt
        assert "Starter" in prompt
        if allowed:
            assert "licensed product fact 1" in prompt
    assert current.model_dump() == before


def test_compact_context_carries_buyer_reality_and_dossier_but_no_source_body():
    intelligence, _ = context()
    rendered = intelligence.render_for_strategy()

    for expected in (
        "Repeat warranty questions consume",
        "answer repeat warranty questions by hand",
        "the first hour disappears into repeats",
        "seasonal warranty spike",
        "LEAD",
        "SUPPORT",
        "CONTEXT",
        "WITHHOLD",
        "No ledger fact proves a customer status view",
        "Complete Evidence Ledger: final authority",
    ):
        assert expected in rendered
    assert SOURCE_BODY_SENTINEL not in rendered


@pytest.mark.asyncio
async def test_current_dossier_and_research_change_the_normalized_brief_without_an_extra_call():
    intelligence, _ = context()
    adapted = adapt_researched_audience(artifacts(), research(), intelligence)
    provider = RoleScriptedProvider({"strategist": strategist_answer()})

    brief = await Strategist(make_session(provider)).build(
        request=request(),
        artifacts=adapted,
        corpus=SourceCorpus(),
        contract=parse_contract(request().request),
        intelligence=intelligence,
    )

    assert provider.calls_by_role == {"strategist": 1}
    assert brief.orientation == "A shared-inbox triage tool for repair shops."
    assert brief.emails[0].felt_need == (
        "Repeat warranty questions consume the first hour of the day."
    )
    assert brief.emails[0].status_quo == "", "An invented spreadsheet must not become another observed workflow by list order"
    assert any("single researched problem" in warning for warning in intelligence.trace.validation_warnings)
    assert brief.emails[0].evidence_ids == ["E1"]
    assert brief.emails[0].must_not_say == [
        "It reduces repeat triage; it does not eliminate every warranty question."
    ]
    assert intelligence.trace.partial_caveats_injected == brief.emails[0].must_not_say


def test_synthetic_research_problem_cannot_borrow_an_unrelated_capability():
    intelligence, _ = context()
    # Two real problems, only E1 is connected to P1. E2 is integration
    # documentation and does not establish a customer-facing status view.
    problem = intelligence.problems[1].statement
    assert intelligence.normalized_felt_need(problem, ["E2"]) == ""
    assert any("no dossier link" in warning for warning in intelligence.trace.validation_warnings)
    assert intelligence.normalized_felt_need("", ["E2"]) == "", "Activation needs no invented pain"
    assert intelligence.normalized_status_quo("They all use spreadsheets") == ""


def test_synthetic_research_does_not_fill_a_problem_from_list_order_without_a_bridge():
    intelligence, _ = context()
    assert intelligence.normalized_felt_need("An unrelated pain about packaging", ["E2"]) == ""
    assert intelligence.normalized_status_quo("") == ""
    assert any("no substitute pain" in warning for warning in intelligence.trace.validation_warnings)


@pytest.mark.asyncio
async def test_researched_strategy_omits_unverified_biographies_and_objections():
    intelligence, _ = context()
    adapted = adapt_researched_audience(artifacts(), research(), intelligence)
    invented = "Nobody owns the abandoned bot project"
    intelligence.objections.append(Objection(objection=invented))
    adapted.audience.objections.append(Objection(objection=invented))
    sourced = Objection(
        objection="We need to review a reply before it is sent",
        grounding=Grounding.GROUNDED,
        provenance=[Provenance(source="customer interview", quote="We need to review a reply")],
    )
    adapted.audience.objections.append(sourced)
    adapted.audience.objections.append(Objection(
        objection="Our buyer requires a trial", grounding=Grounding.USER_STATED,
    ))
    unrelated = "A founder with eleven unowned pipelines"
    adapted.audience.segments.append(Segment(name=unrelated))
    demand = DemandMap(segments=[AudienceSegment(
        name=intelligence.selected_audience, workflow="Abandoned a homemade bot last June",
    )])
    before = adapted.model_dump()
    provider = RoleScriptedProvider({"strategist": strategist_answer()})
    await Strategist(make_session(provider)).build(
        request=request(), artifacts=adapted, corpus=SourceCorpus(),
        contract=parse_contract(request().request), intelligence=intelligence, demand=demand,
    )
    prompt = provider.requests_for("strategist")[0].system_prompt
    assert invented not in prompt
    assert unrelated not in prompt
    assert "Abandoned a homemade bot last June" not in prompt
    assert sourced.objection in prompt
    assert "Our buyer requires a trial" in prompt
    assert "Repeat warranty questions consume" in prompt
    assert adapted.model_dump() == before
    assert intelligence.objections[-1].objection == invented
    assert provider.calls_by_role == {"strategist": 1}


@pytest.mark.asyncio
async def test_missing_intelligence_keeps_the_same_scripted_legacy_brief():
    provider = RoleScriptedProvider({"strategist": strategist_answer()})
    brief = await Strategist(make_session(provider)).build(
        request=request(),
        artifacts=artifacts(),
        corpus=SourceCorpus(),
        contract=parse_contract(request().request),
    )

    assert brief.orientation == "Model-authored orientation"
    assert brief.emails[0].felt_need == "A product-derived problem that research did not verify"
    assert brief.emails[0].status_quo == "They probably use a spreadsheet"
    assert brief.emails[0].must_not_say == []


@pytest.mark.asyncio
async def test_stale_dossier_is_labelled_but_never_forces_its_orientation():
    intelligence, _ = context(state=DossierState.STALE)
    provider = RoleScriptedProvider({"strategist": strategist_answer(orientation="Fresh model choice")})

    brief = await Strategist(make_session(provider)).build(
        request=request(),
        artifacts=adapt_researched_audience(artifacts(), research(), intelligence),
        corpus=SourceCorpus(),
        contract=parse_contract(request().request),
        intelligence=intelligence,
    )

    prompt = provider.requests_for("strategist")[0].system_prompt or ""
    assert brief.orientation == "Fresh model choice"
    assert "STALE ADVISORY ONLY" in prompt
    assert "market_scan_changed" in prompt


@pytest.mark.asyncio
async def test_withhold_stays_licensed_and_records_an_advisory_warning():
    intelligence, _ = context()
    provider = RoleScriptedProvider({"strategist": strategist_answer(evidence=["E4"])})

    brief = await Strategist(make_session(provider)).build(
        request=request(),
        artifacts=adapt_researched_audience(artifacts(), research(), intelligence),
        corpus=SourceCorpus(),
        contract=parse_contract(request().request),
        intelligence=intelligence,
    )

    assert brief.emails[0].evidence_ids == ["E4"]
    assert intelligence.trace.withhold_evidence_selected == ["E4"]
    assert any("WITHHOLD evidence selected" in item for item in intelligence.trace.validation_warnings)
    assert "E4" in ledger().ids


@pytest.mark.asyncio
async def test_partial_caveats_dedupe_and_existing_evidence_limits_and_spending_survive():
    intelligence, _ = context()
    answer = json.loads(strategist_answer(evidence=["E1", "E2", "E3", "E4", "E5"]))
    answer["emails"][0]["must_not_say"] = [
        "It reduces repeat triage; it does not eliminate every warranty question."
    ]
    answer["emails"].append(
        {
            **answer["emails"][0],
            "position": 2,
            "single_idea": "A second distinct argument",
            "evidence_ids": ["E1", "E6"],
        }
    )
    provider = RoleScriptedProvider({"strategist": json.dumps(answer)})

    brief = await Strategist(make_session(provider)).build(
        request=CampaignRequest(
            name="Sequence", request="Write me 2 emails", product_description="triage"
        ),
        artifacts=adapt_researched_audience(artifacts(), research(), intelligence),
        corpus=SourceCorpus(),
        contract=parse_contract("Write me 2 emails"),
        intelligence=intelligence,
    )

    assert len(brief.emails[0].evidence_ids) == MAX_EVIDENCE_PER_EMAIL
    assert brief.emails[0].must_not_say.count(
        "It reduces repeat triage; it does not eliminate every warranty question."
    ) == 1
    assert brief.emails[1].evidence_ids == ["E6"], "E1 was already spent"


def test_unknown_dossier_references_and_unavailable_fits_are_ignored_defensively():
    row = research_row()
    status = dossier_status(row)
    assert status.dossier is not None
    status.dossier.ranked_relevance.append(
        RankedRelevanceItem(evidence_id="UNKNOWN", band=RelevanceBand.LEAD, why="invented")
    )
    status.dossier.problem_fits.extend(
        [
            ProblemFit(problem_id="UNKNOWN", verdict=FitVerdict.SOLVED, evidence_ids=["E1"]),
            ProblemFit(problem_id="P1", verdict=FitVerdict.ADDRESSED, capability_ids=["C1"]),
        ]
    )
    match = resolve_audience_research(row.audience_name, [row])

    intelligence = build_campaign_intelligence(
        selected_audience=row.audience_name,
        match=match,
        dossier_status=status,
        ledger=ledger(),
    )

    assert "UNKNOWN" not in {item.evidence_id for item in intelligence.ranked_evidence}
    assert all(item.problem_id != "UNKNOWN" for item in intelligence.problem_fits)
    assert all(item.verdict is not FitVerdict.ADDRESSED for item in intelligence.problem_fits)
    assert any("unknown evidence" in item.lower() for item in intelligence.trace.validation_warnings)


@pytest.mark.asyncio
@pytest.mark.parametrize("verdict", [FitVerdict.ADDRESSED, FitVerdict.SOLVED])
@pytest.mark.parametrize("inferred", [False, True])
async def test_v2_problem_bridge_and_scope_limit_survive_into_the_writer(verdict, inferred):
    row = research_row()
    status = dossier_status(row)
    assert status.dossier is not None
    status.dossier.schema_version = 2
    status.dossier.recommendation = CampaignRecommendation(
        state=RecommendationState.RECOMMENDED_NARROW,
        readiness=CampaignReadiness.GO_NARROW,
        allowed_claims=["licensed product fact 1"],
        allowed_evidence_ids=["E1"],
    )
    caveat = "Collection operations are supported; higher participation is not established."
    status.dossier.problem_fits = [ProblemFit(
        problem_id="P1", verdict=verdict, evidence_ids=["E1"],
        capability_ids=["collection"], caveat=caveat,
    )]
    intelligence = build_campaign_intelligence(
        selected_audience=row.audience_name,
        match=resolve_audience_research(row.audience_name, [row]),
        dossier_status=status, ledger=ledger(),
    )
    if inferred:
        intelligence.problems[0].grounding = str(Grounding.INFERRED)
        intelligence.problems[0].review_notes = ["Historical sources; current demand unknown."]
    provider = RoleScriptedProvider(default_answers())
    provider.set_default("strategist", strategist_answer(evidence=["E1"]))
    current_artifacts = adapt_researched_audience(artifacts(), research(), intelligence)
    brief = await Strategist(make_session(provider)).build(
        request=request(), artifacts=current_artifacts, corpus=SourceCorpus(),
        contract=parse_contract(request().request), intelligence=intelligence,
    )

    assert [fit.verdict for fit in intelligence.problem_fits] == [verdict]
    assert caveat in brief.emails[0].must_not_say
    assert research().problems[0].statement == brief.emails[0].felt_need
    await EmailWriter(make_session(provider)).draft(
        brief=brief.emails[0], campaign=brief, request=request(),
        artifacts=current_artifacts, previous=[],
    )
    assert caveat in (provider.requests_for("email_writer")[0].system_prompt or "")
    if inferred:
        prompt = provider.requests_for("email_writer")[0].system_prompt or ""
        assert "Use it only conditionally" in prompt
        assert "Historical sources; current demand unknown." in prompt
    assert not any("Ignored unavailable" in item for item in intelligence.trace.validation_warnings)


@pytest.mark.parametrize("evidence_id", ["UNKNOWN", "E4"])
def test_v2_addressed_bridge_without_usable_evidence_still_drops(evidence_id):
    row = research_row()
    status = dossier_status(row)
    assert status.dossier is not None
    status.dossier.schema_version = 2
    status.dossier.recommendation = CampaignRecommendation(
        state=RecommendationState.RECOMMENDED_NARROW,
        readiness=CampaignReadiness.GO_NARROW,
        forbidden_evidence_ids=["E4"],
    )
    status.dossier.problem_fits = [ProblemFit(
        problem_id="P1", verdict=FitVerdict.ADDRESSED,
        evidence_ids=[evidence_id], capability_ids=["collection"],
    )]
    intelligence = build_campaign_intelligence(
        selected_audience=row.audience_name,
        match=resolve_audience_research(row.audience_name, [row]),
        dossier_status=status, ledger=ledger(),
    )
    intelligence.validate_against(ledger())
    assert intelligence.problem_fits == []


def database(*, with_dossier: bool = True):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        brand = Brand(name="Repair OS")
        other_brand = Brand(name="Other Brand")
        session.add_all([brand, other_brand])
        session.commit()
        session.refresh(brand)
        session.refresh(other_brand)
        knowledge = ArtifactStore(session).save(
            ArtifactScope(brand_id=brand.id),
            artifacts(),
            fingerprint_documents([]),
        )
        knowledge_row = KnowledgeArtifactRepository(session).latest_for_brand(brand.id)
        assert knowledge_row is not None and knowledge.version == knowledge_row.version
        store = MarketStore(session)
        research_saved = store.save_research(brand.id, research(), None)
        store.save_research(
            other_brand.id,
            research("Repair shops answering warranty requests for another brand"),
            None,
        )
        scan = store.save_scan(brand.id, MarketSnapshot())
        if with_dossier:
            template = dossier_status(research_saved).dossier
            assert template is not None
            stored_dossier = template.model_copy(
                update={
                    "audience_research_id": research_saved.id,
                    "audience_research_version": research_saved.version,
                    "knowledge_id": knowledge_row.id,
                    "knowledge_version": knowledge_row.version,
                    "market_scan_id": scan.id,
                    "market_scan_version": scan.version,
                }
            )
            store.save_dossier(brand.id, stored_dossier)
        return engine, brand.id, other_brand.id, research_saved.id


def test_db_gateway_queries_no_intelligence_without_brand_or_selection():
    engine, brand_id, _, _ = database()
    with Session(engine) as session:
        brand_campaign = Campaign(
            name="No audience",
            request="Write one email",
            product_description="Shared-inbox triage",
            brand_id=brand_id,
        )
        no_brand = Campaign(
            name="Historical",
            request="Write one email",
            product_description="Shared-inbox triage",
        )
        session.add_all([brand_campaign, no_brand])
        session.commit()
        current = artifacts()

        assert _DbKnowledgeGateway(session, brand_campaign).campaign_intelligence(current) is None
        assert _DbKnowledgeGateway(session, no_brand).campaign_intelligence(current) is None


def test_db_gateway_scopes_research_to_brand_and_selected_audience():
    engine, brand_id, _, research_id = database()
    with Session(engine) as session:
        campaign = Campaign(
            name="Selected",
            request="Write one email",
            product_description="Shared-inbox triage",
            brand_id=brand_id,
            audience_segment="Repair shops answering warranty requests",
        )
        session.add(campaign)
        session.commit()
        bundle = _DbKnowledgeGateway(session, campaign).campaign_intelligence(artifacts())

    assert bundle is not None
    assert bundle.context.trace.audience_research_id == research_id
    assert bundle.context.trace.audience_resolution_status is AudienceResolution.LOADED
    assert bundle.context.problems[0].statement.startswith("Repeat warranty")
    assert "another brand" not in bundle.context.render_for_strategy()


def test_db_gateway_resolves_need_from_this_brands_selected_map_segment():
    engine, brand_id, other_brand_id, _ = database(with_dossier=False)
    name = research().audience_name
    need = "Collect recorded repair results for the public portfolio."
    with Session(engine) as session:
        store = MarketStore(session)
        store.save_map(brand_id, DemandMap(segments=[
            AudienceSegment(name="Another workflow", need="Unrelated job"),
            AudienceSegment(name=name, need=need),
        ]))
        store.save_map(other_brand_id, DemandMap(segments=[
            AudienceSegment(name=name, need="Other brand's job"),
        ]))
        campaign = Campaign(
            name="Selected", request="Write one email", brand_id=brand_id,
            audience_segment=name,
        )
        session.add(campaign)
        session.commit()

        bundle = _DbKnowledgeGateway(session, campaign).campaign_intelligence(artifacts())

    assert bundle.context.selected_need == need
    assert bundle.artifacts.audience.primary().name == name
    assert bundle.artifacts.audience.primary().job_to_be_done == research().desired_outcomes[0].text
    assert "Other brand's job" not in bundle.context.render_for_strategy()
    assert "Unrelated job" not in bundle.context.render_for_strategy()


def test_missing_and_ambiguous_research_use_explicit_fallback_without_leakage():
    engine, brand_id, _, _ = database(with_dossier=False)
    with Session(engine) as session:
        store = MarketStore(session)
        store.save_research(
            brand_id,
            research("Shops answering warranty requests in Leeds"),
            None,
        )
        ambiguous_campaign = Campaign(
            name="Ambiguous",
            request="Write one email",
            product_description="Shared-inbox triage",
            brand_id=brand_id,
            audience_segment="Repair shops answering warranty requests in Leeds",
        )
        missing_campaign = Campaign(
            name="Missing",
            request="Write one email",
            product_description="Shared-inbox triage",
            brand_id=brand_id,
            audience_segment="Dental practices handling insurance claims",
        )
        session.add_all([ambiguous_campaign, missing_campaign])
        session.commit()

        ambiguous = _DbKnowledgeGateway(session, ambiguous_campaign).campaign_intelligence(artifacts())
        missing = _DbKnowledgeGateway(session, missing_campaign).campaign_intelligence(artifacts())

    assert ambiguous is not None
    assert ambiguous.context.trace.audience_resolution_status is AudienceResolution.AMBIGUOUS
    assert ambiguous.artifacts.audience.primary().situation == (
        "A discovery hypothesis about repair shops."
    )
    assert missing is not None
    assert missing.context.trace.audience_resolution_status is AudienceResolution.MISSING
    assert missing.context.problems == []


def test_db_gateway_reports_current_missing_and_stale_dossier_postures():
    current_engine, brand_id, _, _ = database()
    missing_engine, missing_brand, _, _ = database(with_dossier=False)
    with Session(current_engine) as session:
        campaign = Campaign(
            name="Current",
            request="Write one email",
            product_description="Shared-inbox triage",
            brand_id=brand_id,
            audience_segment=research().audience_name,
        )
        session.add(campaign)
        session.commit()
        current = _DbKnowledgeGateway(session, campaign).campaign_intelligence(artifacts())
        MarketStore(session).save_scan(brand_id, MarketSnapshot())
        stale = _DbKnowledgeGateway(session, campaign).campaign_intelligence(artifacts())
    with Session(missing_engine) as session:
        campaign = Campaign(
            name="Missing dossier",
            request="Write one email",
            product_description="Shared-inbox triage",
            brand_id=missing_brand,
            audience_segment=research().audience_name,
        )
        session.add(campaign)
        session.commit()
        missing = _DbKnowledgeGateway(session, campaign).campaign_intelligence(artifacts())

    assert current is not None and current.context.trace.dossier_status is DossierPosture.CURRENT
    assert stale is not None and stale.context.trace.dossier_status is DossierPosture.STALE
    assert stale.context.trace.stale_reasons == ["market_scan_changed"]
    assert missing is not None and missing.context.trace.dossier_status is DossierPosture.MISSING
    assert missing.context.trace.legacy_fallback_used


@pytest.mark.asyncio
async def test_pipeline_emits_and_persists_intelligence_trace_without_research_or_relevance_calls():
    engine, brand_id, _, research_id = database()
    provider = RoleScriptedProvider(default_answers())
    provider.set_default("strategist", strategist_answer())
    with Session(engine) as session:
        campaign = Campaign(
            name="Integrated",
            request="Write me 1 email for repair shops",
            product_description="Shared-inbox triage",
            brand_id=brand_id,
            audience_segment=research().audience_name,
            policy={
                "preset": "fast",
                "require_proof": False,
                "draft_candidates": 1,
                "max_revisions": 0,
                "subject_variants": 0,
            },
        )
        session.add(campaign)
        session.commit()
        session.refresh(campaign)
        execution = await CampaignOrchestrator(session, provider).run(campaign)
        intelligence_events = session.exec(
            select(ExecutionLog)
            .where(ExecutionLog.campaign_execution_id == execution.id)
            .where(ExecutionLog.event_type == "phase")
        ).all()

    trace = execution.result["intelligence"]
    assert trace["audience_research_id"] == str(research_id)
    assert trace["dossier_status"] == "current"
    assert trace["dossier_id"]
    assert trace["dossier_version"] == 1
    assert any(event.data.get("phase") == "intelligence" for event in intelligence_events)
    assert provider.calls_by_role["audience_researcher"] == 0
    assert provider.calls_by_role["relevance_analyst"] == 0
    assert provider.calls_by_role["strategist"] == 1


@pytest.mark.asyncio
async def test_pipeline_reader_persona_receives_researched_situation_without_reader_changes():
    intelligence, _ = context()
    adapted = adapt_researched_audience(artifacts(), research(), intelligence)
    provider = RoleScriptedProvider(default_answers())
    provider.set_default("strategist", strategist_answer())
    pipeline = EmailCampaignPipeline(
        session=make_session(provider),
        knowledge=IntelligenceGateway(
            CampaignIntelligenceBundle(artifacts=adapted, context=intelligence)
        ),
        policy=PRESETS["fast"].model_copy(
            update={"draft_candidates": 1, "max_revisions": 0, "subject_variants": 0}
        ),
    )

    await pipeline.run(request())

    reader_prompt = provider.requests_for("blind_reader")[0].system_prompt or ""
    assert "opens the shared inbox before starting repairs" in reader_prompt


@pytest.mark.asyncio
async def test_complete_ledger_reaches_strategy_and_contract_correction_is_unchanged():
    intelligence, _ = context()
    provider = RoleScriptedProvider(default_answers())
    provider.push("strategist", strategist_answer(), campaign_brief(2))
    request_two = CampaignRequest(
        name="Sequence", request="Write me 2 emails", product_description="triage"
    )

    brief = await Strategist(make_session(provider)).build(
        request=request_two,
        artifacts=adapt_researched_audience(artifacts(), research(), intelligence),
        corpus=SourceCorpus(),
        contract=parse_contract(request_two.request),
        intelligence=intelligence,
    )

    prompt = provider.requests_for("strategist")[0].system_prompt or ""
    assert all(f"[E{index}]" in prompt for index in range(1, 7))
    assert provider.calls_by_role["strategist"] == 2
    assert len(brief.emails) == 2


@pytest.mark.asyncio
async def test_v2_withheld_evidence_is_removed_before_strategy_writer_and_critic_slices():
    intelligence, _ = context()
    intelligence.trace.dossier_schema_version = 2
    intelligence.recommendation_state = RecommendationState.RECOMMENDED_NARROW
    intelligence.readiness = CampaignReadiness.GO_NARROW
    intelligence.allowed_evidence_ids = ["E1"]
    intelligence.forbidden_evidence_ids = ["E4"]
    intelligence.forbidden_capability_ids = ["voice_telephony"]
    intelligence.forbidden_claims = ["Do not make the withheld claim."]
    intelligence.selected_company_name = "Unreadable Repair Co"
    provider = RoleScriptedProvider(default_answers())
    provider.set_default("strategist", strategist_answer(evidence=["E1", "E4"]))
    current_artifacts = adapt_researched_audience(artifacts(), research(), intelligence)

    brief = await Strategist(make_session(provider)).build(
        request=request(),
        artifacts=current_artifacts,
        corpus=SourceCorpus(),
        contract=parse_contract(request().request),
        intelligence=intelligence,
    )

    planned = brief.emails[0]
    strategy_prompt = provider.requests_for("strategist")[0].system_prompt or ""
    assert planned.evidence_ids == ["E1"]
    # E2/E3/E5/E6 were never selected, but are just as unavailable as the
    # explicitly excluded E4. Later reader-question retrieval must not revive them.
    assert planned.forbidden_evidence_ids == ["E2", "E3", "E4", "E5", "E6"]
    assert planned.forbidden_capability_ids == ["voice_telephony"]
    assert any(
        "Do not state that Unreadable Repair Co has an internal problem" in item
        for item in planned.must_not_say
    )
    assert "[E1]" in strategy_prompt
    assert "[E4]" not in strategy_prompt
    assert "Licensed product fact 4" not in strategy_prompt

    await EmailWriter(make_session(provider)).draft(
        brief=planned,
        campaign=brief,
        request=request(),
        artifacts=current_artifacts,
        previous=[],
    )
    writer_prompt = provider.requests_for("email_writer")[0].system_prompt or ""
    assert "[E1]" in writer_prompt
    assert "[E4]" not in writer_prompt
    assert "Licensed product fact 4" not in writer_prompt
    assert current_artifacts.evidence.slice_for(
        ["E1", "E4"], excluded_ids=frozenset(planned.forbidden_evidence_ids)
    ).ids == {"E1"}
