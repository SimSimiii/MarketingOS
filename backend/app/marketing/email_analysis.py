"""Reuse checks without imposing the generated-email envelope on a user's draft.

Absence of support is a request for evidence, never a finding that a claim is false.
Editorial checks remain advice. No writer, rewrite or web call runs here.
"""
from app.knowledge.artifacts import KnowledgeArtifacts
from app.knowledge.ledger import EvidenceIndex
from app.marketing.email_copy import Email
from app.marketing.gates import (
    clarity_gate,
    copy_review_gate,
    evidence_gate,
    placeholder_gate,
    repeated_call_to_action_gate,
    sameness_gate,
    stock_phrase_gate,
)
from app.schemas.email_analysis import AnalysisFinding, EmailAnalysisRequest, EmailAnalysisResult


def as_email(request: EmailAnalysisRequest) -> Email:
    # The pasted body includes its greeting, CTA and signature. Do not duplicate
    # these or reflow the user's text just to fit the generator's envelope.
    return Email(position=1, subject=request.subject, preview_text=request.preview_text,
                 greeting="", body=request.body, call_to_action="", sign_off="")


def analyse(request: EmailAnalysisRequest, artifacts: KnowledgeArtifacts | None) -> EmailAnalysisResult:
    email = as_email(request)
    text = f"{request.subject}\n{request.preview_text}\n{request.body}"
    findings: list[AnalysisFinding] = []
    parts = [
        (placeholder_gate(text, request.merge_fields), "verification",
         "Resolve the placeholder or declare it as an intended merge field."),
        (stock_phrase_gate(text), "editorial", "Replace the quoted phrase with a specific point."),
        (repeated_call_to_action_gate(email), "editorial", "Keep the next step clear for the stated objective."),
        (sameness_gate(email), "editorial", "Use a supported, specific detail if this advice fits the email's purpose."),
    ]
    coverage = [
        "Editorial findings are suggestions; no sendability verdict or conversion forecast is produced.",
        "The pasted text is analysed as supplied. Subjective semantic truth is not established by string matching.",
    ]
    if artifacts is not None:
        parts.extend([
            (evidence_gate(text, EvidenceIndex(artifacts.evidence)), "verification",
             "Check this passage against the source, or add the missing evidence. Missing support does not mean false."),
            (clarity_gate(email, artifacts.business), "editorial", "Name the offering where the reader can identify it."),
            (copy_review_gate(email, artifacts.evidence.entries), "editorial",
             "Review the quoted passage in context; preserve supported specificity."),
        ])
        coverage.append("Numbers, quotes and URLs are compared with the current compiled ledger and approved proof; omitted material remains unverified.")
    else:
        coverage.append("Brand knowledge is not compiled: product facts, prices and promises were not checked. Compile knowledge to check support.")
        findings.append(AnalysisFinding(category="context", check="knowledge", detail="No compiled brand knowledge available.",
                                        action="Compile the brand's sources, then analyse this draft again."))
    if not request.audience.strip():
        findings.append(AnalysisFinding(category="context", check="audience", detail="No recipient situation supplied.",
                                        action="Describe the intended reader to assess relevance without guessing."))
    if not request.objective.strip():
        findings.append(AnalysisFinding(category="context", check="objective", detail="No objective supplied.",
                                        action="State the action this email should help the reader take."))
    for report, category, action in parts:
        for issue in report.issues:
            findings.append(AnalysisFinding(category=category, check=issue.gate, detail=issue.detail, action=action))
    return EmailAnalysisResult(findings=findings, coverage=coverage, objective=request.objective,
                               knowledge_version=artifacts.version if artifacts else None,
                               forecast_calls=int(request.cold_read))
