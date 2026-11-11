"""Source-aware judgment of claims. Code checks the receipt, not the prose's meaning.

One review per distinct draft/context, with the runtime's one JSON repair at
most. No web, recursive research or writer self-approval. A missing review never
becomes an approval. The same service reviews campaign drafts and local edits.
"""

import hashlib
import json
from typing import Literal
from urllib.parse import urljoin, urlsplit

from pydantic import BaseModel, Field

from app.ai.models import ModelTier
from app.knowledge.artifacts import KnowledgeArtifacts
from app.knowledge.corpus import MARKDOWN_LINK_RE, SourceCorpus, contains_quote, fold
from app.marketing.briefs import EmailBrief
from app.marketing.email_copy import Email, render_review
from app.marketing.gates import GateIssue, GateReport, GateSeverity
from app.runtime.exceptions import OutputValidationError
from app.runtime.model_session import ModelSession

ROLE_ID = "claim_reviewer"
REVIEW_VERSION = 3
MAX_FACT_CHARS = 48_000


class Citation(BaseModel):
    source_id: str
    quote: str = Field(min_length=1)


class ClaimAssessment(BaseModel):
    text: str = Field(min_length=1, description="Exact passage from the email, including markup if present.")
    status: Literal["supported", "unsupported", "contradicted", "uncertain"]
    explanation: str = Field(min_length=1)
    citations: list[Citation] = Field(max_length=6)


class ReviewFinding(BaseModel):
    text: str = Field(min_length=1, description="Exact passage from the email.")
    kind: Literal["factual", "instruction", "editorial"]
    explanation: str = Field(min_length=1)


class BenefitRetention(BaseModel):
    status: Literal["preserved", "lost", "not_applicable"]
    explanation: str = Field(min_length=1, max_length=600)
    original_passage: str = ""
    revised_passage: str = ""


class GroundingDecision(BaseModel):
    verdict: Literal["supported", "revise", "uncertain"]
    claims: list[ClaimAssessment] = Field(max_length=32)
    findings: list[ReviewFinding] = Field(max_length=12)
    summary: str = Field(min_length=1)
    benefit_retention: BenefitRetention | None = None


class FactualRepair(BaseModel):
    """Verified fragments of a rejected draft, not approval of a new version."""

    supported_passages: list[ClaimAssessment]
    source_excerpts: dict[str, str]

    def render(self) -> str:
        return "\n".join(
            f"- {claim.text}\n  Source: "
            + " | ".join(f"[{citation.source_id}] {citation.quote}" for citation in claim.citations)
            for claim in self.supported_passages
        )


def offer_source_excerpts(
    artifacts: KnowledgeArtifacts, corpus: SourceCorpus | None, *,
    offer_id: str = "", allowed_ids: set[str] | None = None,
) -> dict[str, str]:
    """Find the captured terms around the licensed plan quote."""
    if corpus is None:
        return {}
    plans = artifacts.offer.plans
    plan_headings = {fold(plan.name) for plan in plans}
    excerpts: dict[str, str] = {}
    for plan in plans:
        if offer_id not in {"", "offering", plan.reference_id}:
            continue
        provenance = plan.provenance
        if provenance is None or (allowed_ids is not None and provenance.evidence_id not in allowed_ids):
            continue
        evidence = artifacts.evidence.get(provenance.evidence_id)
        anchor = evidence.verbatim if evidence else provenance.quote
        if not anchor.strip() or not (provenance.source or provenance.document_id):
            continue
        for index, chunk in enumerate(corpus.chunks):
            if provenance.document_id:
                same_source = chunk.document_id == provenance.document_id
            else:
                same_source = provenance.source in (chunk.source, *chunk.source_aliases)
            if not same_source or not contains_quote(anchor, chunk.content):
                continue
            prefix = f"offer:{plan.reference_id}"
            # The preceding section can state terms shared by several plans,
            # such as currency. Keep its original heading and cite it separately.
            if index:
                previous = corpus.chunks[index - 1]
                if previous.document_id == chunk.document_id and fold(previous.heading) not in plan_headings:
                    excerpts[f"{prefix}:context"] = previous.render()
            excerpts[prefix] = chunk.render()
            break
        if len(excerpts) >= 6:
            break
    return excerpts


