"""Verified Product x Audience x Market relevance, without campaign strategy.

The model proposes a compact dossier from three persisted inputs.  This module
is the trust boundary after that call: every product and audience reference is
resolved against the exact input snapshots, verdict mechanics are enforced in
code, and only the normalized result can be persisted.

There is deliberately no web access here and no second role.  Ranking, fit,
objections and silences are different views of the same bounded judgment.
"""

import json
import re
from collections.abc import Iterable
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field

from app.ai.model_router import ModelTier
from app.knowledge.artifacts import Grounding, KnowledgeArtifacts, Objection
from app.knowledge.ledger import (
    Evidence,
    EvidenceIndex,
    EvidenceKind,
    EvidenceLedger,
    category_of,
    value_of,
)
from app.market.audience_research import AudienceResearch
from app.market.capabilities import (
    CapabilityState,
    ClaimVisibility,
    ProductCapabilityProfile,
)
from app.market.positioning import PositioningMap, Territory, axis_for_evidence
from app.market.qualification import CompanyQualification, QualificationClass
from app.runtime.model_session import ModelSession

ROLE_ID = "relevance_analyst"
MAX_RANKED_EVIDENCE = 30


class RelevanceBand(StrEnum):
    LEAD = "LEAD"
    SUPPORT = "SUPPORT"
    CONTEXT = "CONTEXT"
    WITHHOLD = "WITHHOLD"


class FitVerdict(StrEnum):
    SOLVED = "SOLVED"
    ADDRESSED = "ADDRESSED"
    PARTIAL = "PARTIAL"
    UNSUPPORTED = "UNSUPPORTED"
    IMMATERIAL = "IMMATERIAL"
    OFF_LIMITS = "OFF_LIMITS"


class RankedRelevanceProposal(BaseModel):
    evidence_id: str
    band: RelevanceBand
    why: str
    problem_ids: list[str] = Field(default_factory=list)


class ProblemFitProposal(BaseModel):
    problem_id: str
    verdict: FitVerdict
    evidence_ids: list[str] = Field(default_factory=list)
    capability_ids: list[str] = Field(default_factory=list)
    blocked_by: list[str] = Field(default_factory=list)
    caveat: str = ""
    why: str = ""
    materiality_basis: str = ""


class ObjectionProposal(BaseModel):
    objection: str
    severity: str = "strong"
    answer: str = ""
    evidence_ids: list[str] = Field(default_factory=list)


class SilenceProposal(BaseModel):
    problem_id: str
    reason: str
    question: str = ""


class RelevanceProposal(BaseModel):
    """The model's untrusted structured answer."""

    orientation: str = ""
    ranked_relevance: list[RankedRelevanceProposal] = Field(default_factory=list)
    problem_fits: list[ProblemFitProposal] = Field(default_factory=list)
    segment_objections: list[ObjectionProposal] = Field(default_factory=list)
    silences: list[SilenceProposal] = Field(default_factory=list)


class RankedRelevanceItem(BaseModel):
    evidence_id: str
    band: RelevanceBand
    why: str
    problem_ids: list[str] = Field(default_factory=list)
    territory: Territory | None = None


class ProblemFit(BaseModel):
    problem_id: str
    verdict: FitVerdict
    evidence_ids: list[str] = Field(default_factory=list)
    capability_ids: list[str] = Field(default_factory=list)
    blocked_by: list[str] = Field(default_factory=list)
    caveat: str = ""
    why: str = ""
    materiality_basis: str = ""


class DossierSilence(BaseModel):
    problem_id: str
    reason: str
    question: str = ""


class DossierEvidence(BaseModel):
    """The exact licensed fact a persisted dossier reference resolved to."""

    id: str
    kind: EvidenceKind
    claim: str
    verbatim: str
    source: str = ""
    strength: str
    category: str
    value_band: str

    @classmethod
    def of(cls, evidence: Evidence) -> "DossierEvidence":
        return cls(
            id=evidence.id,
            kind=evidence.kind,
            claim=evidence.claim,
            verbatim=evidence.verbatim,
            source=evidence.source,
            strength=str(evidence.strength),
            category=str(category_of(evidence)),
            value_band=str(value_of(evidence).band),
        )


class ValidationCounts(BaseModel):
    dropped_items: int = 0
    normalized_items: int = 0


def claim_identity(text: str, evidence_ids: Iterable[str] = ()) -> str:
    """The identity two claim rows must share to be the same claim.

    Evidence first, because that is what a claim actually spends: the ledger
    row licensing "Pro is $29/month" is the same fact whether the profile
    worded it as a customer claim or the contested-territory check worded it
    as one to hold back, and set arithmetic over *text* would never notice.
    Text is the fallback for claims that carry no ledger reference at all -
    a scope boundary, or a capability we have not verified.
    """
    ids = sorted({item for item in evidence_ids if item})
    if ids:
        return "evidence:" + "|".join(ids)
    return "text:" + " ".join(text.lower().split())


class ContractClaim(BaseModel):
    """One claim, under an identity stable enough to do set arithmetic on."""

    id: str
    text: str
    evidence_ids: list[str] = Field(default_factory=list)
    #: Why this claim landed in the set it landed in. Rendered to the operator,
    #: never to the writer.
    reason: str = ""


