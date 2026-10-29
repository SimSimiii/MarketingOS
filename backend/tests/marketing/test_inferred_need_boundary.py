"""Sourced hypotheses may inform copy without becoming known recipient facts."""

import pytest

from app.knowledge.artifacts import Grounding
from app.market.audience_research import EvidenceReference, interpretation_reversal
from app.market.relevance import FitVerdict, RecommendationState
from app.marketing.intelligence import (
    AudienceResolution,
    CampaignIntelligence,
    CampaignIntelligenceTrace,
    DossierPosture,
    IntelligenceFit,
    IntelligenceProblem,
)
from app.marketing.report import EmailReportLine


def context():
    return CampaignIntelligence(
        selected_audience="Technical founders",
        trace=CampaignIntelligenceTrace(
            selected_audience="Technical founders",
            audience_resolution_status=AudienceResolution.LOADED,
            dossier_status=DossierPosture.CURRENT, dossier_schema_version=2,
        ),
        recommendation_state=RecommendationState.RECOMMENDED_NARROW,
        allowed_evidence_ids=["E1"],
        problems=[IntelligenceProblem(
            id="P1", statement="Analytics reports are difficult to navigate.",
            grounding=str(Grounding.INFERRED),
            evidence=[EvidenceReference(source_id="S1", quote="Analytics reports are difficult to navigate.")],
        )],
        problem_fits=[IntelligenceFit(problem_id="P1", verdict=FitVerdict.ADDRESSED, evidence_ids=["E1"])],
    )


@pytest.mark.parametrize("defect", ["stale", "legacy", "forbidden", "unlicensed", "unlinked", "unsourced", "reversal", "partial"])
def test_conditional_need_still_requires_a_current_licensed_sourced_fit(defect):
    item = context()
    if defect == "stale":
        item.trace.dossier_status = DossierPosture.STALE
    elif defect == "legacy":
        item.trace.dossier_schema_version = 1
    elif defect == "forbidden":
        item.forbidden_evidence_ids = ["E1"]
    elif defect == "unlicensed":
        item.allowed_evidence_ids = []
    elif defect == "unlinked":
        item.problem_fits = []
    elif defect == "unsourced":
        item.problems[0].evidence = []
    elif defect == "reversal":
        item.problems[0].statement = "Analytics reports are easier to navigate."
    elif defect == "partial":
        item.problem_fits[0].verdict = FitVerdict.PARTIAL
    assert item.normalized_felt_need("Analytics pain", ["E1"], ["P1"]) == ""


def test_complex_incumbent_and_simpler_alternative_are_different_objects():
    evidence = [EvidenceReference(source_id="S1", quote="Google Analytics reports are harder to navigate.")]
    assert not interpretation_reversal(
        "Google Analytics reports are too complex, pushing site owners toward simpler alternatives.", evidence,
    )
    assert interpretation_reversal("Google Analytics reports are simpler to navigate.", evidence)


def test_review_status_does_not_misreport_a_high_pull_score_as_below_threshold():
    rendered = EmailReportLine(position=1, pull=8, landed=False).render()
    assert "below" not in rendered
    assert "unresolved review" in rendered
