"""Campaign Quality Evaluation V1 stays deterministic unless live is explicit."""

from __future__ import annotations

import json
from collections import deque
from collections.abc import AsyncIterator

import pytest
from pydantic import ValidationError

from app.ai.base import AIProvider, AIRequest, AIResponse
from app.ai.model_router import ModelRouter
from app.core.config import PROMPTS_DIR
from app.evaluation import campaign_quality_bench
from app.evaluation.campaign_quality import (
    CampaignQualityCase,
    CommercialReviewer,
    QualityVerdict,
    evaluate_campaign,
    evaluate_deterministic,
)
from app.evaluation.campaign_quality_bench import (
    _context_from_stored,
    load_case,
    render_markdown,
    write_artifacts,
)
from app.knowledge.artifacts import BusinessProfile, KnowledgeArtifacts
from app.knowledge.ledger import Evidence, EvidenceKind, EvidenceLedger
from app.market.qualification import (
    CompanyQualification,
    CompanySignal,
    EvidenceCompleteness,
    QualificationClass,
    QualificationDimension,
    Reachability,
    SignalGrounding,
)
from app.market.relevance import (
    CampaignReadiness,
    CampaignRecommendation,
    RecommendationState,
)
from app.models.campaign import Campaign
from app.runtime.events import EventBus
from app.runtime.model_session import ModelSession
from app.runtime.prompt_engine import get_prompt_engine
from app.schemas.campaign import CampaignGenerationAdvice


class _ScriptedProvider(AIProvider):
    def __init__(self, *responses: str) -> None:
        self.responses = deque(responses)
        self.requests: list[AIRequest] = []

    async def generate(self, request: AIRequest) -> AIResponse:
        self.requests.append(request)
        return AIResponse(content=self.responses.popleft(), model=request.model or "scripted")

    async def stream(self, request: AIRequest) -> AsyncIterator[str]:
        response = await self.generate(request)
        yield response.content

    def count_tokens(self, text: str) -> int:
        return len(text.split())


def _session(provider: AIProvider) -> ModelSession:
    return ModelSession(
        provider=provider,
        prompt_engine=get_prompt_engine(PROMPTS_DIR),
        events=EventBus(),
        model_router=ModelRouter(),
        execution_id="campaign-quality-test",
    )


def _findings(case: CampaignQualityCase, rule_id: str):
    report = evaluate_deterministic(case)
    return [
        finding
        for draft in report.drafts
        for finding in draft.findings
        if finding.rule_id == rule_id
    ]


def _commercial_answer(winner: str = "A", score: int = 4) -> str:
    def rubric() -> dict:
        return {
            name: {"score": score, "evidence": f"Concrete evidence for {name}."}
            for name in (
                "specificity_to_audience_company",
                "relevance_of_problem",
                "credibility_trust",
                "value_clarity",
                "differentiation",
                "readability_flow",
                "cta_quality",
                "likely_reply_interest",
                "spamminess_generic_ai_tone",
            )
        }

    return json.dumps(
        {
            "drafts": [
                {"label": "A", "rubric": rubric()},
                {"label": "B", "rubric": rubric()},
            ],
            "winner": winner,
            "comparison_evidence": "The winner makes the mechanism easier to verify.",
        }
    )


def test_regression_fixtures_cover_the_required_cases():
    expected = {
        "strong-grounded": QualityVerdict.SAFE_TO_REVIEW,
        "generic-safe": QualityVerdict.NEEDS_REVISION,
        "false-voice": QualityVerdict.UNSAFE,
        "false-backend-replacement": QualityVerdict.UNSAFE,
        "invented-company-problem": QualityVerdict.UNSAFE,
        "blind-comparison": QualityVerdict.SAFE_TO_REVIEW,
    }

    assert {name: evaluate_deterministic(load_case(name)).verdict for name in expected} == expected

    comparison = load_case("blind-comparison")
    assert len(comparison.drafts) == 2
    assert len(comparison.context.buyer_personas) >= 2

    with pytest.raises(ValidationError):
        CampaignQualityCase(id="empty", drafts=[])


def test_forbidden_voice_claim_names_the_text_and_rule_reference():
    findings = _findings(load_case("false-voice"), "CQ-SAF-001")

    assert findings
    assert "handles inbound voice calls" in findings[0].offending_text
    assert findings[0].reference_ids == ["F-NO-VOICE"]