class ClaimContract(BaseModel):
    """What a campaign may say, must not say, and is choosing not to say.

    Four sets, of which exactly three are mutually exclusive and one is not.
    `verified_product_claims` is the broad internal inventory and deliberately
    overlaps everything - it is the record of what is true, not a licence to
    print it. The other three partition that inventory for one dossier, and
    `campaign_allowed_claims` is the only one the writer is ever handed.

    The separation that matters is forbidden against withheld. Forbidden is
    "this is not true of us": a scope boundary, or a capability nobody
    verified. Withheld is "this may well be true and we are not spending it
    here": contested territory, a WITHHOLD ranking, evidence with no
    customer-copy licence, evidence irrelevant to any problem this audience
    has. Collapsing the two - which is what shipping both through one
    `forbidden_claims` list did - loses the distinction between a lie and a
    choice, and makes the operator read a pricing fact as a prohibition.
    """

    contract_version: int = 1
    verified_product_claims: list[ContractClaim] = Field(default_factory=list)
    campaign_allowed_claims: list[ContractClaim] = Field(default_factory=list)
    forbidden_claims: list[ContractClaim] = Field(default_factory=list)
    withheld_claims: list[ContractClaim] = Field(default_factory=list)
    #: Conflicts resolved and data-quality problems found while building. A
    #: non-empty list is not a failure; it is the audit trail of one.
    warnings: list[str] = Field(default_factory=list)

    @property
    def allowed_ids(self) -> set[str]:
        return {item.id for item in self.campaign_allowed_claims}

    @property
    def forbidden_ids(self) -> set[str]:
        return {item.id for item in self.forbidden_claims}

    @property
    def withheld_ids(self) -> set[str]:
        return {item.id for item in self.withheld_claims}

    @property
    def allowed_evidence_ids(self) -> list[str]:
        """Every ledger id the allowed set is licensed by, in a stable order."""
        ids: list[str] = []
        for claim in self.campaign_allowed_claims:
            ids.extend(claim.evidence_ids)
        return list(dict.fromkeys(ids))

    def conflicts(self) -> list[str]:
        """Any breach of the three-way disjointness invariant.

        Empty for anything `build_claim_contract` produced - it resolves
        conflicts rather than reporting them. This exists so a contract that
        arrived from anywhere else can be checked before it is trusted.
        """
        found: list[str] = []
        for left, right in (
            ("allowed", "forbidden"),
            ("allowed", "withheld"),
            ("forbidden", "withheld"),
        ):
            shared = getattr(self, f"{left}_ids") & getattr(self, f"{right}_ids")
            found.extend(
                f"Claim {item!r} is in both {left} and {right} claims."
                for item in sorted(shared)
            )
        return found


class RecommendationState(StrEnum):
    RECOMMENDED = "RECOMMENDED"
    RECOMMENDED_NARROW = "RECOMMENDED_NARROW"
    DISCOVERY_ONLY = "DISCOVERY_ONLY"
    NOT_RECOMMENDED = "NOT_RECOMMENDED"


class CampaignReadiness(StrEnum):
    GO = "GO"
    GO_NARROW = "GO_NARROW"
    DISCOVERY_ONLY = "DISCOVERY_ONLY"
    NO_GO = "NO_GO"


class QualifiedCompanySnapshot(BaseModel):
    prospect_id: UUID
    name: str
    url: str = ""
    qualification: CompanyQualification


class RecommendedCompany(BaseModel):
    prospect_id: UUID
    name: str
    url: str = ""
    classification: QualificationClass
    reason_codes: list[str] = Field(default_factory=list)
    hard_disqualifiers_triggered: list[str] = Field(default_factory=list)


class CampaignRecommendation(BaseModel):
    state: RecommendationState
    readiness: CampaignReadiness
    reasons: list[str] = Field(default_factory=list)
    eligible_subsegment: str = ""
    qualified_companies: list[RecommendedCompany] = Field(default_factory=list)
    adjacent_companies: list[RecommendedCompany] = Field(default_factory=list)
    excluded_companies: list[RecommendedCompany] = Field(default_factory=list)
    unverified_companies: list[RecommendedCompany] = Field(default_factory=list)
    allowed_claims: list[str] = Field(default_factory=list)
    allowed_evidence_ids: list[str] = Field(default_factory=list)
    forbidden_claims: list[str] = Field(default_factory=list)
    forbidden_capability_ids: list[str] = Field(default_factory=list)
    forbidden_evidence_ids: list[str] = Field(default_factory=list)
    unresolved_objections: list[str] = Field(default_factory=list)
    recommended_next_action: str = ""
    override_risk: str = ""
    #: The structured contract the four flat lists above are projections of.
    #: Optional so a V2 dossier persisted before the contract existed still
    #: loads; `None` means legacy, and readers tighten it themselves.
    claim_contract: ClaimContract | None = None


class RelevanceDossier(BaseModel):
    #: Payload V1 stays readable. Only newly normalized capability-aware rows
    #: are V2, and campaign adapters branch on this rather than rewriting V1.
    schema_version: int = 1
    audience_research_id: UUID
    audience_name: str
    audience_research_version: int
    knowledge_id: UUID
    knowledge_version: int
    market_scan_id: UUID
    market_scan_version: int
    capability_profile_id: UUID | None = None
    capability_profile_version: int | None = None
    qualification_fingerprint: str = ""
    built_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    orientation: str = ""
    ranked_relevance: list[RankedRelevanceItem] = Field(default_factory=list)
    problem_fits: list[ProblemFit] = Field(default_factory=list)
    segment_objections: list[Objection] = Field(default_factory=list)
    silences: list[DossierSilence] = Field(default_factory=list)
    evidence: list[DossierEvidence] = Field(default_factory=list)
    validation_counts: ValidationCounts = Field(default_factory=ValidationCounts)
    validation_warnings: list[str] = Field(default_factory=list)
    recommendation: CampaignRecommendation | None = None