def _review_material(
    email: Email, brief: EmailBrief, artifacts: KnowledgeArtifacts, corpus: SourceCorpus | None,
) -> tuple[list[dict], dict[str, str]]:
    selected = {*brief.evidence_ids, *brief.next_step_evidence_ids}
    eligible = [entry for entry in artifacts.evidence.entries
                if entry.id not in brief.forbidden_evidence_ids]
    eligible.sort(key=lambda entry: entry.id not in selected)
    sources: dict[str, str] = {}
    facts: list[dict] = []
    size = 0
    for entry in eligible:
        fact = entry.model_dump(mode="json")
        length = len(json.dumps(fact, ensure_ascii=False))
        if size + length > MAX_FACT_CHARS:
            continue
        facts.append(fact)
        sources[entry.id] = entry.verbatim
        size += length
    if corpus is not None:
        sources.update(proposition_source_excerpts(brief, artifacts, corpus))
        sources.update(offer_source_excerpts(
            artifacts, corpus, offer_id=brief.offer_id,
            allowed_ids=artifacts.evidence.ids - set(brief.forbidden_evidence_ids)
            if brief.forbidden_evidence_ids else None,
        ))
        for index, hit in enumerate(corpus.search(render_review(email), limit=3)):
            sources[f"source:{index}"] = hit.render()[:3000]
        sources.update(destination_excerpts(brief, artifacts, corpus))
    return facts, sources


def proposition_source_excerpts(
    brief: EmailBrief, artifacts: KnowledgeArtifacts, corpus: SourceCorpus | None,
) -> dict[str, str]:
    """Keep the original product, mechanism and next-step sources across versions."""
    if corpus is None:
        return {}
    value = brief.value_case.for_evidence(set(brief.evidence_ids) - set(brief.forbidden_evidence_ids))
    business = artifacts.business
    queries = (
        ("mechanism", f"{brief.mechanism} {value.mechanism} {brief.single_idea}", 3),
        ("benefit", value.reader_benefit or brief.single_idea, 2),
        ("product", f"{business.what_it_does} {business.category}", 2),
        ("action", f"{brief.call_to_action} {brief.next_step_value}", 2),
    )
    excerpts: dict[str, str] = {}
    seen: set[tuple[str, int]] = set()
    for label, query, limit in queries:
        for index, hit in enumerate(corpus.search(query, limit=limit)):
            key = hit.document_id, hit.index
            if key not in seen:
                seen.add(key)
                excerpts[f"proposition:{label}:{index}"] = hit.render()
    return excerpts


def _resolve_link(base: str, link: str) -> str:
    try:
        return urljoin(base, link)
    except ValueError:
        return ""


def absolute_destination(destination: str, origin: str) -> str:
    if (destination.startswith("/") and not destination.startswith("//") and "\\" not in destination
            and origin.startswith(("https://", "http://"))):
        destination = _resolve_link(origin, destination)
    if any(char.isspace() for char in destination) or "\\" in destination:
        return ""
    try:
        url = urlsplit(destination)
    except ValueError:
        return ""
    if url.scheme in {"https", "http"} and url.hostname and url.username is None:
        return destination
    return ""


def captured_destination(
    destination: str, corpus: SourceCorpus | None, *, identity_url: str,
) -> bool:
    """A destination already captured or explicitly linked by the brand."""
    if not corpus or not identity_url:
        return False

    def host(url: str) -> str:
        try:
            parts = urlsplit(url)
            if parts.scheme in {"http", "https"} and parts.username is None:
                return (parts.hostname or "").removeprefix("www.")
        except ValueError:
            pass
        return ""

    identity = host(identity_url)
    if not identity:
        return False

    def official(url: str) -> bool:
        origin = host(url)
        return origin == identity or origin.endswith("." + identity)

    if not official(destination):
        return False
    return any(
        document.source == destination or any(
            _resolve_link(document.source, match[1]) == destination
            for match in MARKDOWN_LINK_RE.finditer(document.content)
        )
        for document in corpus.documents if official(document.source)
    )


def destination_excerpts(brief: EmailBrief, artifacts: KnowledgeArtifacts, corpus: SourceCorpus) -> dict[str, str]:
    """Surface literal links to the chosen CTA without fetching the destination."""
    destination = brief.next_step_url
    if destination.startswith("/") and not destination.startswith("//"):
        # Resolve the offer's root-relative URL against its own captured page,
        # never against an unrelated document that happens to use the same path.
        action = next((item for item in artifacts.offer.calls_to_action
                       if item.reference_id == brief.action_id and item.url == destination), None)
        base = action.provenance.source if action and action.provenance else ""
        destination = _resolve_link(base, destination)
    if not destination.startswith(("https://", "http://")):
        return {}
    sources: dict[str, str] = {}
    page = next((chunk for chunk in corpus.chunks if chunk.source == destination), None)
    if page:
        sources["cta:0"] = page.render()[:3000]
    for document in corpus.documents:
        if not document.source.startswith(("https://", "http://")):
            continue
        for match in MARKDOWN_LINK_RE.finditer(document.content):
            if _resolve_link(document.source, match[1]) == destination:
                # Include the source page and resolved destination as metadata;
                # the literal markdown link is the citable excerpt.
                sources[f"cta:{len(sources)}"] = (
                    f"Source page: {document.source}\nResolved link: {destination}\n"
                    f"Literal link: {match[0]}"
                )
                break
        if len(sources) == 3:
            break
    return sources


