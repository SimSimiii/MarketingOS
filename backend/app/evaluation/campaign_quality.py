"""Reusable campaign-quality checks for finished email drafts.

The deterministic pass answers whether a draft is safe to review and costs no
model calls.  The optional commercial pass is deliberately separate: it asks
configured models to read anonymous variants as fixed buyer personas, and is
only reached by callers that explicitly provide a reviewer.

Nothing in this module rewrites copy or changes campaign state.  Evaluation is
an observation over an immutable :class:`CampaignQualityCase`.
"""

from __future__ import annotations

import asyncio
import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field, computed_field

from app.ai.model_router import ModelTier
from app.knowledge.ledger import (
    Evidence,
    EvidenceIndex,
    EvidenceKind,
    EvidenceLedger,
    extract_claims,
)
from app.marketing.email_copy import Email, render_email
from app.marketing.gates import placeholder_gate, spam_gate, stock_phrase_gate, structure_gate
from app.runtime.exceptions import ModelRuntimeError
from app.runtime.model_session import ModelSession


class QualityVerdict(StrEnum):
    SAFE_TO_REVIEW = "SAFE_TO_REVIEW"
    NEEDS_REVISION = "NEEDS_REVISION"
    UNSAFE = "UNSAFE"


class FindingSeverity(StrEnum):
    BLOCKING = "blocking"
    ADVISORY = "advisory"


class FindingKind(StrEnum):
    SAFETY = "safety"
    COMMERCIAL = "commercial"


class EvidenceScope(StrEnum):
    PRODUCT = "product"
    COMPANY = "company"
    CAMPAIGN = "campaign"


class CommercialReviewStatus(StrEnum):
    NOT_RUN = "NOT_RUN"
    PASS = "PASS"
    NEEDS_REVISION = "NEEDS_REVISION"
    INCOMPLETE = "INCOMPLETE"


class EvidenceReference(BaseModel):
    """One statement a deterministic check may use as support."""

    id: str
    text: str
    scope: EvidenceScope = EvidenceScope.PRODUCT


class ForbiddenClaim(BaseModel):
    """A campaign-specific prohibition with a stable, user-visible id.

    ``patterns`` are regular expressions so a contract can cover several
    phrasings without teaching the evaluator product semantics.  If omitted,
    the significant words in ``description`` must all appear in the passage.
    """

    id: str
    description: str
    patterns: list[str] = Field(default_factory=list)


class CampaignQualityContext(BaseModel):
    product_name: str = ""
    target_audience: str = ""
    target_company: str = ""
    evidence: list[EvidenceReference] = Field(default_factory=list)
    #: The explicit boundary of claims this campaign is allowed to make.
    claim_contract: list[EvidenceReference] = Field(default_factory=list)
    #: True when an empty contract is meaningful (V2 explicitly licensed no
    #: product claims), rather than merely absent on a legacy input.
    claim_contract_enforced: bool = False
    #: Evidence about the recipient company, never about the sending product.
    company_evidence: list[EvidenceReference] = Field(default_factory=list)
    forbidden_claims: list[ForbiddenClaim] = Field(default_factory=list)
    buyer_personas: list[str] = Field(default_factory=list)


class CampaignDraft(BaseModel):
    id: str
    email: Email
    #: Per-email prohibitions, such as EmailBrief.must_not_say.
    forbidden_claims: list[ForbiddenClaim] = Field(default_factory=list)


class CampaignQualityCase(BaseModel):
    id: str
    name: str = ""
    context: CampaignQualityContext = Field(default_factory=CampaignQualityContext)
    drafts: list[CampaignDraft] = Field(min_length=1)
    source: str = "fixture"
    notes: list[str] = Field(default_factory=list)


class QualityFinding(BaseModel):
    rule_id: str
    kind: FindingKind
    severity: FindingSeverity
    message: str
    offending_text: str = ""
    location: str = ""
    #: The forbidden-rule or evidence ids involved, where one exists.
    reference_ids: list[str] = Field(default_factory=list)


class DeterministicCheck(BaseModel):
    rule_id: str
    name: str
    findings: list[QualityFinding] = Field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.findings


class ScoreEvidence(BaseModel):
    score: int = Field(ge=1, le=5)
    evidence: str = Field(description="A concise reference to words in the draft.")


class CommercialRubric(BaseModel):
    specificity_to_audience_company: ScoreEvidence
    relevance_of_problem: ScoreEvidence
    credibility_trust: ScoreEvidence
    value_clarity: ScoreEvidence
    differentiation: ScoreEvidence
    readability_flow: ScoreEvidence
    cta_quality: ScoreEvidence
    likely_reply_interest: ScoreEvidence
    spamminess_generic_ai_tone: ScoreEvidence = Field(
        description="1 is spammy/generic-AI; 5 is natural and credible."
    )

    @computed_field
    @property
    def average_score(self) -> float:
        scores = [getattr(self, name).score for name in _RUBRIC_FIELDS]
        return round(sum(scores) / len(scores), 2)