class DossierState(StrEnum):
    CURRENT = "current"
    STALE = "stale"
    MISSING = "missing"


class MissingPrerequisite(BaseModel):
    code: str
    message: str


class RelevanceStatus(BaseModel):
    audience_name: str
    status: DossierState
    stale_reasons: list[str] = Field(default_factory=list)
    missing_prerequisites: list[MissingPrerequisite] = Field(default_factory=list)
    dossier_id: UUID | None = None
    generation_version: int | None = None
    created_at: datetime | None = None
    dossier: RelevanceDossier | None = None


class RelevanceValidationError(RuntimeError):
    """Normalization could not produce a meaningful verified dossier."""


class RelevanceAnalyst:
    """Make the one closed-world relevance call and verify its answer."""

    def __init__(self, session: ModelSession) -> None:
        self._session = session

    async def analyse(
        self,
        *,
        artifacts: KnowledgeArtifacts,
        knowledge_id: UUID,
        knowledge_version: int,
        research: AudienceResearch,
        research_id: UUID,
        research_version: int,
        positioning: PositioningMap,
        market_scan_id: UUID,
        market_scan_version: int,
        capability_profile: ProductCapabilityProfile | None = None,
        capability_profile_id: UUID | None = None,
        capability_profile_version: int | None = None,
        company_qualifications: list[QualifiedCompanySnapshot] | None = None,
        qualification_fingerprint: str = "",
    ) -> RelevanceDossier:
        proposal = await self._session.structured(
            role=ROLE_ID,
            tier=ModelTier.DEEP,
            template="relevance_dossier",
            variables={
                "product_context": _product_context(
                    artifacts,
                    knowledge_id,
                    knowledge_version,
                    capability_profile=capability_profile,
                ),
                "audience_context": _audience_context(
                    research, research_id, research_version
                ),
                "market_context": _market_context(
                    positioning, market_scan_id, market_scan_version
                ),
            },
            task=(
                "Return one campaign-independent relevance dossier. Select and license; "
                "do not write an angle, subject, opening, CTA, sequence, or email copy. "
                "Use only the exact evidence and problem ids supplied."
            ),
            schema=RelevanceProposal,
            # This call must remain closed even if the role catalogue changes.
            tools=[],
        )
        return normalize_dossier(
            proposal,
            ledger=artifacts.evidence,
            research=research,
            positioning=positioning,
            knowledge_id=knowledge_id,
            knowledge_version=knowledge_version,
            research_id=research_id,
            research_version=research_version,
            market_scan_id=market_scan_id,
            market_scan_version=market_scan_version,
            capability_profile=capability_profile,
            capability_profile_id=capability_profile_id,
            capability_profile_version=capability_profile_version,
            company_qualifications=company_qualifications or [],
            qualification_fingerprint=qualification_fingerprint,
        )