def factual_repair(
    email: Email, brief: EmailBrief, artifacts: KnowledgeArtifacts, gates: GateReport,
    corpus: SourceCorpus | None = None,
) -> FactualRepair | None:
    receipt = gates.semantic_review
    if not receipt or receipt.get("approved") is not False or not gates.blocking:
        return None
    try:
        decision = GroundingDecision.model_validate(receipt.get("decision"))
    except ValueError:
        return None
    if not (any(claim.status != "supported" for claim in decision.claims)
            or any(finding.kind in {"factual", "instruction"} for finding in decision.findings)):
        return None
    _, sources = _review_material(email, brief, artifacts, corpus)
    text = render_review(email)
    approved = [
        claim for claim in decision.claims
        if claim.status == "supported" and claim.text in text and claim.citations
        and all(_citation_matches(citation, sources) for citation in claim.citations)
    ]
    excerpts = {
        "prior:" + citation.source_id: sources[citation.source_id]
        for claim in approved for citation in claim.citations
        if citation.source_id.startswith("source:")
    }
    return FactualRepair(supported_passages=approved, source_excerpts=excerpts) if approved else None


def _citation_matches(citation: Citation, sources: dict[str, str]) -> bool:
    quote = fold(citation.quote)
    return bool(quote) and citation.source_id in sources and quote in fold(sources[citation.source_id])


def _retention_notes(decision: GroundingDecision) -> list[GateIssue]:
    retention = decision.benefit_retention
    if retention is not None and retention.status != "lost":
        return []
    return [GateIssue(
        gate="claim-review", severity=GateSeverity.ADVISORY,
        detail=(retention.explanation if retention else
                "The rewrite's preservation of the supported reader benefit was not assessed."),
    )]


def _hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     default=str).encode()).hexdigest()


def review_key(email: Email, brief: EmailBrief, artifacts: KnowledgeArtifacts) -> str:
    # Editorial history is not a source of facts. Source/permission changes are.
    brief_data = brief.model_dump(mode="json")
    if not brief.user_request:
        brief_data.pop("user_request")
    for proposition in [brief_data, *brief_data["alternative_arguments"]]:
        if not proposition["destination_rejected"]:
            proposition.pop("destination_rejected")
    return _hash({"version": REVIEW_VERSION, "email": email.model_dump(mode="json"),
                  "brief": brief_data,
                  "knowledge": {"business": artifacts.business.model_dump(mode="json"),
                                "offer": artifacts.offer.model_dump(mode="json"),
                                "evidence": artifacts.evidence.model_dump(mode="json")}})


def reuse_review(report: GateReport, receipt: dict | None, *, email: Email,
                 brief: EmailBrief, artifacts: KnowledgeArtifacts) -> GateReport:
    """Selection/recovery may reuse only an approval of these exact words/facts."""
    key = review_key(email, brief, artifacts)
    if (not receipt or receipt.get("key") != key
            or receipt.get("approved") is not True):
        return report.extend(GateReport(issues=[GateIssue(
            gate="claim-review", detail="This version needs an AI source review for the current text and knowledge.",
        )]))
    report.semantic_review = {**receipt, "key": key, "version": REVIEW_VERSION}
    if receipt.get("factual_repair"):
        report.issues.extend(_retention_notes(GroundingDecision.model_validate(receipt["decision"])))
    return report