class CommercialDraftReview(BaseModel):
    draft_id: str
    blind_label: str
    rubric: CommercialRubric


class PersonaCommercialReview(BaseModel):
    persona: str
    drafts: list[CommercialDraftReview] = Field(default_factory=list)
    winner_draft_id: str = ""
    winner_blind_label: str = ""
    comparison_evidence: str = ""
    reported: bool = True
    error: str = ""


class CommercialReviewReport(BaseModel):
    blind: bool = True
    model_calls: int = 0
    personas: list[PersonaCommercialReview] = Field(default_factory=list)

    @property
    def reported(self) -> list[PersonaCommercialReview]:
        return [review for review in self.personas if review.reported]


class DraftQualityResult(BaseModel):
    draft_id: str
    position: int
    checks: list[DeterministicCheck] = Field(default_factory=list)

    @computed_field
    @property
    def findings(self) -> list[QualityFinding]:
        return [finding for check in self.checks for finding in check.findings]

    @computed_field
    @property
    def evidentially_safe(self) -> bool:
        return not any(
            finding.kind is FindingKind.SAFETY and finding.severity is FindingSeverity.BLOCKING
            for finding in self.findings
        )


class CampaignQualityReport(BaseModel):
    campaign_id: str
    campaign_name: str = ""
    source: str = ""
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    live: bool = False
    verdict: QualityVerdict
    evidentially_safe: bool
    commercial_review_status: CommercialReviewStatus
    drafts: list[DraftQualityResult] = Field(default_factory=list)
    commercial_review: CommercialReviewReport | None = None
    revision_priorities: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class _BlindDraftReview(BaseModel):
    label: str = Field(description="The anonymous draft label exactly as supplied.")
    rubric: CommercialRubric


class _BlindPersonaResponse(BaseModel):
    drafts: list[_BlindDraftReview]
    winner: str = Field(description="The winning anonymous label, or TIE.")
    comparison_evidence: str