def normalize_dossier(
    proposal: RelevanceProposal,
    *,
    ledger: EvidenceLedger,
    research: AudienceResearch,
    positioning: PositioningMap,
    knowledge_id: UUID,
    knowledge_version: int,
    research_id: UUID,
    research_version: int,
    market_scan_id: UUID,
    market_scan_version: int,
    capability_ids: set[str] | None = None,
    constraint_ids: set[str] | None = None,
    capability_profile: ProductCapabilityProfile | None = None,
    capability_profile_id: UUID | None = None,
    capability_profile_version: int | None = None,
    company_qualifications: list[QualifiedCompanySnapshot] | None = None,
    qualification_fingerprint: str = "",
) -> RelevanceDossier:
    """Resolve every model reference and enforce each verdict mechanically.

    Optional capability and constraint id sets make the boundary forward
    compatible.  V1 passes neither because the repository has neither a stable
    capability catalogue nor persisted product constraints.
    """

    if capability_profile is not None:
        capability_ids = {
            item.id
            for item in capability_profile.capabilities
            if item.state is CapabilityState.VERIFIED
        }
        constraint_ids = {item.id for item in capability_profile.constraints}

    evidence_by_id = {entry.id: entry for entry in ledger.entries}
    problems_by_id = {problem.id: problem for problem in research.problems}
    counts = ValidationCounts()
    warnings: list[str] = []

    orientation, orientation_changed = _orientation(proposal.orientation, ledger)
    if orientation_changed:
        counts.normalized_items += 1
        warnings.append("Orientation was shortened or removed by deterministic validation.")

    ranked: list[RankedRelevanceItem] = []
    ranked_ids: set[str] = set()
    for proposed in proposal.ranked_relevance:
        evidence = evidence_by_id.get(proposed.evidence_id)
        if evidence is None:
            counts.dropped_items += 1
            warnings.append(f"Dropped ranking with unknown evidence id {proposed.evidence_id!r}.")
            continue
        if proposed.evidence_id in ranked_ids:
            counts.dropped_items += 1
            warnings.append(
                f"Dropped duplicate ranking for evidence {proposed.evidence_id!r}; first band won."
            )
            continue
        why, why_changed = _short_sentence(proposed.why)
        if not why:
            counts.dropped_items += 1
            warnings.append(f"Dropped ranking for {proposed.evidence_id!r} without a reason.")
            continue
        problem_ids, problems_changed = _resolved_ids(
            proposed.problem_ids, set(problems_by_id)
        )
        territory = _territory_for(evidence, positioning)
        ranked.append(
            RankedRelevanceItem(
                evidence_id=evidence.id,
                band=proposed.band,
                why=why,
                problem_ids=problem_ids,
                territory=territory,
            )
        )
        ranked_ids.add(evidence.id)
        if why_changed or problems_changed:
            counts.normalized_items += 1
            warnings.append(f"Normalized ranking for evidence {evidence.id!r}.")

    if len(ranked) > MAX_RANKED_EVIDENCE:
        overflow = len(ranked) - MAX_RANKED_EVIDENCE
        ranked = ranked[:MAX_RANKED_EVIDENCE]
        counts.dropped_items += overflow
        warnings.append(f"Dropped {overflow} ranking(s) above the deterministic limit.")

    # Contested and withheld evidence cannot license an answer to an objection.
    # This has to be settled here, while the objections are still being built:
    # `recommend_campaign` runs afterwards and would only ever find an answer
    # that already reads as licensed.
    unlicensed_for_copy = withheld_evidence_ids(ranked)
    if capability_profile is not None:
        unlicensed_for_copy |= _unverified_capability_evidence(capability_profile) & set(
            evidence_by_id
        )

    fits: list[ProblemFit] = []
    fitted_problems: set[str] = set()
    for proposed in proposal.problem_fits:
        problem = problems_by_id.get(proposed.problem_id)
        if problem is None:
            counts.dropped_items += 1
            warnings.append(f"Dropped fit with unknown problem id {proposed.problem_id!r}.")
            continue
        if problem.id in fitted_problems:
            counts.dropped_items += 1
            warnings.append(f"Dropped duplicate fit for problem {problem.id!r}.")
            continue

        evidence_ids, evidence_changed = _resolved_ids(
            proposed.evidence_ids, set(evidence_by_id)
        )
        capabilities, capability_changed = _catalog_ids(
            proposed.capability_ids, capability_ids
        )
        blocked_by, constraints_changed = _catalog_ids(
            proposed.blocked_by, constraint_ids
        )
        caveat, caveat_changed = _short_sentence(proposed.caveat)
        why, why_changed = _short_sentence(proposed.why)
        materiality, materiality_changed = _short_sentence(
            proposed.materiality_basis
        )
        changed = any(
            (
                evidence_changed,
                capability_changed,
                constraints_changed,
                caveat_changed,
                why_changed,
                materiality_changed,
            )
        )

        verdict = proposed.verdict
        valid = True
        if verdict is FitVerdict.SOLVED:
            valid = any(
                evidence_by_id[evidence_id].kind
                in {EvidenceKind.METRIC, EvidenceKind.TESTIMONIAL}
                for evidence_id in evidence_ids
            )
        elif verdict is FitVerdict.PARTIAL:
            valid = bool(evidence_ids or capabilities) and bool(caveat)
        elif verdict is FitVerdict.UNSUPPORTED:
            # Unsupported is the absence of a licensed bridge.  Persuasive
            # prose cannot turn the references the model supplied into one.
            if evidence_ids or capabilities or blocked_by:
                evidence_ids, capabilities, blocked_by = [], [], []
                changed = True
        elif verdict is FitVerdict.IMMATERIAL:
            valid = bool(evidence_ids) and bool(problem.cost) and bool(materiality)
        elif verdict is FitVerdict.ADDRESSED:
            valid = capability_ids is not None and bool(capabilities)
        elif verdict is FitVerdict.OFF_LIMITS:
            valid = constraint_ids is not None and bool(blocked_by)

        if not valid:
            counts.dropped_items += 1
            warnings.append(
                f"Dropped {verdict} fit for {problem.id!r}; its mechanical requirements failed."
            )
            continue

        fits.append(
            ProblemFit(
                problem_id=problem.id,
                verdict=verdict,
                evidence_ids=evidence_ids,
                capability_ids=capabilities,
                blocked_by=blocked_by,
                caveat=caveat,
                why=why,
                materiality_basis=materiality,
            )
        )
        fitted_problems.add(problem.id)
        if changed:
            counts.normalized_items += 1
            warnings.append(f"Normalized fit for problem {problem.id!r}.")

    objections: list[Objection] = []
    seen_objections: set[str] = set()
    for proposed in proposal.segment_objections:
        objection, objection_changed = _short_sentence(proposed.objection)
        if not objection:
            counts.dropped_items += 1
            warnings.append("Dropped an empty segment-specific objection.")
            continue
        key = " ".join(objection.lower().split())
        if key in seen_objections:
            counts.dropped_items += 1
            warnings.append("Dropped a duplicate segment-specific objection.")
            continue
        evidence_ids, evidence_changed = _resolved_ids(
            proposed.evidence_ids, set(evidence_by_id)
        )
        licensed = [item for item in evidence_ids if item not in unlicensed_for_copy]
        if licensed != evidence_ids:
            warnings.append(
                f"Stripped withheld or contested evidence from the answer to {objection!r}: "
                + ", ".join(sorted(set(evidence_ids) - set(licensed)))
                + "."
            )
            evidence_ids = licensed
            evidence_changed = True
        answer, answer_changed = _short_sentence(proposed.answer)
        if answer and not evidence_ids:
            answer = ""
            answer_changed = True
        objections.append(
            Objection(
                objection=objection,
                severity=proposed.severity.strip() or "strong",
                answer=answer,
                grounding=Grounding.INFERRED,
                evidence_ids=evidence_ids,
            )
        )
        seen_objections.add(key)
        if objection_changed or evidence_changed or answer_changed:
            counts.normalized_items += 1
            warnings.append(f"Normalized objection {objection!r}.")

    silences: list[DossierSilence] = []
    silenced_problems: set[str] = set()
    for proposed in proposal.silences:
        problem = problems_by_id.get(proposed.problem_id)
        if problem is None:
            counts.dropped_items += 1
            warnings.append(f"Dropped silence with unknown problem id {proposed.problem_id!r}.")
            continue
        if problem.id in silenced_problems:
            counts.dropped_items += 1
            warnings.append(f"Dropped duplicate silence for problem {problem.id!r}.")
            continue
        reason, reason_changed = _short_sentence(proposed.reason)
        question, question_changed = _short_sentence(proposed.question)
        if not reason:
            counts.dropped_items += 1
            warnings.append(f"Dropped silence for {problem.id!r} without a reason.")
            continue
        silences.append(
            DossierSilence(problem_id=problem.id, reason=reason, question=question)
        )
        silenced_problems.add(problem.id)
        if reason_changed or question_changed:
            counts.normalized_items += 1
            warnings.append(f"Normalized silence for problem {problem.id!r}.")

    if not ranked and not fits and not silences:
        raise RelevanceValidationError(
            "The relevance proposal contained no verified ranking, problem fit, or meaningful "
            "silence after deterministic validation. No dossier was saved."
        )

    referenced = set()
    referenced.update(item.evidence_id for item in ranked)
    for fit in fits:
        referenced.update(fit.evidence_ids)
    for objection in objections:
        referenced.update(objection.evidence_ids)
    evidence_snapshot = [
        DossierEvidence.of(entry) for entry in ledger.entries if entry.id in referenced
    ]

    dossier = RelevanceDossier(
        schema_version=2 if capability_profile is not None else 1,
        audience_research_id=research_id,
        audience_name=research.audience_name,
        audience_research_version=research_version,
        knowledge_id=knowledge_id,
        knowledge_version=knowledge_version,
        market_scan_id=market_scan_id,
        market_scan_version=market_scan_version,
        capability_profile_id=capability_profile_id,
        capability_profile_version=capability_profile_version,
        qualification_fingerprint=qualification_fingerprint,
        orientation=orientation,
        ranked_relevance=ranked,
        problem_fits=fits,
        segment_objections=objections,
        silences=silences,
        evidence=evidence_snapshot,
        validation_counts=counts,
        validation_warnings=list(dict.fromkeys(warnings)),
    )
    if capability_profile is not None:
        dossier.recommendation = recommend_campaign(
            dossier,
            profile=capability_profile,
            research=research,
            companies=company_qualifications or [],
            ledger=ledger,
        )
    return dossier


