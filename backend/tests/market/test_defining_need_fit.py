from app.market.capabilities import derive_capability_profile
from app.market.relevance import (
    DefiningNeedFit,
    FitVerdict,
    ProblemFitProposal,
    RecommendationState,
    RelevanceProposal,
    recommend_campaign,
)
from tests.market.test_relevance import ledger, normalize, research


def proposal(fit):
    return RelevanceProposal(defining_need_fit=fit, problem_fits=[ProblemFitProposal(
        problem_id="P1", verdict=FitVerdict.SOLVED, evidence_ids=["E1"],
    )])


def recommendation(dossier):
    evidence = ledger()
    audience = research()
    audience.definition.eligible_subsegments = ["A broader-sounding buyer label"]
    return recommend_campaign(dossier, profile=derive_capability_profile(
        evidence, knowledge_id=dossier.knowledge_id, knowledge_version=3,
    ), research=audience, companies=[], ledger=evidence)


def test_a_positive_secondary_problem_and_broad_label_cannot_redeem_missing_core_requirement():
    dossier = normalize(proposal(DefiningNeedFit(
        status="addressed", evidence_ids=["E1"],
        unverified_requirements=["The complete required workflow remains unverified."],
    )))
    assert dossier.defining_need_fit.status == "partial"
    result = recommendation(dossier)
    assert result.state is RecommendationState.DISCOVERY_ONLY
    assert "defining audience need" in " ".join(result.reasons)
    assert "Target only" not in result.recommended_next_action


def test_unknown_reference_cannot_license_a_complete_fit():
    dossier = normalize(proposal(DefiningNeedFit(status="addressed", evidence_ids=["invented"])))
    assert dossier.defining_need_fit.status == "unknown"
    assert recommendation(dossier).state is RecommendationState.DISCOVERY_ONLY


def test_documented_task_fit_does_not_require_inventing_customer_outcome_proof():
    dossier = normalize(proposal(DefiningNeedFit(status="addressed", evidence_ids=["E2"],
                                                why="The published API performs the required task.")))
    assert recommendation(dossier).state is RecommendationState.RECOMMENDED


def test_missing_complete_need_assessment_is_explicit_and_does_not_become_go():
    dossier = normalize(proposal(None))
    assert dossier.defining_need_fit.status == "unknown"
    assert recommendation(dossier).state is RecommendationState.DISCOVERY_ONLY