class ClaimReviewer:
    def __init__(self, session: ModelSession) -> None:
        self._session = session
        self._cache: dict[str, GateReport] = {}

    async def review(self, *, email: Email, brief: EmailBrief, artifacts: KnowledgeArtifacts,
                     hints: GateReport, corpus: SourceCorpus | None = None,
                     repair: FactualRepair | None = None,
                     pasted_text: str | None = None) -> GateReport:
        key = review_key(email, brief, artifacts)
        if pasted_text is not None:
            key = _hash([key, pasted_text])
        cache_key = _hash([key, repair.model_dump(mode="json")]) if repair else key
        if cache_key in self._cache:
            return self._cache[cache_key].model_copy(deep=True)
        facts, sources = _review_material(email, brief, artifacts, corpus)
        if repair:
            # The candidate's search may find different chunks. Keep the
            # literal excerpts previously checked against the original corpus.
            sources.update(repair.source_excerpts)
        text = render_review(email) if pasted_text is None else pasted_text
        # Planning suggestions are neither user instructions nor source facts.
        # Keep the selected proposition, exclusions and steering visible, and
        # let the reviewer establish the actual qualifications from citations.
        review_brief = brief.model_copy(update={
            "claim_conditions": [],
            "value_case": brief.value_case.model_copy(update={"decision_conditions": []}),
        })
        try:
            decision = await self._session.structured(
                role=ROLE_ID, tier=ModelTier.BALANCED, template="claim_reviewer", tools=[],
                variables={"email": text, "brief": review_brief.render(for_writer=True),
                           "user_request": brief.user_request,
                           "facts": json.dumps(facts, ensure_ascii=False),
                           "sources": json.dumps(sources, ensure_ascii=False),
                           "offer": artifacts.offer.model_dump_json(),
                           "business": artifacts.business.model_dump_json(),
                           "hints": hints.render(), "destination": brief.next_step_url,
                           "repair_context": repair.render() if repair else ""},
                task="Review this exact draft against the supplied sources and instructions.",
                schema=GroundingDecision,
            )
        except OutputValidationError:
            return GateReport(issues=[GateIssue(gate="claim-review",
                              detail="AI source review returned an invalid decision; this draft is not approved.")])
        issues: list[GateIssue] = []
        display_claims: list[ClaimAssessment] = []
        for claim in decision.claims:
            anchored = claim.text in text
            if not anchored:
                issues.append(GateIssue(gate="review-reference", detail="AI review cited a passage absent from this version."))
            valid_citations = [citation for citation in claim.citations if _citation_matches(citation, sources)]
            all_citations_match = len(valid_citations) == len(claim.citations)
            if not all_citations_match:
                issues.append(GateIssue(gate="review-reference", detail="AI review cited an absent source or quotation."))
            if claim.status == "supported" and not claim.citations:
                issues.append(GateIssue(gate="review-reference", detail="A factual approval has no source citation."))
            if claim.status != "supported":
                issues.append(GateIssue(gate="claim-review", detail=f'"{claim.text}": {claim.explanation}'))
            if anchored and (claim.status != "supported" or (valid_citations and all_citations_match)):
                display_claims.append(claim.model_copy(update={"citations": valid_citations}))
        display_findings: list[ReviewFinding] = []
        for finding in decision.findings:
            if finding.text not in text:
                issues.append(GateIssue(gate="review-reference", detail="AI review finding is not anchored to this version."))
            else:
                display_findings.append(finding)
            issues.append(GateIssue(gate="claim-review", detail=finding.explanation,
                          severity=GateSeverity.ADVISORY if finding.kind == "editorial" else GateSeverity.BLOCKING))
        if decision.verdict != "supported" and not any(i.severity == GateSeverity.BLOCKING for i in issues):
            issues.append(GateIssue(gate="claim-review", detail=decision.summary))
        if repair:
            retention = decision.benefit_retention
            if (retention is not None and retention.status != "not_applicable"
                    and (retention.original_passage not in {claim.text for claim in repair.supported_passages}
                         or (retention.status == "preserved"
                             and (not retention.revised_passage.strip() or retention.revised_passage not in text)))):
                decision.benefit_retention = None
            issues.extend(_retention_notes(decision))
        report = GateReport(issues=issues)
        report.semantic_review = {"key": key, "approved": report.passed,
                                  "decision": decision.model_dump(mode="json"), "version": REVIEW_VERSION}
        if repair:
            report.semantic_review["factual_repair"] = True
        if pasted_text is not None and any(issue.gate == "review-reference" for issue in issues):
            report.semantic_review["display_decision"] = decision.model_copy(update={
                "summary": "Some references could not be verified. The review below contains the passages and citations that could be matched.",
                "verdict": "uncertain",
                "claims": display_claims,
                "findings": display_findings,
            }).model_dump(mode="json")
        report.semantic_review["sources"] = {
            citation.source_id: (
                entry.source if (entry := artifacts.evidence.get(citation.source_id)) else
                sources[citation.source_id].partition("\n")[0]
            )
            for claim in display_claims for citation in claim.citations
        }
        self._cache[cache_key] = report
        return report.model_copy(deep=True)