def withheld_evidence_ids(ranked: Iterable[RankedRelevanceItem]) -> set[str]:
    """Evidence this dossier ranked as not worth spending, or contested.

    A free function because `normalize_dossier` needs it while it is still
    building objections, long before any recommendation exists - and an
    objection answered out of contested evidence is exactly the kind of
    licensed-looking claim this contract is here to stop.
    """
    return {
        item.evidence_id
        for item in ranked
        if item.band is RelevanceBand.WITHHOLD or item.territory is Territory.CONTESTED
    }


def _unverified_capability_evidence(profile: ProductCapabilityProfile) -> set[str]:
    """Ledger ids whose only job was to establish a capability nobody verified."""
    return {
        entry.evidence_id
        for item in profile.capabilities
        if item.state is not CapabilityState.VERIFIED
        for entry in item.evidence
    }


def relevant_evidence_ids(
    ranked: Iterable[RankedRelevanceItem], fits: Iterable[ProblemFit]
) -> set[str]:
    """Evidence this dossier actually connected to this audience.

    Two ways in, because the verdicts that carry a real fit reference evidence
    differently: SOLVED and PARTIAL name ledger ids directly, while ADDRESSED
    is licensed by a capability and may name none at all. A LEAD or SUPPORT
    ranking is the dossier's own judgment that a fact belongs in this
    conversation, so it counts on its own.

    Everything else in the ledger is true and irrelevant. Shipping all of it
    as usable copy material was the whole defect.
    """
    relevant = {
        item.evidence_id
        for item in ranked
        if item.band in {RelevanceBand.LEAD, RelevanceBand.SUPPORT}
    }
    for fit in fits:
        if fit.verdict in {FitVerdict.SOLVED, FitVerdict.ADDRESSED, FitVerdict.PARTIAL}:
            relevant.update(fit.evidence_ids)
    return relevant


def _dedupe_claims(claims: Iterable[ContractClaim]) -> list[ContractClaim]:
    """First row of each identity wins; input order is preserved."""
    seen: dict[str, ContractClaim] = {}
    for claim in claims:
        seen.setdefault(claim.id, claim)
    return list(seen.values())


def _withhold_reason(evidence_id: str, ranked: Iterable[RankedRelevanceItem]) -> str:
    item = next((row for row in ranked if row.evidence_id == evidence_id), None)
    if item is None:
        return "Withheld from this campaign."
    if item.territory is Territory.CONTESTED:
        return "Contested territory: every rival makes this claim too."
    return "Ranked WITHHOLD for this audience."