def test_high_risk_voice_and_backend_claims_are_unsafe_without_evidence():
    voice = _findings(load_case("false-voice"), "CQ-SAF-002")
    backend = _findings(load_case("false-backend-replacement"), "CQ-SAF-002")

    assert {item.reference_ids[0] for item in voice} == {"RISK-VOICE-TELEPHONY"}
    assert "handles inbound voice calls" in voice[0].offending_text
    assert any(item.reference_ids == ["RISK-FULL-BACKEND"] for item in backend)


def test_hipaa_and_an_unlicensed_number_are_reported_separately():
    case = load_case("strong-grounded").model_copy(deep=True)
    case.drafts[
        0
    ].email.body += "\n\nNotewright is HIPAA compliant and improves response quality by 73%."

    report = evaluate_deterministic(case)
    by_rule = {finding.rule_id: finding for draft in report.drafts for finding in draft.findings}

    assert report.verdict is QualityVerdict.UNSAFE
    assert by_rule["CQ-SAF-002"].reference_ids == ["RISK-HIPAA"]
    assert by_rule["CQ-SAF-005"].offending_text == "73%"


def test_invented_company_problem_is_not_licensed_by_unrelated_company_evidence():
    findings = _findings(load_case("invented-company-problem"), "CQ-SAF-003")

    assert len(findings) == 1
    assert "Northstar's support team loses handoffs" in findings[0].offending_text
    assert findings[0].reference_ids == []

    subject_only = load_case("invented-company-problem").model_copy(deep=True)
    subject_only.drafts[0].email.subject = "Northstar uses three disconnected support queues"
    subject_only.drafts[
        0
    ].email.body = "RelayDesk drafts support replies from approved knowledge articles for review."
    subject_findings = _findings(subject_only, "CQ-SAF-003")
    assert any(finding.location == "subject" for finding in subject_findings)


def test_a_product_assertion_outside_the_safe_contract_is_blocking():
    case = load_case("strong-grounded").model_copy(deep=True)
    case.drafts[0].email.body += "\n\nNotewright deploys every release to production for you."

    findings = _findings(case, "CQ-SAF-004")

    assert findings
    assert "deploys every release" in findings[0].offending_text

    case.drafts[0].email.body = load_case("strong-grounded").drafts[0].email.body
    case.drafts[0].email.subject = "Notewright deploys releases for you"
    assert any(finding.location == "subject" for finding in _findings(case, "CQ-SAF-004"))


def test_weak_cta_contradiction_density_and_repetition_have_stable_rules():
    generic = load_case("generic-safe")
    assert _findings(generic, "CQ-COM-001")[0].offending_text == "Learn more"

    contradiction = load_case("strong-grounded").model_copy(deep=True)
    contradiction.drafts[0].email.subject = "No setup required"
    contradiction.drafts[0].email.body = (
        "Setup requires an administrator before the first draft can be created. "
        + contradiction.drafts[0].email.body
    )
    assert _findings(contradiction, "CQ-COM-002")

    repeated = load_case("strong-grounded").model_copy(deep=True)
    repeated.drafts[
        0
    ].email.body += (
        "\n\nNotewright turns a merged pull request into a draft release note in about 9 seconds."
    )
    repeat_findings = _findings(repeated, "CQ-COM-004")
    assert repeat_findings
    assert "E-MECHANISM-1" in {
        reference for finding in repeat_findings for reference in finding.reference_ids
    }

    dense = load_case("strong-grounded").model_copy(deep=True)
    dense.drafts[0].email.body = (
        "Notewright drafts release notes.\n\n"
        "Notewright creates update summaries.\n\n"
        "Notewright provides an editing view.\n\n"
        "Notewright generates a first version.\n\n"
        "Notewright keeps changes organised.\n\n"
        "Notewright writes release communication."
    )
    assert _findings(dense, "CQ-COM-003")


def test_artifact_generation_writes_machine_and_human_readable_reports(tmp_path):
    report = evaluate_deterministic(load_case("false-voice"))

    json_path, markdown_path = write_artifacts(report, tmp_path)

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    markdown = markdown_path.read_text(encoding="utf-8")
    assert payload["verdict"] == "UNSAFE"
    assert payload["drafts"][0]["checks"]
    assert "CQ-SAF-001" in markdown
    assert "Revision priorities" in markdown
    assert "handles inbound voice calls" in markdown


