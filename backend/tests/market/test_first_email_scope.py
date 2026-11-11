"""A documented-use draft cannot silently qualify a broader audience or request."""

from uuid import uuid4

import pytest

from app.knowledge.artifacts import KnowledgeArtifacts
from app.market.capabilities import derive_capability_profile
from app.market.relevance import (
    CampaignReadiness,
    DefiningNeedFit,
    FirstEmailScope,
    FitVerdict,
    ProblemFitProposal,
    RankedRelevanceProposal,
    RelevanceAnalyst,
    RelevanceBand,
    RelevanceDossier,
    RelevanceProposal,
    normalize_dossier,
    recommendation_for_request,
)
from tests.market.test_relevance import ledger, positioning, research
from tests.marketing.conftest import RoleScriptedProvider, make_session

REQUEST = "Write exactly one email. Introduce the product with one clear next step."


@pytest.mark.asyncio
@pytest.mark.parametrize("reviewed_id", ["E2", "E3"])
async def test_automatic_scope_uses_reviewed_workflow_and_preserves_withholds(reviewed_id):
    evidence = ledger()
    profile = derive_capability_profile(evidence, knowledge_id=uuid4(), knowledge_version=1)
    proposal = RelevanceProposal(
        defining_need_fit=DefiningNeedFit(
            status="partial", evidence_ids=["E2"],
            unverified_requirements=["Migration without changing the support stack"],
            caveat="The complete proposed audience workflow remains unverified.",
        ),
        first_email_scope=FirstEmailScope(
            status="addressed", workflow="Try the API and get automatic migration",
            evidence_ids=["E2"], excluded_promises=["No guaranteed migration"],
        ),
        ranked_relevance=[
            RankedRelevanceProposal(evidence_id="E2", band=RelevanceBand.SUPPORT, why="API"),
            RankedRelevanceProposal(evidence_id="E3", band=RelevanceBand.WITHHOLD, why="Outside scope"),
        ],
        problem_fits=[ProblemFitProposal(problem_id="P1", verdict=FitVerdict.SOLVED, evidence_ids=["E1"])],
    )
    reviewed = FirstEmailScope(
        status="addressed", workflow="Use the documented shared-inbox API",
        evidence_ids=[reviewed_id], excluded_promises=["No automatic migration in this workflow"],
    )
    provider = RoleScriptedProvider()
    provider.push("relevance_dossier", proposal.model_dump_json())
    provider.push("first_email_scope_review", reviewed.model_dump_json())
    dossier = await RelevanceAnalyst(make_session(provider)).analyse(
        artifacts=KnowledgeArtifacts(evidence=evidence),
        knowledge_id=profile.knowledge_id, knowledge_version=1,
        research=research(), research_id=uuid4(), research_version=1,
        positioning=positioning(), market_scan_id=uuid4(), market_scan_version=1,
        capability_profile=profile, compact=True, draft_request=REQUEST,
    )
    assert len(provider.requests_for("relevance_analyst")) == 2
    recommendation = recommendation_for_request(dossier, REQUEST)
    if reviewed_id == "E2":
        assert recommendation.readiness is CampaignReadiness.GO_NARROW
        assert recommendation.eligible_subsegment == reviewed.workflow
        assert dossier.first_email_scope.excluded_promises == [
            "No guaranteed migration", "No automatic migration in this workflow",
        ]
    else:
        assert recommendation.readiness is CampaignReadiness.DISCOVERY_ONLY


def scoped_dossier(*, refs=None, withheld=False, unmet=False, request=REQUEST, unknown_required=False,
                  audience_question=None):
    evidence = ledger()
    profile = derive_capability_profile(evidence, knowledge_id=uuid4(), knowledge_version=1)
    audience = research()
    if unknown_required:
        audience.definition.required_product_capabilities = ["unknown_required_capability"]
    proposal = RelevanceProposal(
        defining_need_fit=DefiningNeedFit(
            status="partial", evidence_ids=["E2"],
            unverified_requirements=["Migration without changing the support stack"],
            caveat="The complete proposed audience workflow remains unverified.",
        ),
        first_email_scope=FirstEmailScope(
            request="A model cannot bind this licence to another request",
            status="addressed", workflow="Collaborate through the documented shared-inbox API",
            evidence_ids=refs if refs is not None else ["E2"],
            setup_conditions=["Connect through the documented API."],
            excluded_promises=["No disruptive migration"],
            audience_decision_question=audience_question,
            unmet_user_requirements=["The user explicitly requires no stack change."] if unmet else [],
        ),
        ranked_relevance=[RankedRelevanceProposal(
            evidence_id="E2", band=RelevanceBand.WITHHOLD if withheld else RelevanceBand.SUPPORT,
            why="Documented mechanism.",
        )],
        problem_fits=[ProblemFitProposal(problem_id="P1", verdict=FitVerdict.SOLVED, evidence_ids=["E1"])],
    )
    return normalize_dossier(
        proposal, ledger=evidence, research=audience, positioning=positioning(),
        knowledge_id=profile.knowledge_id, knowledge_version=1,
        research_id=uuid4(), research_version=1, market_scan_id=uuid4(), market_scan_version=1,
        capability_profile=profile, draft_request=request,
    )