def _unusable_reason(
    evidence_id: str,
    ranked: Iterable[RankedRelevanceItem],
    forbidden_evidence: set[str],
) -> str:
    """Why one referenced id cannot be spent. Names the cause, not the symptom.

    "Contested territory" tells an operator something they can act on;
    "rests on unusable evidence E-price" only tells them to go and look.
    """
    if evidence_id in forbidden_evidence:
        return "Establishes a capability nobody verified."
    return _withhold_reason(evidence_id, ranked)


def build_claim_contract(
    *,
    profile: ProductCapabilityProfile,
    ledger: EvidenceLedger,
    ranked: list[RankedRelevanceItem],
    fits: list[ProblemFit],
) -> ClaimContract:
    """Partition product truth into what this one campaign may spend.

    Safe by construction rather than by afterthought: a claim has to earn its
    way into the allowed set past four separate tests, and anything that fails
    any of them lands in a set the writer never sees. Where a claim qualifies
    for more than one set the precedence is fixed - forbidden beats withheld
    beats allowed - so the same inputs always yield the same contract and an
    operator can re-derive any row by hand.
    """
    warnings: list[str] = []
    valid_ids = ledger.ids
    withheld_evidence = withheld_evidence_ids(ranked)
    forbidden_evidence = _unverified_capability_evidence(profile) & valid_ids
    unusable = withheld_evidence | forbidden_evidence
    relevant = relevant_evidence_ids(ranked, fits)

    verified: list[ContractClaim] = []
    allowed: list[ContractClaim] = []
    withheld: list[ContractClaim] = []
    forbidden: list[ContractClaim] = []

    for claim in profile.claims:
        ids = [item for item in dict.fromkeys(claim.evidence_ids) if item in valid_ids]
        identity = claim_identity(claim.text, ids)
        verified.append(
            ContractClaim(
                id=identity,
                text=claim.text,
                evidence_ids=ids,
                reason=claim.reason or f"Product truth ({claim.visibility}).",
            )
        )

        held = ""
        if claim.visibility is not ClaimVisibility.CUSTOMER:
            held = "Not licensed for customer-facing copy."
        elif not ids:
            warnings.append(
                f"Customer claim {claim.text!r} names no ledger evidence that still exists."
            )
            held = "No surviving ledger evidence licenses this claim."
        elif blocked := sorted(set(ids) & unusable):
            # Any blocked reference disqualifies the whole claim. Keeping a
            # claim because *some other* id survived is how a contested price
            # ended up campaign-safe.
            warnings.append(
                f"Claim {claim.text!r} rests on withheld or forbidden evidence "
                f"({', '.join(blocked)}) and is not campaign-safe."
            )
            held = " ".join(
                dict.fromkeys(
                    _unusable_reason(item, ranked, forbidden_evidence) for item in blocked
                )
            )
        elif not set(ids) & relevant:
            held = "No addressed or partial problem for this audience uses it."

        target = withheld if held else allowed
        target.append(
            ContractClaim(
                id=identity,
                text=claim.text,
                evidence_ids=ids,
                reason=held or claim.reason or "Licensed, relevant, and customer-safe.",
            )
        )

    for boundary in profile.constraints:
        forbidden.append(
            ContractClaim(
                id=claim_identity(boundary.statement),
                text=boundary.statement,
                reason=f"Scope boundary {boundary.id}.",
            )
        )
    for capability in profile.capabilities:
        if capability.state is CapabilityState.VERIFIED:
            continue
        ids = [item.evidence_id for item in capability.evidence if item.evidence_id]
        forbidden.append(
            ContractClaim(
                id=claim_identity(capability.label, ids),
                text=f"Do not claim {capability.label}; its capability state is {capability.state}.",
                evidence_ids=[item for item in ids if item in valid_ids],
                reason=f"Capability {capability.id} is {capability.state}.",
            )
        )

    for evidence_id in sorted(withheld_evidence):
        entry = ledger.get(evidence_id)
        if entry is None:
            warnings.append(
                f"Ranked evidence {evidence_id!r} is no longer in the ledger."
            )
            continue
        withheld.append(
            ContractClaim(
                id=claim_identity(entry.claim, [evidence_id]),
                text=entry.claim,
                evidence_ids=[evidence_id],
                reason=_withhold_reason(evidence_id, ranked),
            )
        )

    # Precedence: forbidden beats withheld beats allowed. Matched on identity
    # *and* on wording, because the two arrive keyed differently - a scope
    # boundary carries no evidence id, so a prohibition worded exactly like a
    # licensed claim would otherwise slip past an id-only comparison.
    forbidden_rows = _dedupe_claims(forbidden)
    forbidden_keys = {item.id for item in forbidden_rows} | {
        claim_identity(item.text) for item in forbidden_rows
    }
    withheld_rows: list[ContractClaim] = []
    for claim in _dedupe_claims(withheld):
        if {claim.id, claim_identity(claim.text)} & forbidden_keys:
            warnings.append(
                f"Claim {claim.text!r} was both forbidden and withheld; forbidden won."
            )
            continue
        withheld_rows.append(claim)
    withheld_keys = {item.id for item in withheld_rows} | {
        claim_identity(item.text) for item in withheld_rows
    }
    allowed_rows: list[ContractClaim] = []
    for claim in _dedupe_claims(allowed):
        keys = {claim.id, claim_identity(claim.text)}
        if keys & forbidden_keys:
            warnings.append(
                f"Claim {claim.text!r} was both allowed and forbidden; forbidden won."
            )
            continue
        if keys & withheld_keys:
            warnings.append(
                f"Claim {claim.text!r} was both allowed and withheld; withheld won."
            )
            continue
        allowed_rows.append(claim)

    return ClaimContract(
        verified_product_claims=_dedupe_claims(verified),
        campaign_allowed_claims=allowed_rows,
        forbidden_claims=forbidden_rows,
        withheld_claims=withheld_rows,
        warnings=list(dict.fromkeys(warnings)),
    )