def test_deterministic_cli_never_constructs_a_model_provider(monkeypatch, tmp_path):
    def forbidden_provider_call():
        raise AssertionError("deterministic evaluation must not construct a provider")

    monkeypatch.setattr(campaign_quality_bench, "get_ai_provider", forbidden_provider_call)

    exit_code = campaign_quality_bench.main(
        ["--campaign", "strong-grounded", "--out", str(tmp_path)]
    )

    assert exit_code == 0
    assert (tmp_path / "strong-grounded.json").is_file()
    assert (tmp_path / "strong-grounded.md").is_file()


@pytest.mark.asyncio
async def test_live_review_is_mocked_blind_and_rotates_order_by_persona():
    case = load_case("blind-comparison")
    provider = _ScriptedProvider(_commercial_answer("A"), _commercial_answer("A"))

    report = await evaluate_campaign(case, CommercialReviewer(_session(provider)))

    requests = provider.requests
    assert len(requests) == len(case.context.buyer_personas) == 2
    assert report.commercial_review is not None
    assert report.commercial_review.model_calls == 2
    assert report.commercial_review.blind is True
    assert all(
        draft.id not in request.system_prompt for request in requests for draft in case.drafts
    )
    first = report.commercial_review.personas[0]
    second = report.commercial_review.personas[1]
    assert first.drafts[0].draft_id != second.drafts[0].draft_id
    assert "DRAFT A" in requests[0].system_prompt
    assert "DRAFT B" in requests[0].system_prompt
    assert report.verdict is QualityVerdict.SAFE_TO_REVIEW


def test_v2_generation_snapshot_is_the_read_only_claim_boundary():
    campaign = Campaign(
        name="V2 campaign",
        request="Write one email for support leaders",
        product_description="A broad description that is not allowed to widen V2 claims.",
        audience_segment="Support leaders",
    )
    artifacts = KnowledgeArtifacts(
        business=BusinessProfile(company_name="RelayDesk", what_it_does="Support automation"),
        evidence=EvidenceLedger(
            entries=[
                Evidence(
                    id="E-allowed",
                    kind=EvidenceKind.FEATURE,
                    claim="RelayDesk drafts text replies.",
                    verbatim="RelayDesk drafts text replies.",
                ),
                Evidence(
                    id="E-withheld",
                    kind=EvidenceKind.FEATURE,
                    claim="RelayDesk handles voice calls.",
                    verbatim="An old page said RelayDesk handles voice calls.",
                ),
            ]
        ),
    )
    qualification = CompanyQualification(
        classification=QualificationClass.QUALIFIED,
        audience_structure_fit=QualificationDimension.STRONG,
        product_capability_fit=QualificationDimension.STRONG,
        evidence_completeness=EvidenceCompleteness.COMPLETE,
        reachability=Reachability.REACHABLE,
        evidence=[
            CompanySignal(
                code="uses_zendesk",
                value="true",
                grounding=SignalGrounding.DIRECT,
                quote="Northstar lists Zendesk on its support page.",
            )
        ],
    )
    advice = CampaignGenerationAdvice(
        campaign_id=campaign.id,
        readiness=CampaignReadiness.GO,
        recommendation=CampaignRecommendation(
            state=RecommendationState.RECOMMENDED,
            readiness=CampaignReadiness.GO,
            allowed_claims=["RelayDesk drafts text replies."],
            allowed_evidence_ids=["E-allowed"],
            forbidden_claims=["RelayDesk handles voice calls."],
            forbidden_capability_ids=["voice_telephony"],
            forbidden_evidence_ids=["E-withheld"],
        ),
        selected_company_name="Northstar",
        selected_company_qualification=qualification,
    )
    before = (campaign.model_dump(), artifacts.model_dump(), advice.model_dump())

    context = _context_from_stored(campaign, None, artifacts, advice)

    assert context.claim_contract_enforced is True
    assert [item.id for item in context.evidence] == ["E-allowed"]
    assert [item.text for item in context.claim_contract] == ["RelayDesk drafts text replies."]
    assert context.target_company == "Northstar"
    assert context.company_evidence[0].id == "COMPANY-uses_zendesk"
    assert "V2-CAPABILITY-voice_telephony" in {item.id for item in context.forbidden_claims}
    assert (campaign.model_dump(), artifacts.model_dump(), advice.model_dump()) == before


def test_markdown_says_when_live_commercial_review_was_not_run():
    markdown = render_markdown(evaluate_deterministic(load_case("strong-grounded")))

    assert "Commercial model review was not run" in markdown
    assert "spends no model quota" in markdown
