import pytest

from app.market.capabilities import derive_capability_profile
from app.market.relevance import (
    DefiningNeedFit,
    FitVerdict,
    ProblemFitProposal,
    RankedRelevanceProposal,
    RecommendationState,
    RelevanceBand,
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


def test_supported_alternative_keeps_setup_and_never_qualifies_the_whole_audience():
    audience = research().model_copy(update={"audience_name": "Inbox or ticketing teams"})
    dossier = normalize(proposal(DefiningNeedFit(
        status="addressed", evidence_ids=["E2"], supported_alternative="Inbox",
        setup_conditions=["Connect the shared inbox through the documented API."],
        caveat="Ticketing migration is not documented.",
    )), audience=audience)
    result = recommend_campaign(dossier, profile=derive_capability_profile(
        ledger(), knowledge_id=dossier.knowledge_id, knowledge_version=3,
    ), research=audience, companies=[], ledger=ledger())
    assert result.state is RecommendationState.RECOMMENDED_NARROW
    assert result.eligible_subsegment == "Inbox"
    assert dossier.defining_need_fit.setup_conditions


def test_alternative_scope_cannot_drop_a_required_conjunction():
    audience = research().model_copy(update={"audience_name": "Inbox and ticketing teams"})
    dossier = normalize(proposal(DefiningNeedFit(
        status="addressed", evidence_ids=["E2"], supported_alternative="Inbox",
    )), audience=audience)
    assert dossier.defining_need_fit.status == "partial"
    assert dossier.defining_need_fit.supported_alternative == ""
    assert recommendation(dossier).state is RecommendationState.DISCOVERY_ONLY


def test_unknown_alternative_or_evidence_cannot_create_supported_scope():
    audience = research().model_copy(update={"audience_name": "Inbox or ticketing teams"})
    wrong = normalize(proposal(DefiningNeedFit(
        status="addressed", evidence_ids=["E2"], supported_alternative="Phone",
    )), audience=audience)
    assert wrong.defining_need_fit.status == "partial"
    no_proof = normalize(proposal(DefiningNeedFit(
        status="addressed", evidence_ids=["invented"], supported_alternative="Inbox",
    )), audience=audience)
    assert no_proof.defining_need_fit.status == "unknown"


def test_optional_questions_do_not_erase_the_evidenced_complete_core_task():
    core = "Automatically send a newsletter from the blog RSS feed."
    question = "Whether every future post will display perfectly."
    dossier = normalize(proposal(DefiningNeedFit(
        status="partial", evidence_ids=["E2"], supported_core_workflow=core,
        unverified_requirements=[question],
        caveat="Initial template setup is required.",
    )), audience_scope={"need": core})
    assert dossier.defining_need_fit.status == "addressed"
    assert dossier.defining_need_fit.unverified_requirements == []
    assert question in dossier.defining_need_fit.decision_gaps
    assert dossier.defining_need_fit.caveat == "Initial template setup is required."


def test_an_explicit_core_condition_stays_unverified_even_with_secondary_proof():
    core = "Measure the traffic gap caused specifically by consent rejection."
    question = "Consent-specific causal attribution is not established."
    dossier = normalize(proposal(DefiningNeedFit(
        status="partial", evidence_ids=["E2"],
        unverified_requirements=[question],
        unverified_requirement_basis={question: "caused specifically by consent rejection"},
    )), audience_scope={"need": core})
    assert dossier.defining_need_fit.status == "partial"
    assert dossier.defining_need_fit.unverified_requirements == [question]
    assert recommendation(dossier).state is RecommendationState.DISCOVERY_ONLY


def test_contradictory_core_support_stays_provisional_without_buying_a_repair_call():
    core = "Automatic RSS delivery"
    question = "Automatic RSS delivery is unverified."
    fit = DefiningNeedFit(status="addressed", supported_core_workflow=core, evidence_ids=["E2"],
                         unverified_requirements=[question], unverified_requirement_basis={question: core})
    dossier = normalize(proposal(fit), audience_scope={"need": core})
    assert dossier.defining_need_fit.status == "partial"
    assert dossier.defining_need_fit.supported_core_workflow == ""
    assert question in dossier.defining_need_fit.unverified_requirements
    assert any("Contradictory" in warning for warning in dossier.validation_warnings)
    assert recommendation(dossier).state is RecommendationState.DISCOVERY_ONLY


@pytest.mark.parametrize("band,required,expected", [
    (RelevanceBand.LEAD, [], RecommendationState.RECOMMENDED_NARROW),
    (RelevanceBand.WITHHOLD, [], RecommendationState.DISCOVERY_ONLY),
    (RelevanceBand.LEAD, ["unknown-capability"], RecommendationState.DISCOVERY_ONLY),
])
def test_a_scoped_hypothesis_draft_does_not_invent_demand_or_qualify_recipients(band, required, expected):
    audience = research().model_copy(update={"problems": []})
    audience.definition.required_product_capabilities = required
    core = "Operate the documented workflow."
    dossier = normalize(RelevanceProposal(
        defining_need_fit=DefiningNeedFit(status="addressed", supported_core_workflow=core, evidence_ids=["E2"]),
        ranked_relevance=[RankedRelevanceProposal(evidence_id="E2", band=band, why="Documents the workflow.")],
    ), audience=audience, audience_scope={"need": core})
    result = recommend_campaign(dossier, profile=derive_capability_profile(
        ledger(), knowledge_id=dossier.knowledge_id, knowledge_version=3,
    ), research=audience, companies=[], ledger=ledger())
    assert result.state is expected
    assert not result.qualified_companies
    assert not dossier.problem_fits
    if expected is RecommendationState.RECOMMENDED_NARROW:
        assert "no firsthand buyer problem" in " ".join(result.reasons)
        assert "unconfirmed" in result.recommended_next_action
        assert any("unverified" in warning for warning in result.claim_contract.warnings)


def test_a_claimed_complete_fit_without_the_exact_core_assessment_stays_unknown():
    dossier = normalize(proposal(DefiningNeedFit(status="addressed", evidence_ids=["E2"])),
                        audience_scope={"need": "Operate the complete selected workflow."})
    assert dossier.defining_need_fit.status == "unknown"
    assert recommendation(dossier).state is RecommendationState.DISCOVERY_ONLY