def recommend_campaign(
    dossier: RelevanceDossier,
    *,
    profile: ProductCapabilityProfile,
    research: AudienceResearch,
    companies: list[QualifiedCompanySnapshot],
    ledger: EvidenceLedger,
) -> CampaignRecommendation:
    """Derive a persisted recommendation from normalized, inspectable facts."""
    grouped: dict[QualificationClass, list[RecommendedCompany]] = {
        item: [] for item in QualificationClass
    }
    for item in companies:
        qualification = item.qualification
        grouped[qualification.classification].append(
            RecommendedCompany(
                prospect_id=item.prospect_id,
                name=item.name,
                url=item.url,
                classification=qualification.classification,
                reason_codes=qualification.reason_codes,
                hard_disqualifiers_triggered=qualification.hard_disqualifiers_triggered,
            )
        )

    required_unavailable = [
        capability_id
        for capability_id in research.definition.required_product_capabilities
        if profile.state_of(capability_id) is not CapabilityState.VERIFIED
    ]
    positive = [
        item
        for item in dossier.problem_fits
        if item.verdict in {FitVerdict.SOLVED, FitVerdict.ADDRESSED}
    ]
    partial = [item for item in dossier.problem_fits if item.verdict is FitVerdict.PARTIAL]
    unsupported = [
        item
        for item in dossier.problem_fits
        if item.verdict in {FitVerdict.UNSUPPORTED, FitVerdict.OFF_LIMITS}
    ]
    reasons: list[str] = []

    if required_unavailable:
        state = RecommendationState.NOT_RECOMMENDED
        reasons.extend(
            f"Required product capability is not verified: {capability_id}."
            for capability_id in required_unavailable
        )
    elif companies and not grouped[QualificationClass.QUALIFIED]:
        if grouped[QualificationClass.EXCLUDED]:
            state = RecommendationState.NOT_RECOMMENDED
            reasons.append("No researched company qualified; one or more hard exclusions fired.")
        else:
            state = RecommendationState.DISCOVERY_ONLY
            reasons.append("No researched company has complete direct qualification evidence.")
    elif positive and not unsupported and not dossier.silences:
        if (
            partial
            or grouped[QualificationClass.ADJACENT]
            or grouped[QualificationClass.EXCLUDED]
            or grouped[QualificationClass.UNVERIFIED]
        ):
            state = RecommendationState.RECOMMENDED_NARROW
            reasons.append("A licensed product bridge exists only for the qualified slice.")
        else:
            state = RecommendationState.RECOMMENDED
            reasons.append("Verified product evidence addresses the researched audience problem.")
    elif positive or partial:
        state = RecommendationState.RECOMMENDED_NARROW
        reasons.append("The current product fit is partial or carries unresolved scope limits.")
    elif unsupported or dossier.silences:
        state = RecommendationState.DISCOVERY_ONLY
        reasons.append("Research found a need, but the current product evidence does not bridge it.")
    else:
        state = RecommendationState.DISCOVERY_ONLY
        reasons.append("There is not enough licensed evidence to recommend a truthful campaign.")

    readiness = {
        RecommendationState.RECOMMENDED: CampaignReadiness.GO,
        RecommendationState.RECOMMENDED_NARROW: CampaignReadiness.GO_NARROW,
        RecommendationState.DISCOVERY_ONLY: CampaignReadiness.DISCOVERY_ONLY,
        RecommendationState.NOT_RECOMMENDED: CampaignReadiness.NO_GO,
    }[state]

    contract = build_claim_contract(
        profile=profile,
        ledger=ledger,
        ranked=dossier.ranked_relevance,
        fits=dossier.problem_fits,
    )
    forbidden_capability_ids = [
        item.id
        for item in profile.capabilities
        if item.state is not CapabilityState.VERIFIED
    ]
    # Every ledger id the campaign may not reference at all: the contested and
    # withheld rankings, plus whatever was only ever there to establish a
    # capability nobody verified. `intelligence.py` subtracts this from the
    # usable set, so it has to be the union, not just the rankings.
    unusable_evidence = withheld_evidence_ids(dossier.ranked_relevance) | (
        _unverified_capability_evidence(profile) & ledger.ids
    )
    unresolved = [
        item.objection for item in dossier.segment_objections if not item.answer.strip()
    ]
    unresolved.extend(item.question or item.reason for item in dossier.silences)

    eligible = next(iter(research.definition.eligible_subsegments), "")
    if state is RecommendationState.NOT_RECOMMENDED:
        next_action = (
            f"Narrow the audience to {eligible}."
            if eligible
            else "Narrow the audience to a workflow the current verified capabilities support."
        )
        risk = (
            "Generating anyway risks implying product capabilities or company problems that "
            "the current evidence does not establish. Copy will remain claim-constrained."
        )
    elif state is RecommendationState.DISCOVERY_ONLY:
        next_action = (
            "Gather direct product and company evidence before treating this as an outreach list."
        )
        risk = (
            "Generating now will require audience-level hypotheses and may produce a weak "
            "campaign because company-specific fit is unresolved."
        )
    elif state is RecommendationState.RECOMMENDED_NARROW:
        next_action = (
            f"Target only {eligible}." if eligible else "Target only companies classified QUALIFIED."
        )
        risk = (
            "Generating outside the eligible slice risks writing to a structurally similar "
            "company whose actual need the product cannot support."
        )
    else:
        next_action = "Proceed with the qualified audience and licensed claims."
        risk = "No material qualification mismatch is currently known."

    return CampaignRecommendation(
        state=state,
        readiness=readiness,
        reasons=list(dict.fromkeys(reasons)),
        eligible_subsegment=eligible,
        qualified_companies=grouped[QualificationClass.QUALIFIED],
        adjacent_companies=grouped[QualificationClass.ADJACENT],
        excluded_companies=grouped[QualificationClass.EXCLUDED],
        unverified_companies=grouped[QualificationClass.UNVERIFIED],
        # The four flat lists stay, as projections of the contract, so every
        # existing reader keeps working. They are now the narrow sets.
        allowed_claims=[item.text for item in contract.campaign_allowed_claims],
        allowed_evidence_ids=contract.allowed_evidence_ids,
        forbidden_claims=[item.text for item in contract.forbidden_claims],
        forbidden_capability_ids=list(dict.fromkeys(forbidden_capability_ids)),
        forbidden_evidence_ids=sorted(unusable_evidence),
        unresolved_objections=list(dict.fromkeys(unresolved)),
        recommended_next_action=next_action,
        override_risk=risk,
        claim_contract=contract,
    )