def test_first_email_scope_does_not_upgrade_the_complete_audience_or_another_request():
    dossier = scoped_dossier()
    assert dossier.recommendation.readiness is CampaignReadiness.DISCOVERY_ONLY
    assert dossier.defining_need_fit.status == "partial"
    assert dossier.first_email_scope.request == REQUEST
    scoped = recommendation_for_request(dossier, REQUEST)
    assert scoped.readiness is CampaignReadiness.GO_NARROW
    assert scoped.allowed_evidence_ids == dossier.recommendation.allowed_evidence_ids
    assert not scoped.qualified_companies
    assert recommendation_for_request(dossier, REQUEST + " Guarantee no migration.") is dossier.recommendation
    assert recommendation_for_request(dossier, "") is dossier.recommendation
    restored = RelevanceDossier.model_validate_json(dossier.model_dump_json())
    assert recommendation_for_request(restored, REQUEST).readiness is CampaignReadiness.GO_NARROW


@pytest.mark.parametrize("options", [
    {"refs": ["invented"]}, {"refs": ["E2", "invented"]},
    {"refs": ["E1"]}, {"withheld": True}, {"unmet": True}, {"request": ""},
    {"unknown_required": True},
])
def test_invalid_or_unsatisfied_scope_cannot_license_a_draft(options):
    dossier = scoped_dossier(**options)
    assert recommendation_for_request(dossier, REQUEST).readiness is CampaignReadiness.DISCOVERY_ONLY


def test_explicit_missing_user_requirement_blocks_even_a_globally_positive_audience():
    from app.market.relevance import RecommendationState

    dossier = scoped_dossier(unmet=True)
    dossier.recommendation = dossier.recommendation.model_copy(update={
        "state": RecommendationState.RECOMMENDED, "readiness": CampaignReadiness.GO,
    })
    assert recommendation_for_request(dossier, REQUEST).readiness is CampaignReadiness.DISCOVERY_ONLY


def test_known_fact_selected_for_the_scoped_email_gets_ordinary_contract_checks():
    dossier = scoped_dossier(refs=["E2", "E3"])
    assert "E3" in dossier.recommendation.allowed_evidence_ids
    assert recommendation_for_request(dossier, REQUEST).readiness is CampaignReadiness.GO_NARROW
    assert any(item.evidence_id == "E3" and item.band is RelevanceBand.SUPPORT
               for item in dossier.ranked_relevance)


def test_generic_workflow_does_not_license_an_email_with_a_decisive_audience_gap():
    question = "Can an agency see one client's tasks separately?"
    dossier = scoped_dossier(audience_question=question)
    assert dossier.first_email_scope.audience_decision_question == question
    assert recommendation_for_request(dossier, REQUEST).readiness is CampaignReadiness.DISCOVERY_ONLY


def test_scoped_constraints_and_task_reach_strategy_without_erasing_the_rejected_promise():
    from types import SimpleNamespace

    from app.market.relevance import RelevanceStatus
    from app.marketing.intelligence import (
        AudienceResearchMatch,
        AudienceResolution,
        build_campaign_intelligence,
    )

    dossier = scoped_dossier()
    match = AudienceResearchMatch(status=AudienceResolution.LOADED,
                                  row=SimpleNamespace(id=dossier.audience_research_id, version=1),
                                  research=research())
    context = build_campaign_intelligence(
        selected_audience=research().audience_name, match=match, ledger=ledger(),
        dossier_status=RelevanceStatus(audience_name=research().audience_name, status="current", dossier=dossier),
        campaign_request=REQUEST,
    )
    assert context.readiness is CampaignReadiness.GO_NARROW
    assert context.selected_need == dossier.first_email_scope.workflow
    rendered = context.render_for_strategy()
    assert "Do not promise: No disruptive migration" in rendered
    assert "Not established: Migration without changing the support stack" in rendered
    assert "Connect through the documented API." in rendered
    constraints = context.constraints_for(["E2"], ledger())
    assert "Connect through the documented API." not in constraints
    assert "Do not promise: No disruptive migration" in constraints