_RUBRIC_FIELDS = (
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


class CommercialReviewer:
    """Optional, quota-spending commercial review over anonymous drafts."""

    ROLE_ID = "campaign_quality_reviewer"

    def __init__(self, session: ModelSession) -> None:
        self._session = session

    async def review(self, case: CampaignQualityCase) -> CommercialReviewReport:
        personas = case.context.buyer_personas or [
            case.context.target_audience or "a busy professional who has never heard of the sender"
        ]
        reviews = await asyncio.gather(
            *(
                self._review_as(case, persona, persona_index)
                for persona_index, persona in enumerate(personas)
            )
        )
        return CommercialReviewReport(
            model_calls=len(self._session.usage.calls), personas=list(reviews)
        )

    async def _review_as(
        self, case: CampaignQualityCase, persona: str, persona_index: int
    ) -> PersonaCommercialReview:
        assignments = _blind_assignments(case.drafts, persona_index)
        label_to_id = {label: draft.id for label, draft in assignments}
        listing = "\n\n".join(
            f"DRAFT {label}\n{render_email(draft.email)}" for label, draft in assignments
        )
        campaign_context = (
            "\n".join(
                part
                for part in (
                    f"Product: {case.context.product_name}" if case.context.product_name else "",
                    (
                        f"Intended audience: {case.context.target_audience}"
                        if case.context.target_audience
                        else ""
                    ),
                    (
                        f"Target company: {case.context.target_company}"
                        if case.context.target_company
                        else ""
                    ),
                )
                if part
            )
            or "No context beyond the fixed buyer persona."
        )
        system_prompt = self._session.render(
            "campaign_quality_review",
            {
                "buyer_persona": persona,
                "campaign_context": campaign_context,
                "drafts": listing,
            },
        )
        try:
            response = await self._session.structured(
                role=self.ROLE_ID,
                tier=ModelTier.BALANCED,
                system_prompt=system_prompt,
                task=(
                    "Score every anonymous draft once. Compare only the drafts shown and "
                    "return the anonymous winning label, or TIE."
                ),
                schema=_BlindPersonaResponse,
            )
        except ModelRuntimeError as exc:
            return PersonaCommercialReview(
                persona=persona, reported=False, error=f"the model review failed: {exc}"
            )

        seen: set[str] = set()
        drafts: list[CommercialDraftReview] = []
        for scored in response.drafts:
            label = scored.label.strip().upper().removeprefix("DRAFT ")
            if label not in label_to_id or label in seen:
                continue
            seen.add(label)
            drafts.append(
                CommercialDraftReview(
                    draft_id=label_to_id[label], blind_label=label, rubric=scored.rubric
                )
            )
        if len(drafts) != len(assignments):
            return PersonaCommercialReview(
                persona=persona,
                reported=False,
                error="the model did not return one rubric for every anonymous draft",
            )

        winner = response.winner.strip().upper().removeprefix("DRAFT ")
        winner_id = label_to_id.get(winner, "") if winner != "TIE" else ""
        return PersonaCommercialReview(
            persona=persona,
            drafts=drafts,
            winner_draft_id=winner_id,
            winner_blind_label=winner if winner in label_to_id or winner == "TIE" else "",
            comparison_evidence=response.comparison_evidence,
        )


@dataclass(frozen=True)
class _RiskRule:
    id: str
    label: str
    patterns: tuple[re.Pattern[str], ...]


# These are assertion shapes with unusually high downside.  They are not a
# blacklist of words: a matching assertion passes when supplied evidence or
# the explicit claim contract contains the same capability.
_RISK_RULES = (
    _RiskRule(
        "RISK-VOICE-TELEPHONY",
        "voice or telephony support",
        (
            re.compile(
                r"\b(?:support|offer|provide)s?\s+(?:inbound\s+|outbound\s+)?"
                r"(?:voice|phone|telephony)(?:\s+(?:calls?|calling|support|agents?|automation))?\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:make|take|handle|answer|place|route|transcribe)s?\s+"
                r"(?:inbound\s+|outbound\s+)?(?:voice\s+|phone\s+)?calls?\b",
                re.IGNORECASE,
            ),
        ),
    ),
    _RiskRule(
        "RISK-HIPAA",
        "HIPAA compliance",
        (re.compile(r"\bHIPAA(?:[- ](?:compliant|certified|ready))?\b", re.IGNORECASE),),
    ),
    _RiskRule(
        "RISK-FULL-BACKEND",
        "full backend replacement",
        (
            re.compile(
                r"\b(?:replace|eliminate|remove|retire)s?\s+(?:your|the|their)?\s*"
                r"(?:entire|full|whole)?\s*back[\s-]?end\b",
                re.IGNORECASE,
            ),
            re.compile(r"\bno\s+(?:more\s+)?back[\s-]?end\b", re.IGNORECASE),
        ),
    ),
)

_ARCHITECTURE_TERMS = (
    "AWS",
    "Azure",
    "GCP",
    "Kubernetes",
    "microservice",
    "microservices",
    "monolith",
    "Postgres",
    "MongoDB",
    "Snowflake",
    "Salesforce",
    "HubSpot",
    "Zendesk",
    "Intercom",
    "data warehouse",
    "tech stack",
    "architecture",
    "backend",
    "back-end",
)

_PASSAGE_SPLIT_RE = re.compile(r"(?<=[.!?])[\"'”’)\]]*\s+|\n\s*\n")
_WORD_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = frozenset(
    {
        "about",
        "after",
        "again",
        "also",
        "and",
        "are",
        "because",
        "before",
        "been",
        "being",
        "but",
        "can",
        "company",
        "does",
        "every",
        "for",
        "from",
        "have",
        "into",
        "its",
        "more",
        "our",
        "product",
        "that",
        "the",
        "their",
        "them",
        "then",
        "there",
        "these",
        "they",
        "this",
        "tool",
        "uses",
        "using",
        "was",
        "were",
        "what",
        "when",
        "which",
        "with",
        "would",
        "you",
        "your",
    }
)
_NEGATION_RE = re.compile(
    r"\b(?:not|never|cannot|can't|don't|do not|doesn't|does not|without)\b", re.IGNORECASE
)
_WEAK_CTAS = frozenset(
    {
        "click here",
        "get started",
        "interested",
        "interested?",
        "learn more",
        "let me know",
        "read more",
        "thoughts",
        "thoughts?",
    }
)
_CTA_VERBS = frozenset(
    {
        "book",
        "check",
        "compare",
        "inspect",
        "open",
        "read",
        "reply",
        "review",
        "run",
        "schedule",
        "see",
        "show",
        "start",
        "try",
        "view",
        "watch",
    }
)


def evaluate_deterministic(case: CampaignQualityCase) -> CampaignQualityReport:
    """Run every zero-cost rule and return a complete, serializable report."""

    drafts = [
        DraftQualityResult(
            draft_id=draft.id,
            position=draft.email.position,
            checks=_checks_for(draft, case.context),
        )
        for draft in case.drafts
    ]
    safe = all(draft.evidentially_safe for draft in drafts)
    has_commercial_findings = any(
        finding.kind is FindingKind.COMMERCIAL for draft in drafts for finding in draft.findings
    )
    status = (
        CommercialReviewStatus.NEEDS_REVISION
        if has_commercial_findings
        else CommercialReviewStatus.NOT_RUN
    )
    verdict = (
        QualityVerdict.UNSAFE
        if not safe
        else QualityVerdict.NEEDS_REVISION
        if has_commercial_findings
        else QualityVerdict.SAFE_TO_REVIEW
    )
    report = CampaignQualityReport(
        campaign_id=case.id,
        campaign_name=case.name,
        source=case.source,
        verdict=verdict,
        evidentially_safe=safe,
        commercial_review_status=status,
        drafts=drafts,
        notes=list(case.notes),
    )
    report.revision_priorities = _revision_priorities(report)
    return report


async def evaluate_campaign(
    case: CampaignQualityCase, reviewer: CommercialReviewer | None = None
) -> CampaignQualityReport:
    """Evaluate deterministically, then optionally spend quota on the rubric."""

    report = evaluate_deterministic(case)
    if reviewer is None:
        return report

    commercial = await reviewer.review(case)
    report.live = True
    report.commercial_review = commercial
    if len(commercial.reported) != len(commercial.personas):
        report.commercial_review_status = CommercialReviewStatus.INCOMPLETE
    elif _commercial_needs_revision(commercial):
        report.commercial_review_status = CommercialReviewStatus.NEEDS_REVISION
    else:
        report.commercial_review_status = CommercialReviewStatus.PASS

    if not report.evidentially_safe:
        report.verdict = QualityVerdict.UNSAFE
    elif report.commercial_review_status is CommercialReviewStatus.NEEDS_REVISION or any(
        finding.kind is FindingKind.COMMERCIAL
        for draft in report.drafts
        for finding in draft.findings
    ):
        report.verdict = QualityVerdict.NEEDS_REVISION
    else:
        report.verdict = QualityVerdict.SAFE_TO_REVIEW
    report.revision_priorities = _revision_priorities(report)
    return report


def _checks_for(draft: CampaignDraft, context: CampaignQualityContext) -> list[DeterministicCheck]:
    return [
        _forbidden_check(draft, context),
        _risky_claim_check(draft.email, context),
        _target_claim_check(draft.email, context),
        _claim_contract_check(draft.email, context),
        _numerical_claim_check(draft.email, context),
        _cta_check(draft.email),
        _consistency_check(draft.email),
        _claim_density_check(draft.email, context),
        _repeated_fact_check(draft.email, context),
        _baseline_check(draft.email),
    ]


def _forbidden_check(draft: CampaignDraft, context: CampaignQualityContext) -> DeterministicCheck:
    findings: list[QualityFinding] = []
    for rule in [*context.forbidden_claims, *draft.forbidden_claims]:
        for location, passage in _passages(draft.email):
            if not _matches_forbidden(rule, passage):
                continue
            findings.append(
                _finding(
                    "CQ-SAF-001",
                    FindingKind.SAFETY,
                    FindingSeverity.BLOCKING,
                    f"The draft uses a forbidden capability or claim: {rule.description}.",
                    passage,
                    location,
                    [rule.id],
                )
            )
    return DeterministicCheck(
        rule_id="CQ-SAF-001", name="Forbidden capabilities and claims", findings=_dedupe(findings)
    )


def _risky_claim_check(email: Email, context: CampaignQualityContext) -> DeterministicCheck:
    findings: list[QualityFinding] = []
    product_support = [*context.evidence, *context.claim_contract]
    company_support = [
        *context.company_evidence,
        *(item for item in context.evidence if item.scope is EvidenceScope.COMPANY),
    ]
    rules = [*_RISK_RULES, _architecture_rule(context)]
    for location, passage in _passages(email):
        for rule in rules:
            matches = [match for pattern in rule.patterns for match in pattern.finditer(passage)]
            if not matches or not any(_affirmed(passage, match.span()) for match in matches):
                continue
            ids = _risk_support_ids(
                rule,
                company_support if rule.id == "RISK-COMPANY-ARCHITECTURE" else product_support,
            )
            if ids:
                continue
            findings.append(
                _finding(
                    "CQ-SAF-002",
                    FindingKind.SAFETY,
                    FindingSeverity.BLOCKING,
                    f"Unsupported high-risk claim: {rule.label}; no supplied evidence licenses it.",
                    passage,
                    location,
                    [rule.id],
                )
            )
    return DeterministicCheck(
        rule_id="CQ-SAF-002", name="Unsupported high-risk claims", findings=_dedupe(findings)
    )


def _target_claim_check(email: Email, context: CampaignQualityContext) -> DeterministicCheck:
    company_evidence = [
        *context.company_evidence,
        *(item for item in context.evidence if item.scope is EvidenceScope.COMPANY),
    ]
    findings: list[QualityFinding] = []
    for location, passage in _passages(email):
        if not _looks_target_specific(passage, context.target_company):
            continue
        ids = _supporting_ids(passage, company_evidence)
        if ids:
            continue
        findings.append(
            _finding(
                "CQ-SAF-003",
                FindingKind.SAFETY,
                FindingSeverity.BLOCKING,
                "This states an internal fact about the recipient that is not grounded in "
                "supplied company evidence.",
                passage,
                location,
                [],
            )
        )
    return DeterministicCheck(
        rule_id="CQ-SAF-003", name="Target-company grounding", findings=_dedupe(findings)
    )


def _claim_contract_check(email: Email, context: CampaignQualityContext) -> DeterministicCheck:
    # No explicit contract means there is no deterministic semantic boundary
    # to enforce.  Numerical and high-risk claims are still checked elsewhere.
    if not context.claim_contract and not context.claim_contract_enforced:
        return DeterministicCheck(rule_id="CQ-SAF-004", name="Campaign-safe claim contract")

    allowed = [
        *context.claim_contract,
        *(item for item in context.evidence if item.scope is not EvidenceScope.COMPANY),
    ]
    findings: list[QualityFinding] = []
    for location, passage in _passages(email):
        if not _looks_like_product_claim(passage, context.product_name):
            continue
        ids = _supporting_ids(passage, allowed)
        if ids:
            continue
        findings.append(
            _finding(
                "CQ-SAF-004",
                FindingKind.SAFETY,
                FindingSeverity.BLOCKING,
                "This product claim falls outside the supplied campaign-safe claim contract.",
                passage,
                location,
                [],
            )
        )
    return DeterministicCheck(
        rule_id="CQ-SAF-004", name="Campaign-safe claim contract", findings=_dedupe(findings)
    )


def _numerical_claim_check(email: Email, context: CampaignQualityContext) -> DeterministicCheck:
    references = [
        *context.evidence,
        *context.claim_contract,
        *context.company_evidence,
    ]
    ledger = EvidenceLedger(
        entries=[
            Evidence(
                id=reference.id,
                kind=EvidenceKind.FEATURE,
                claim=reference.text,
                verbatim=reference.text,
            )
            for reference in _unique_references(references)
        ]
    )
    index = EvidenceIndex(ledger)
    findings: list[QualityFinding] = []
    passages = _passages(email)
    for unsupported in index.unsupported(render_email(email)):
        location, _ = _passage_containing(passages, unsupported.claim.text)
        findings.append(
            _finding(
                "CQ-SAF-005",
                FindingKind.SAFETY,
                FindingSeverity.BLOCKING,
                unsupported.reason,
                unsupported.claim.text,
                location,
                [],
            )
        )
    return DeterministicCheck(
        rule_id="CQ-SAF-005",
        name="Unsupported numerical claims, quotes, and URLs",
        findings=findings,
    )


def _cta_check(email: Email) -> DeterministicCheck:
    raw = " ".join(email.call_to_action.split())
    normalized = raw.lower().rstrip(" .!?")
    finding: QualityFinding | None = None
    if not normalized:
        finding = _finding(
            "CQ-COM-001",
            FindingKind.COMMERCIAL,
            FindingSeverity.ADVISORY,
            "The draft has no call to action.",
            raw,
            "call_to_action",
        )
    elif normalized in _WEAK_CTAS:
        finding = _finding(
            "CQ-COM-001",
            FindingKind.COMMERCIAL,
            FindingSeverity.ADVISORY,
            "The call to action is generic and does not make the next step concrete.",
            raw,
            "call_to_action",
        )
    else:
        words = set(_WORD_RE.findall(normalized))
        if not words & _CTA_VERBS:
            finding = _finding(
                "CQ-COM-001",
                FindingKind.COMMERCIAL,
                FindingSeverity.ADVISORY,
                "The call to action lacks a clear action verb or outcome.",
                raw,
                "call_to_action",
            )
    return DeterministicCheck(
        rule_id="CQ-COM-001",
        name="Call to action",
        findings=[finding] if finding else [],
    )


def _consistency_check(email: Email) -> DeterministicCheck:
    fields = [
        ("subject", email.subject),
        ("preview_text", email.preview_text),
        ("body", email.body),
    ]
    findings: list[QualityFinding] = []

    # A header that promises "no setup" and a body that requires setup is a
    # contradiction even when both statements contain no checkable figure.
    for source_location, source in fields[:2]:
        for negative in re.finditer(
            r"\b(?:no|without|zero)\s+([a-z][a-z-]*(?:\s+[a-z][a-z-]*){0,2})",
            source,
            re.IGNORECASE,
        ):
            anchors = _significant(negative.group(1)) - {"required", "needed", "more"}
            if not anchors:
                continue
            for body_passage in _split_passages(email.body):
                body_words = _significant(body_passage)
                if not anchors & body_words or _NEGATION_RE.search(body_passage):
                    continue
                if re.search(
                    r"\b(?:require|requires|required|need|needs|takes|involves|uses)\b",
                    body_passage,
                    re.IGNORECASE,
                ):
                    findings.append(
                        _finding(
                            "CQ-COM-002",
                            FindingKind.COMMERCIAL,
                            FindingSeverity.ADVISORY,
                            "The header and body make contradictory claims about the same condition.",
                            f"{source_location}: {source} | body: {body_passage}",
                            f"{source_location}/body",
                        )
                    )

    # Conflicting values with the same unit and a shared topic are also hard,
    # deterministic contradictions (for example 5-minute vs 20-minute setup).
    header_claims = [
        (location, text, claim) for location, text in fields[:2] for claim in extract_claims(text)
    ]
    for location, text, header_claim in header_claims:
        for body_passage in _split_passages(email.body):
            for body_claim in extract_claims(body_passage):
                if header_claim.kind is not body_claim.kind:
                    continue
                if _claim_unit(header_claim.normalized) != _claim_unit(body_claim.normalized):
                    continue
                if header_claim.normalized == body_claim.normalized:
                    continue
                if not (_significant(text) & _significant(body_passage)):
                    continue
                findings.append(
                    _finding(
                        "CQ-COM-002",
                        FindingKind.COMMERCIAL,
                        FindingSeverity.ADVISORY,
                        "The header and body give different values for the same claim.",
                        f"{location}: {text} | body: {body_passage}",
                        f"{location}/body",
                    )
                )
    return DeterministicCheck(
        rule_id="CQ-COM-002",
        name="Subject, preview, and body consistency",
        findings=_dedupe(findings),
    )


def _claim_density_check(email: Email, context: CampaignQualityContext) -> DeterministicCheck:
    passages = _split_passages(email.body)
    claimed = [
        passage
        for passage in passages
        if _looks_like_product_claim(passage, context.product_name) or extract_claims(passage)
    ]
    excessive = len(claimed) >= 6 or (
        len(passages) >= 4 and len(claimed) >= 4 and len(claimed) / len(passages) >= 0.65
    )
    findings = (
        [
            _finding(
                "CQ-COM-003",
                FindingKind.COMMERCIAL,
                FindingSeverity.ADVISORY,
                f"{len(claimed)} of {len(passages)} body sentences make product or numerical "
                "claims; the email reads like a compressed product page.",
                " | ".join(claimed[:3]),
                "body",
            )
        ]
        if excessive
        else []
    )
    return DeterministicCheck(rule_id="CQ-COM-003", name="Claim density", findings=findings)


def _repeated_fact_check(email: Email, context: CampaignQualityContext) -> DeterministicCheck:
    passages = _split_passages(email.body)
    references = [*context.claim_contract, *context.evidence]
    findings: list[QualityFinding] = []
    for reference in _unique_references(references):
        carrying = [passage for passage in passages if _strong_support(passage, reference.text)]
        if len(carrying) < 2:
            continue
        findings.append(
            _finding(
                "CQ-COM-004",
                FindingKind.COMMERCIAL,
                FindingSeverity.ADVISORY,
                "The same product fact is repeated instead of advancing the argument.",
                " | ".join(carrying[:3]),
                "body",
                [reference.id],
            )
        )

    # Exact quantitative repetition remains visible even when the evidence
    # statement is broader than either sentence.
    by_claim: dict[str, list[str]] = {}
    for passage in passages:
        for claim in extract_claims(passage):
            by_claim.setdefault(claim.normalized, []).append(passage)
    for claim, carrying in by_claim.items():
        if len(carrying) < 2:
            continue
        ids = [
            reference.id
            for reference in references
            if claim in {item.normalized for item in extract_claims(reference.text)}
        ]
        findings.append(
            _finding(
                "CQ-COM-004",
                FindingKind.COMMERCIAL,
                FindingSeverity.ADVISORY,
                f'The checkable value "{claim}" is repeated in the body.',
                " | ".join(carrying[:3]),
                "body",
                ids,
            )
        )
    return DeterministicCheck(
        rule_id="CQ-COM-004", name="Repeated product facts", findings=_dedupe(findings)
    )


def _baseline_check(email: Email) -> DeterministicCheck:
    text = render_email(email)
    reports = (
        placeholder_gate(text),
        stock_phrase_gate(text),
        spam_gate(email),
        structure_gate(email),
    )
    findings = [
        _finding(
            "CQ-COM-005",
            FindingKind.COMMERCIAL,
            FindingSeverity.ADVISORY,
            issue.detail,
            _quoted_excerpt(issue.detail),
            issue.gate,
            [f"gate:{issue.gate}"],
        )
        for report in reports
        for issue in report.issues
    ]
    return DeterministicCheck(
        rule_id="CQ-COM-005",
        name="Established sendability and readability gates",
        findings=findings,
    )


def _commercial_needs_revision(report: CommercialReviewReport) -> bool:
    return any(
        review.rubric.average_score < 3.5
        or any(getattr(review.rubric, field).score <= 2 for field in _RUBRIC_FIELDS)
        for persona in report.reported
        for review in persona.drafts
    )


def _revision_priorities(report: CampaignQualityReport) -> list[str]:
    ordered_rules = (
        ("CQ-SAF-001", "Remove forbidden capabilities or claims."),
        ("CQ-SAF-002", "Remove or substantiate high-risk product claims."),
        ("CQ-SAF-003", "Remove invented recipient-company details or attach company evidence."),
        ("CQ-SAF-004", "Bring every product assertion inside the campaign-safe claim contract."),
        ("CQ-SAF-005", "Remove unsupported figures, quotations, and URLs."),
        ("CQ-COM-002", "Make the subject, preview, and body tell one consistent story."),
        ("CQ-COM-001", "Replace the CTA with one concrete, low-friction next step."),
        ("CQ-COM-003", "Cut secondary claims and keep one commercial argument."),
        ("CQ-COM-004", "State each product fact once and use the space to advance the argument."),
        ("CQ-COM-005", "Resolve the established sendability and readability findings."),
    )
    present = {finding.rule_id for draft in report.drafts for finding in draft.findings}
    priorities = [message for rule, message in ordered_rules if rule in present]

    if report.commercial_review is not None:
        low_fields: set[str] = set()
        for persona in report.commercial_review.reported:
            for draft in persona.drafts:
                for field in _RUBRIC_FIELDS:
                    if getattr(draft.rubric, field).score <= 2:
                        low_fields.add(field)
        for field in _RUBRIC_FIELDS:
            if field in low_fields:
                priorities.append(f"Improve live-rubric weakness: {field.replace('_', ' ')}.")
    return priorities[:8]


def _blind_assignments(
    drafts: list[CampaignDraft], persona_index: int
) -> list[tuple[str, CampaignDraft]]:
    """Stable anonymous labels, rotated between personas to reduce order bias."""

    ordered = sorted(
        drafts,
        key=lambda draft: (
            hashlib.sha256(render_email(draft.email).encode("utf-8")).hexdigest(),
            draft.id,
        ),
    )
    if ordered:
        offset = persona_index % len(ordered)
        ordered = [*ordered[offset:], *ordered[:offset]]
    return [(chr(ord("A") + index), draft) for index, draft in enumerate(ordered)]


def _architecture_rule(context: CampaignQualityContext) -> _RiskRule:
    subjects = [r"you", r"your\s+(?:company|team|engineers?|developers?)"]
    if context.target_company:
        subjects.append(re.escape(context.target_company))
    subject = "(?:" + "|".join(subjects) + ")"
    terms = "(?:" + "|".join(re.escape(term) for term in _ARCHITECTURE_TERMS) + ")"
    return _RiskRule(
        "RISK-COMPANY-ARCHITECTURE",
        "unverified company architecture",
        (
            re.compile(
                rf"\b{subject}\b.{{0,70}}\b(?:run|runs|use|uses|rely|relies|have|has|built|"
                rf"deploy|host|operate)\b.{{0,70}}\b{terms}\b",
                re.IGNORECASE,
            ),
        ),
    )


def _risk_support_ids(rule: _RiskRule, references: list[EvidenceReference]) -> list[str]:
    found: list[str] = []
    for reference in references:
        matches = [match for pattern in rule.patterns for match in pattern.finditer(reference.text)]
        if matches and any(_affirmed(reference.text, match.span()) for match in matches):
            found.append(reference.id)
    return found


def _matches_forbidden(rule: ForbiddenClaim, passage: str) -> bool:
    if rule.patterns:
        for raw in rule.patterns:
            match = re.search(raw, passage, re.IGNORECASE)
            if match is not None and _affirmed(passage, match.span()):
                return True
        return False
    wanted = _significant(rule.description)
    return bool(wanted) and wanted <= _significant(passage) and not _NEGATION_RE.search(passage)


def _affirmed(text: str, span: tuple[int, int]) -> bool:
    prefix = text[max(0, span[0] - 35) : span[0]]
    return _NEGATION_RE.search(prefix) is None


def _looks_target_specific(passage: str, target_company: str) -> bool:
    if (
        target_company
        and re.search(re.escape(target_company), passage, re.IGNORECASE)
        and re.search(
            r"\b(?:has|have|is|are|runs?|uses?|relies?|spends?|loses?|struggles?|handles?|built|deploys?)\b",
            passage,
            re.IGNORECASE,
        )
    ):
        return True
    return bool(
        re.search(
            r"\b(?:your\s+(?:company|team|engineers?|developers?|support\s+team|sales\s+team|"
            r"current\s+(?:stack|workflow|system|process))|you)\s+"
            r"(?:has|have|is|are|runs?|uses?|relies?|spends?|loses?|struggles?|handles?|built|deploys?)\b",
            passage,
            re.IGNORECASE,
        )
    )


def _looks_like_product_claim(passage: str, product_name: str) -> bool:
    # Bare ``it`` is intentionally excluded. In real copy it usually refers
    # to the reader's release, note, or process; treating every ``it is`` as a
    # product assertion makes an explicit contract unusably noisy.
    subjects = [r"we", r"our\s+(?:product|platform|tool|service)", r"you\s+can"]
    if product_name:
        subjects.append(re.escape(product_name))
    subject = "(?:" + "|".join(subjects) + ")"
    return bool(
        re.search(
            rf"\b{subject}\b\s+(?:can\s+|will\s+)?(?:lets?|helps?|supports?|replaces?|"
            r"integrates?|automates?|generates?|creates?|deploys?|handles?|turns?|provides?|keeps?|"
            r"drafts?|writes?|sends?|works?|is|are)\b",
            passage,
            re.IGNORECASE,
        )
    )


def _supporting_ids(passage: str, references: list[EvidenceReference]) -> list[str]:
    return [reference.id for reference in references if _supports(passage, reference.text)]


def _supports(claim: str, support: str) -> bool:
    claim_flat = _flat(claim)
    support_flat = _flat(support)
    if len(claim_flat) >= 12 and (claim_flat in support_flat or support_flat in claim_flat):
        return True
    claim_words = _significant(claim)
    support_words = _significant(support)
    overlap = claim_words & support_words
    if not claim_words or not support_words or len(overlap) < min(2, len(support_words)):
        return False
    return len(overlap) / len(support_words) >= 0.5 and len(overlap) / len(claim_words) >= 0.25


def _strong_support(claim: str, support: str) -> bool:
    claim_values = {item.normalized for item in extract_claims(claim)}
    support_values = {item.normalized for item in extract_claims(support)}
    if claim_values & support_values:
        return True
    claim_words = _significant(claim)
    support_words = _significant(support)
    overlap = claim_words & support_words
    return len(overlap) >= 3 and bool(support_words) and len(overlap) / len(support_words) >= 0.8


def _passages(email: Email) -> list[tuple[str, str]]:
    passages: list[tuple[str, str]] = []
    for location, text in (
        ("subject", email.subject),
        ("preview_text", email.preview_text),
        ("headline", email.headline),
    ):
        if text.strip():
            passages.append((location, text.strip()))
    passages.extend(("body", passage) for passage in _split_passages(email.body))
    for location, text in (
        ("call_to_action", email.call_to_action),
        ("postscript", email.postscript),
    ):
        if text.strip():
            passages.append((location, text.strip()))
    return passages


def _split_passages(text: str) -> list[str]:
    return [piece.strip() for piece in _PASSAGE_SPLIT_RE.split(text) if piece.strip()]


def _passage_containing(passages: list[tuple[str, str]], needle: str) -> tuple[str, str]:
    lowered = needle.lower()
    return next(
        ((location, passage) for location, passage in passages if lowered in passage.lower()),
        ("", needle),
    )


def _significant(text: str) -> set[str]:
    return {
        word for word in _WORD_RE.findall(text.lower()) if len(word) > 2 and word not in _STOPWORDS
    }


def _flat(text: str) -> str:
    return " ".join(_WORD_RE.findall(text.lower()))


def _claim_unit(normalized: str) -> str:
    return re.sub(r"^[\$€£]?\d+(?:\.\d+)?\s*", "", normalized)


def _quoted_excerpt(detail: str) -> str:
    match = re.search(r"['\"]([^'\"]+)['\"]", detail)
    return match.group(1) if match else ""


def _unique_references(references: list[EvidenceReference]) -> list[EvidenceReference]:
    seen: set[str] = set()
    unique: list[EvidenceReference] = []
    for reference in references:
        if reference.id in seen:
            continue
        seen.add(reference.id)
        unique.append(reference)
    return unique


def _finding(
    rule_id: str,
    kind: FindingKind,
    severity: FindingSeverity,
    message: str,
    offending_text: str = "",
    location: str = "",
    reference_ids: list[str] | None = None,
) -> QualityFinding:
    return QualityFinding(
        rule_id=rule_id,
        kind=kind,
        severity=severity,
        message=message,
        offending_text=offending_text,
        location=location,
        reference_ids=reference_ids or [],
    )


def _dedupe(findings: list[QualityFinding]) -> list[QualityFinding]:
    unique: list[QualityFinding] = []
    seen: set[tuple[str, str, str, tuple[str, ...]]] = set()
    for finding in findings:
        key = (
            finding.rule_id,
            finding.location,
            finding.offending_text,
            tuple(finding.reference_ids),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(finding)
    return unique