def _product_context(
    artifacts: KnowledgeArtifacts,
    knowledge_id: UUID,
    knowledge_version: int,
    *,
    capability_profile: ProductCapabilityProfile | None = None,
) -> str:
    evidence = []
    for entry in artifacts.evidence.entries:
        value = value_of(entry)
        evidence.append(
            {
                "id": entry.id,
                "kind": str(entry.kind),
                "shelf": str(category_of(entry)),
                "value_band": str(value.band),
                "strength": str(entry.strength),
                "claim": entry.claim,
                "verbatim_grounding": entry.verbatim,
                "source": entry.source,
                "user_attested": entry.user_attested,
            }
        )
    return json.dumps(
        {
            "knowledge_id": str(knowledge_id),
            "knowledge_version": knowledge_version,
            "product_identity": {
                "company_name": artifacts.business.company_name,
                "what_it_does": artifacts.business.what_it_does,
                "category": artifacts.business.category,
            },
            "complete_evidence_ledger": evidence,
            "capability_catalogue_available": capability_profile is not None,
            "constraint_catalogue_available": capability_profile is not None,
            "capability_profile": (
                capability_profile.model_dump(mode="json")
                if capability_profile is not None
                else None
            ),
        },
        ensure_ascii=False,
        indent=2,
    )


def _audience_context(
    research: AudienceResearch, research_id: UUID, research_version: int
) -> str:
    return json.dumps(
        {
            "audience_research_id": str(research_id),
            "audience_research_version": research_version,
            "research": research.model_dump(mode="json"),
        },
        ensure_ascii=False,
        indent=2,
    )


def _market_context(
    positioning: PositioningMap, market_scan_id: UUID, market_scan_version: int
) -> str:
    return json.dumps(
        {
            "market_scan_id": str(market_scan_id),
            "market_scan_version": market_scan_version,
            "positioning_map": positioning.model_dump(mode="json"),
        },
        ensure_ascii=False,
        indent=2,
    )


def _territory_for(
    evidence: Evidence, positioning: PositioningMap
) -> Territory | None:
    axis = axis_for_evidence(evidence)
    reading = next((item for item in positioning.readings if item.axis is axis), None)
    return reading.territory if reading is not None else None


def _resolved_ids(proposed: list[str], valid: set[str]) -> tuple[list[str], bool]:
    cleaned = [item for item in dict.fromkeys(proposed) if item in valid]
    return cleaned, cleaned != proposed


def _catalog_ids(
    proposed: list[str], catalogue: set[str] | None
) -> tuple[list[str], bool]:
    if catalogue is None:
        return [], bool(proposed)
    return _resolved_ids(proposed, catalogue)


_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_WHITESPACE = re.compile(r"\s+")
_CTA = re.compile(
    r"\b(?:click|reply|book|schedule|sign\s*up|start\s+(?:now|today|a\s+trial)|"
    r"try\s+(?:it|this)|learn\s+more|buy\s+now)\b",
    re.IGNORECASE,
)


def _short_sentence(value: str, limit: int = 240) -> tuple[str, bool]:
    original = value
    text = _WHITESPACE.sub(" ", value).strip().strip('"“”')
    parts = _SENTENCE_SPLIT.split(text, maxsplit=1)
    if parts:
        text = parts[0]
    if len(text) > limit:
        text = text[:limit].rsplit(" ", 1)[0].rstrip(" ,;:")
    if text and text[-1] not in ".!?":
        text += "."
    return text, text != original.strip()


def _orientation(value: str, ledger: EvidenceLedger) -> tuple[str, bool]:
    orientation, changed = _short_sentence(value)
    if not orientation:
        return "", changed
    if _CTA.search(orientation) or EvidenceIndex(ledger).unsupported(orientation):
        return "", True
    return orientation, changed
