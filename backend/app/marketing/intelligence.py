"""The bounded audience intelligence one campaign may carry into strategy.

Audience research and relevance dossiers are durable market artifacts.  A
campaign reads them; it never creates or refreshes them.  This module is the
adapter between those artifacts and the deliberately older, smaller campaign
types: it resolves one selected audience, renders only the verified facts the
Strategist needs, and makes the few mechanical dossier rules deterministic.
"""

import re
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field, ValidationError

from app.knowledge.artifacts import (
    Fact,
    Grounding,
    KnowledgeArtifacts,
    Objection,
    Provenance,
    Segment,
)
from app.knowledge.ledger import EvidenceLedger
from app.market.audience_research import (
    AudienceProblem,
    AudienceResearch,
    BuyerPhrase,
    EvidenceReference,
    SourcedObservation,
)
from app.market.qualification import CompanyQualification, SignalGrounding
from app.market.relevance import (
    CampaignReadiness,
    ClaimContract,
    DossierState,
    FitVerdict,
    RecommendationState,
    RelevanceBand,
    RelevanceDossier,
    RelevanceStatus,
)
from app.models.market import AudienceResearchRow

_WORD_RE = re.compile(r"[a-z0-9]+")
_GENERIC_AUDIENCE_WORDS = frozenset(
    {
        "audience",
        "business",
        "businesses",
        "buyer",
        "buyers",
        "company",
        "companies",
        "customer",
        "customers",
        "developer",
        "developers",
        "people",
        "person",
        "professional",
        "professionals",
        "team",
        "teams",
        "user",
        "users",
        "with",
        "who",
        "that",
        "their",
    }
)

MAX_RESEARCH_PROBLEMS = 12
MAX_RESEARCH_OBSERVATIONS = 8
MAX_BUYER_PHRASES = 12
MAX_DOSSIER_RANKINGS = 30
MAX_DOSSIER_OBJECTIONS = 12
MAX_VALIDATION_WARNINGS = 20


class AudienceResolution(StrEnum):
    LOADED = "audience_research_loaded"
    MISSING = "audience_research_missing"
    AMBIGUOUS = "audience_research_ambiguous"


class DossierPosture(StrEnum):
    CURRENT = "current"
    STALE = "stale"
    MISSING = "missing"


class IntelligenceObservation(BaseModel):
    text: str
    grounding: str


class IntelligenceProblem(BaseModel):
    id: str
    statement: str
    grounding: str
    corroboration: int = 0
    cost: str = ""


class IntelligencePhrase(BaseModel):
    text: str
    kind: str


class IntelligenceRanking(BaseModel):
    evidence_id: str
    band: RelevanceBand
    why: str = ""
    problem_ids: list[str] = Field(default_factory=list)


class IntelligenceFit(BaseModel):
    problem_id: str
    verdict: FitVerdict
    evidence_ids: list[str] = Field(default_factory=list)
    caveat: str = ""
    why: str = ""
    materiality_basis: str = ""


class IntelligenceSilence(BaseModel):
    problem_id: str
    reason: str
    question: str = ""


class CampaignIntelligenceTrace(BaseModel):
    selected_audience: str
    audience_resolution_status: AudienceResolution
    audience_research_id: UUID | None = None
    audience_research_version: int | None = None
    dossier_status: DossierPosture = DossierPosture.MISSING
    dossier_id: UUID | None = None
    dossier_version: int | None = None
    dossier_schema_version: int = 1
    stale_reasons: list[str] = Field(default_factory=list)
    legacy_fallback_used: bool = True
    withhold_evidence_selected: list[str] = Field(default_factory=list)
    partial_caveats_injected: list[str] = Field(default_factory=list)
    validation_warnings: list[str] = Field(default_factory=list)

    def warn(self, warning: str) -> None:
        warning = _compact(warning)
        if (
            warning
            and warning not in self.validation_warnings
            and len(self.validation_warnings) < MAX_VALIDATION_WARNINGS
        ):
            self.validation_warnings.append(warning)


class CampaignIntelligence(BaseModel):
    """Only the selected audience's verified, campaign-independent context."""

    selected_audience: str
    situation: IntelligenceObservation | None = None
    problems: list[IntelligenceProblem] = Field(default_factory=list)
    incumbent_behaviour: list[IntelligenceObservation] = Field(default_factory=list)
    triggers: list[IntelligenceObservation] = Field(default_factory=list)
    desired_outcomes: list[IntelligenceObservation] = Field(default_factory=list)
    sophistication: str = ""
    buyer_phrases: list[IntelligencePhrase] = Field(default_factory=list)
    signals: list[IntelligenceObservation] = Field(default_factory=list)
    where: list[IntelligenceObservation] = Field(default_factory=list)
    orientation: str = ""
    ranked_evidence: list[IntelligenceRanking] = Field(default_factory=list)
    problem_fits: list[IntelligenceFit] = Field(default_factory=list)
    objections: list[Objection] = Field(default_factory=list)
    silences: list[IntelligenceSilence] = Field(default_factory=list)
    recommendation_state: RecommendationState | None = None
    readiness: CampaignReadiness | None = None
    recommendation_reasons: list[str] = Field(default_factory=list)
    allowed_claims: list[str] = Field(default_factory=list)
    allowed_evidence_ids: list[str] = Field(default_factory=list)
    forbidden_claims: list[str] = Field(default_factory=list)
    forbidden_capability_ids: list[str] = Field(default_factory=list)
    forbidden_evidence_ids: list[str] = Field(default_factory=list)
    #: True, and deliberately unspent here. Carried so the operator can audit
    #: the choice; never rendered to the writer as usable material.
    withheld_claims: list[str] = Field(default_factory=list)
    #: `None` for a legacy dossier that predates the contract.
    claim_contract: ClaimContract | None = None
    selected_company_name: str = ""
    selected_company_url: str = ""
    selected_company_qualification: CompanyQualification | None = None
    trace: CampaignIntelligenceTrace

    @property
    def research_loaded(self) -> bool:
        return self.trace.audience_resolution_status is AudienceResolution.LOADED

    @property
    def dossier_current(self) -> bool:
        return self.trace.dossier_status is DossierPosture.CURRENT

    def render_for_strategy(self) -> str:
        """Compact and deterministic; source pages and the full ledger stay out."""
        lines = [
            "Source authority (highest first):",
            "1. Complete Evidence Ledger: final authority on every product claim.",
            "2. Current Relevance Dossier: ranking and product/problem fit judgment.",
            "3. Verified Audience Research: authority on this buyer's reality.",
            "4. Positioning Map: authority on current market territory.",
            "5. Discovery map: hypotheses and fallback only.",
            "6. Compiled stated audience: the company's view and final fallback.",
            "",
            f"Selected audience: {self.selected_audience}",
            f"Audience resolution: {self.trace.audience_resolution_status}",
        ]
        if not self.research_loaded:
            if self.trace.audience_resolution_status is AudienceResolution.AMBIGUOUS:
                lines.append(
                    "More than one researched audience matched. Use discovery and compiled "
                    "audience material; do not borrow from any research row."
                )
            else:
                lines.append(
                    "No matching verified research exists. Use discovery and compiled audience "
                    "material exactly as the fallback."
                )
            return "\n".join(lines)

        lines.extend(
            [
                (
                    "Audience Research: "
                    f"{self.trace.audience_research_id} v{self.trace.audience_research_version}"
                ),
                f"Researched situation: {self.situation.text if self.situation else 'not established'}",
                f"Observed sophistication: {self.sophistication or 'not established'}",
            ]
        )
        _render_observations(lines, "Incumbent behaviour", self.incumbent_behaviour)
        _render_observations(lines, "Verified triggers", self.triggers)
        _render_observations(lines, "Desired outcomes", self.desired_outcomes)
        if self.problems:
            lines.append("Verified problems (felt_need must come from one of these):")
            lines.extend(
                f"- [{item.id}] {item.statement} "
                f"(grounding={item.grounding}, corroboration={item.corroboration}"
                + (f", cost={item.cost}" if item.cost else "")
                + ")"
                for item in self.problems
            )
        if self.buyer_phrases:
            lines.append(
                "Buyer vocabulary (word choice only; never present these as attributed product "
                "quotations):"
            )
            lines.extend(f"- ({item.kind}) {item.text}" for item in self.buyer_phrases)
        _render_observations(lines, "Observable signals", self.signals)
        _render_observations(lines, "Where this audience is found", self.where)

        lines.extend(
            [
                "",
                f"Relevance Dossier status: {self.trace.dossier_status}",
            ]
        )
        if self.trace.dossier_status is DossierPosture.MISSING:
            lines.append(
                "No dossier exists. Derive product relevance from the complete ledger and "
                "legacy inputs as before."
            )
            return "\n".join(lines)
        lines.append(f"Dossier: {self.trace.dossier_id} v{self.trace.dossier_version}")
        if self.recommendation_state is not None:
            # One label. `readiness` is the same fact under a second name, and
            # printing both taught the reader there were two verdicts to weigh.
            lines.append(f"Campaign recommendation: {self.recommendation_state}")
            lines.extend(f"- {item}" for item in self.recommendation_reasons)
            lines.append(
                "The claims below are the complete set of product facts this campaign may "
                "assert. Anything not listed is unavailable to you, however true it is "
                "elsewhere in the product's knowledge."
            )
            if self.allowed_claims:
                lines.append("Campaign-safe product claims:")
                lines.extend(f"- {item}" for item in self.allowed_claims)
            else:
                lines.append(
                    "Campaign-safe product claims: none. Do not assert a product fact."
                )
            if self.forbidden_claims:
                lines.append("Never claim any of these:")
                lines.extend(f"- {item}" for item in self.forbidden_claims)
            # `withheld_claims` is deliberately NOT rendered here. Those are
            # true, attractive facts we chose not to spend, and a list of them
            # under "do not use" is an invitation to use them. They stay on the
            # context object for the operator's audit view and go no further.

        if self.selected_company_name:
            lines.append(
                f"Selected company: {self.selected_company_name}"
                + (f" ({self.selected_company_url})" if self.selected_company_url else "")
            )
            if self.selected_company_qualification is None:
                lines.append(
                    "No company qualification is available. Write at audience or hypothesis "
                    "level; do not assert anything about this company's internal workflow."
                )
            else:
                qualification = self.selected_company_qualification
                lines.append(f"Company classification: {qualification.classification}")
                direct = [
                    item
                    for item in qualification.evidence
                    if item.grounding is SignalGrounding.DIRECT
                ]
                if direct:
                    lines.append("Direct company evidence (background, not product proof):")
                    lines.extend(
                        f"- {item.code}={item.value}: {item.quote} "
                        f"[source: {item.source_identifier or 'company site'}]"
                        for item in direct
                    )
                else:
                    lines.append(
                        "No direct company workflow evidence is available. Use audience-level "
                        "or explicitly hypothetical language."
                    )
        if self.trace.dossier_status is DossierPosture.STALE:
            lines.append(
                "STALE ADVISORY ONLY. Do not force its orientation or ranking. Stale because: "
                + ", ".join(self.trace.stale_reasons)
            )
        elif self.orientation:
            lines.append(
                "Current licensed orientation (normalization will use this): " + self.orientation
            )

        if self.ranked_evidence:
            lines.append(
                "Ranked ledger references: prefer LEAD, strengthen with SUPPORT, use CONTEXT "
                + (
                    "only to explain. Withheld and contested references are already gone "
                    "from this list and from the claims above; there is nothing here you "
                    "have to hold back by judgment."
                    if self.v2_claim_boundary
                    else "only to explain, and normally avoid WITHHOLD. WITHHOLD remains "
                    "licensed by the complete ledger and is advisory, not deletion."
                )
            )
            lines.extend(
                f"- [{item.evidence_id}] {item.band}: {item.why}"
                + (f" (problems: {', '.join(item.problem_ids)})" if item.problem_ids else "")
                for item in self.ranked_evidence
            )
        if self.problem_fits:
            lines.append("Verified product/problem fits:")
            for fit in self.problem_fits:
                detail = f"- [{fit.problem_id}] {fit.verdict}"
                if fit.evidence_ids:
                    detail += f" via {', '.join(fit.evidence_ids)}"
                if fit.caveat:
                    detail += f"; required caveat: {fit.caveat}"
                if fit.materiality_basis:
                    detail += f"; materiality: {fit.materiality_basis}"
                lines.append(detail)
        if self.objections:
            lines.append("Segment-specific objections:")
            lines.extend(item.render() for item in self.objections)
        if self.silences:
            lines.append("Problems this campaign must not promise to solve:")
            lines.extend(
                f"- [{item.problem_id}] {item.reason}"
                + (f"; unanswered question: {item.question}" if item.question else "")
                for item in self.silences
            )
        unsupported = [
            fit.problem_id for fit in self.problem_fits if fit.verdict is FitVerdict.UNSUPPORTED
        ]
        if unsupported:
            lines.append(
                "UNSUPPORTED problems must not become product promises: "
                + ", ".join(unsupported)
            )
        if self.trace.validation_warnings:
            lines.append(
                "Validation warnings: " + "; ".join(self.trace.validation_warnings)
            )
        return "\n".join(lines)

    def problem_statement(self, problem_id: str) -> str:
        return next(
            (item.statement for item in self.problems if item.id == problem_id), ""
        )

    def normalized_felt_need(self, proposed: str) -> str:
        if not self.problems:
            return proposed
        matched = _one_text_match(proposed, [item.statement for item in self.problems])
        return matched or self.problems[0].statement

    def normalized_status_quo(self, proposed: str) -> str:
        choices = [item.text for item in self.incumbent_behaviour]
        if not choices:
            return proposed
        return _one_text_match(proposed, choices) or choices[0]

    def validate_against(self, ledger: EvidenceLedger) -> None:
        """Recheck every dossier reference at the campaign boundary."""
        valid_evidence = ledger.ids
        self.allowed_evidence_ids = [
            item for item in self.allowed_evidence_ids if item in valid_evidence
        ]
        self.forbidden_evidence_ids = [
            item for item in self.forbidden_evidence_ids if item in valid_evidence
        ]
        usable_evidence = (
            valid_evidence - set(self.forbidden_evidence_ids)
            if self.v2_claim_boundary
            else valid_evidence
        )
        if self.claim_contract is not None:
            # A campaign-safe claim needs *every* id it rests on to still be
            # usable. Partial survival is what let a claim outlive the evidence
            # that licensed it.
            safe = [
                item
                for item in self.claim_contract.campaign_allowed_claims
                if item.evidence_ids and set(item.evidence_ids) <= usable_evidence
            ]
            dropped = len(self.claim_contract.campaign_allowed_claims) - len(safe)
            if dropped:
                self.trace.warn(
                    f"Dropped {dropped} campaign-safe claim(s) whose evidence no longer "
                    "licenses them."
                )
            self.claim_contract = self.claim_contract.model_copy(
                update={"campaign_allowed_claims": safe}
            )
            self.allowed_claims = [item.text for item in safe]
            self.allowed_evidence_ids = self.claim_contract.allowed_evidence_ids

        valid_problems = {item.id for item in self.problems}
        rankings: list[IntelligenceRanking] = []
        for item in self.ranked_evidence:
            if item.evidence_id not in usable_evidence:
                self.trace.warn(
                    f"Ignored unavailable dossier ranking {item.evidence_id}."
                )
                continue
            problem_ids = [id_ for id_ in item.problem_ids if id_ in valid_problems]
            if len(problem_ids) != len(item.problem_ids):
                self.trace.warn(
                    f"Ignored unknown problem references on ranking {item.evidence_id}."
                )
            item.problem_ids = problem_ids
            rankings.append(item)
        self.ranked_evidence = rankings

        fits: list[IntelligenceFit] = []
        for fit in self.problem_fits:
            if fit.problem_id not in valid_problems:
                self.trace.warn(
                    f"Ignored dossier fit with unknown problem id {fit.problem_id}."
                )
                continue
            if (
                not self.v2_claim_boundary
                and fit.verdict in {FitVerdict.ADDRESSED, FitVerdict.OFF_LIMITS}
            ):
                self.trace.warn(
                    f"Ignored unavailable {fit.verdict} fit for problem {fit.problem_id}."
                )
                continue
            evidence_ids = [id_ for id_ in fit.evidence_ids if id_ in usable_evidence]
            if len(evidence_ids) != len(fit.evidence_ids):
                self.trace.warn(
                    f"Ignored unknown evidence references on fit {fit.problem_id}."
                )
            fit.evidence_ids = evidence_ids
            if fit.verdict in {FitVerdict.UNSUPPORTED, FitVerdict.OFF_LIMITS}:
                fit.evidence_ids = []
            if fit.verdict in {FitVerdict.SOLVED, FitVerdict.ADDRESSED} and not fit.evidence_ids:
                self.trace.warn(
                    f"Ignored {fit.verdict} fit for {fit.problem_id} without licensed evidence."
                )
                continue
            if fit.verdict is FitVerdict.PARTIAL and (
                not fit.evidence_ids or not fit.caveat
            ):
                self.trace.warn(
                    f"Ignored PARTIAL fit for {fit.problem_id} without evidence and caveat."
                )
                continue
            fits.append(fit)
        self.problem_fits = fits

        objections: list[Objection] = []
        for objection in self.objections:
            ids = [id_ for id_ in objection.evidence_ids if id_ in usable_evidence]
            if len(ids) != len(objection.evidence_ids):
                self.trace.warn(
                    f"Ignored unknown evidence references on objection "
                    f"{objection.objection!r}."
                )
            objections.append(
                objection.model_copy(
                    update={"evidence_ids": ids, "answer": objection.answer if ids else ""}
                )
            )
        self.objections = objections
        silences: list[IntelligenceSilence] = []
        for silence in self.silences:
            if silence.problem_id not in valid_problems:
                self.trace.warn(
                    f"Ignored dossier silence with unknown problem id {silence.problem_id}."
                )
                continue
            silences.append(silence)
        self.silences = silences

    def constraints_for(self, evidence_ids: list[str], ledger: EvidenceLedger) -> list[str]:
        """Safety constraints mechanically implied by selected, still-licensed ids."""
        selected = set(evidence_ids) & ledger.ids
        caveats: list[str] = []
        for fit in self.problem_fits:
            valid_ids = set(fit.evidence_ids) & ledger.ids
            if (
                fit.verdict is FitVerdict.PARTIAL
                and fit.caveat
                and selected & valid_ids
            ):
                caveats.append(fit.caveat)
        return _distinct(caveats)

    def selected_withhold(self, evidence_ids: list[str], ledger: EvidenceLedger) -> list[str]:
        valid = set(evidence_ids) & ledger.ids
        return _distinct(
            [
                item.evidence_id
                for item in self.ranked_evidence
                if item.band is RelevanceBand.WITHHOLD and item.evidence_id in valid
            ]
        )

    @property
    def v2_claim_boundary(self) -> bool:
        return self.trace.dossier_schema_version >= 2 and self.recommendation_state is not None


@dataclass(frozen=True)
class CampaignIntelligenceBundle:
    artifacts: KnowledgeArtifacts
    context: CampaignIntelligence


@dataclass(frozen=True)
class AudienceResearchMatch:
    status: AudienceResolution
    row: AudienceResearchRow | None = None
    research: AudienceResearch | None = None


def resolve_audience_research(
    selected_audience: str, rows: list[AudienceResearchRow]
) -> AudienceResearchMatch:
    """Exact normalized identity first; forgiving containment only when unique."""
    wanted = _audience_key(selected_audience)
    if not wanted:
        return AudienceResearchMatch(status=AudienceResolution.MISSING)

    parsed: list[tuple[AudienceResearchRow, AudienceResearch]] = []
    for row in rows:
        try:
            parsed.append((row, AudienceResearch.model_validate(row.payload)))
        except ValidationError:
            continue

    exact = [(row, research) for row, research in parsed if row.audience_key == wanted]
    if len(exact) == 1:
        return AudienceResearchMatch(
            status=AudienceResolution.LOADED, row=exact[0][0], research=exact[0][1]
        )
    if len(exact) > 1:
        return AudienceResearchMatch(status=AudienceResolution.AMBIGUOUS)

    candidates = [
        (row, research)
        for row, research in parsed
        if _forgiving_audience_match(wanted, row.audience_key)
    ]
    if len(candidates) == 1:
        return AudienceResearchMatch(
            status=AudienceResolution.LOADED,
            row=candidates[0][0],
            research=candidates[0][1],
        )
    return AudienceResearchMatch(
        status=(
            AudienceResolution.AMBIGUOUS if len(candidates) > 1 else AudienceResolution.MISSING
        )
    )


def build_campaign_intelligence(
    *,
    selected_audience: str,
    match: AudienceResearchMatch,
    dossier_status: RelevanceStatus | None,
    ledger: EvidenceLedger,
) -> CampaignIntelligence:
    trace = CampaignIntelligenceTrace(
        selected_audience=selected_audience,
        audience_resolution_status=match.status,
    )
    if match.row is None or match.research is None:
        return CampaignIntelligence(selected_audience=selected_audience, trace=trace)

    research = match.research
    trace.audience_research_id = match.row.id
    trace.audience_research_version = match.row.version
    context = CampaignIntelligence(
        selected_audience=research.audience_name,
        situation=_observation(research.situation),
        problems=[_problem(item) for item in research.problems[:MAX_RESEARCH_PROBLEMS]],
        incumbent_behaviour=_observations(research.incumbent_behaviour),
        triggers=_observations(research.triggers),
        desired_outcomes=_observations(research.desired_outcomes),
        sophistication=str(research.sophistication or ""),
        buyer_phrases=[_phrase(item) for item in research.buyer_phrases[:MAX_BUYER_PHRASES]],
        signals=_observations(research.signals),
        where=_observations(research.where),
        trace=trace,
    )
    if dossier_status is None or dossier_status.dossier is None:
        return context

    trace.dossier_status = (
        DossierPosture.CURRENT
        if dossier_status.status is DossierState.CURRENT
        else DossierPosture.STALE
    )
    trace.dossier_id = dossier_status.dossier_id
    trace.dossier_version = dossier_status.generation_version
    trace.stale_reasons = list(dossier_status.stale_reasons)
    trace.legacy_fallback_used = trace.dossier_status is not DossierPosture.CURRENT
    dossier = dossier_status.dossier
    trace.dossier_schema_version = dossier.schema_version
    _add_dossier(context, dossier, ledger)
    return context


def adapt_researched_audience(
    artifacts: KnowledgeArtifacts,
    research: AudienceResearch,
    context: CampaignIntelligence,
) -> KnowledgeArtifacts:
    """Replace only the selected primary segment and keep every legacy fallback."""
    merged = artifacts.model_copy(deep=True)
    base = _selected_segment(merged, context.trace.selected_audience, research.audience_name)
    desired = _best_observation(research.desired_outcomes)
    trigger = "; ".join(_distinct([item.text for item in research.triggers])[:3])
    situation = research.situation.text if research.situation else base.situation
    segment = Segment(
        name=research.audience_name,
        situation=situation,
        job_to_be_done=desired.text if desired is not None else base.job_to_be_done,
        trigger=trigger or base.trigger,
        sophistication=research.sophistication or base.sophistication,
        pains=[_problem_fact(item, research) for item in research.problems],
    )
    remove = {
        _audience_key(context.trace.selected_audience),
        _audience_key(research.audience_name),
        _audience_key(base.name),
    }
    merged.audience.segments = [
        item for item in merged.audience.segments if _audience_key(item.name) not in remove
    ]
    merged.audience.segments.insert(0, segment)
    if context.dossier_current:
        _merge_objections(merged, context.objections)
    return merged


def attach_selected_dossier_objection(
    artifacts: KnowledgeArtifacts,
    context: CampaignIntelligence,
    selected_objections: list[str],
) -> None:
    """Give the unchanged Writer the answer for only objections the brief chose."""
    if context.dossier_current:
        return
    chosen: list[Objection] = []
    for proposed in selected_objections:
        match = _matching_objection(proposed, context.objections)
        if match is not None:
            chosen.append(match)
    _merge_objections(artifacts, chosen)


def _add_dossier(
    context: CampaignIntelligence, dossier: RelevanceDossier, ledger: EvidenceLedger
) -> None:
    valid_evidence = ledger.ids
    valid_problems = {item.id for item in context.problems}
    context.orientation = _compact(dossier.orientation)
    context.trace.validation_warnings = _distinct(dossier.validation_warnings)[
        :MAX_VALIDATION_WARNINGS
    ]
    if dossier.schema_version >= 2 and dossier.recommendation is not None:
        recommendation = dossier.recommendation
        context.recommendation_state = recommendation.state
        context.readiness = recommendation.readiness
        context.recommendation_reasons = list(recommendation.reasons)
        context.allowed_claims = list(recommendation.allowed_claims)
        context.allowed_evidence_ids = list(recommendation.allowed_evidence_ids)
        context.forbidden_claims = list(recommendation.forbidden_claims)
        context.forbidden_capability_ids = list(
            recommendation.forbidden_capability_ids
        )
        context.forbidden_evidence_ids = list(recommendation.forbidden_evidence_ids)
        context.claim_contract = recommendation.claim_contract
        if recommendation.claim_contract is None:
            # A V2 dossier persisted before the contract existed. Its two lists
            # were built independently and can overlap, so tighten them here
            # rather than hand a writer a claim its own dossier forbids.
            forbidden = set(context.forbidden_claims)
            kept = [item for item in context.allowed_claims if item not in forbidden]
            if len(kept) != len(context.allowed_claims):
                context.trace.warn(
                    "Legacy dossier allowed a claim it also forbids; forbidden won."
                )
            context.allowed_claims = kept
        else:
            context.withheld_claims = [
                item.text for item in recommendation.claim_contract.withheld_claims
            ]

    for item in dossier.ranked_relevance[:MAX_DOSSIER_RANKINGS]:
        if item.evidence_id not in valid_evidence:
            context.trace.warn(
                f"Ignored dossier ranking with unknown evidence id {item.evidence_id}."
            )
            continue
        context.ranked_evidence.append(
            IntelligenceRanking(
                evidence_id=item.evidence_id,
                band=item.band,
                why=_compact(item.why),
                problem_ids=[id_ for id_ in item.problem_ids if id_ in valid_problems],
            )
        )

    for fit in dossier.problem_fits[:MAX_RESEARCH_PROBLEMS]:
        if fit.problem_id not in valid_problems:
            context.trace.warn(
                f"Ignored dossier fit with unknown problem id {fit.problem_id}."
            )
            continue
        if fit.verdict in {FitVerdict.ADDRESSED, FitVerdict.OFF_LIMITS}:
            context.trace.warn(
                f"Ignored unavailable {fit.verdict} fit for problem {fit.problem_id}."
            )
            continue
        evidence_ids = [id_ for id_ in fit.evidence_ids if id_ in valid_evidence]
        if len(evidence_ids) != len(fit.evidence_ids):
            context.trace.warn(
                f"Ignored unknown evidence references on fit {fit.problem_id}."
            )
        if fit.verdict is FitVerdict.UNSUPPORTED:
            evidence_ids = []
        if fit.verdict is FitVerdict.SOLVED and not evidence_ids:
            context.trace.warn(
                f"Ignored SOLVED fit for {fit.problem_id} without licensed evidence."
            )
            continue
        if fit.verdict is FitVerdict.PARTIAL and (
            not evidence_ids or not fit.caveat.strip()
        ):
            context.trace.warn(
                f"Ignored PARTIAL fit for {fit.problem_id} without evidence and caveat."
            )
            continue
        context.problem_fits.append(
            IntelligenceFit(
                problem_id=fit.problem_id,
                verdict=fit.verdict,
                evidence_ids=evidence_ids,
                caveat=_compact(fit.caveat),
                why=_compact(fit.why),
                materiality_basis=_compact(fit.materiality_basis),
            )
        )

    for objection in dossier.segment_objections[:MAX_DOSSIER_OBJECTIONS]:
        evidence_ids = [id_ for id_ in objection.evidence_ids if id_ in valid_evidence]
        answer = _compact(objection.answer) if evidence_ids else ""
        if len(evidence_ids) != len(objection.evidence_ids):
            context.trace.warn(
                f"Ignored unknown evidence references on objection {objection.objection!r}."
            )
        context.objections.append(
            objection.model_copy(
                update={
                    "objection": _compact(objection.objection),
                    "answer": answer,
                    "evidence_ids": evidence_ids,
                }
            )
        )

    for silence in dossier.silences[:MAX_RESEARCH_PROBLEMS]:
        if silence.problem_id not in valid_problems:
            context.trace.warn(
                f"Ignored dossier silence with unknown problem id {silence.problem_id}."
            )
            continue
        context.silences.append(
            IntelligenceSilence(
                problem_id=silence.problem_id,
                reason=_compact(silence.reason),
                question=_compact(silence.question),
            )
        )


def _observation(item: SourcedObservation | None) -> IntelligenceObservation | None:
    if item is None or not item.text.strip():
        return None
    return IntelligenceObservation(text=_compact(item.text), grounding=str(item.grounding))


def _observations(items: list[SourcedObservation]) -> list[IntelligenceObservation]:
    return [
        found
        for item in items[:MAX_RESEARCH_OBSERVATIONS]
        if (found := _observation(item)) is not None
    ]


def _problem(item: AudienceProblem) -> IntelligenceProblem:
    return IntelligenceProblem(
        id=item.id,
        statement=_compact(item.statement),
        grounding=str(item.grounding),
        corroboration=item.corroboration,
        cost=_compact(item.cost),
    )


def _phrase(item: BuyerPhrase) -> IntelligencePhrase:
    return IntelligencePhrase(text=_compact(item.text), kind=str(item.kind))


def _problem_fact(item: AudienceProblem, research: AudienceResearch) -> Fact:
    reference = item.evidence[0] if item.evidence else None
    return Fact(
        statement=item.statement,
        grounding=item.grounding,
        provenance=_provenance(reference, research) if reference else None,
    )


def _provenance(
    reference: EvidenceReference, research: AudienceResearch
) -> Provenance:
    source = next((item for item in research.sources if item.id == reference.source_id), None)
    return Provenance(
        source=source.final_url if source is not None else "",
        quote=reference.quote,
    )


def _best_observation(items: list[SourcedObservation]) -> SourcedObservation | None:
    if not items:
        return None
    order = {Grounding.GROUNDED: 2, Grounding.USER_STATED: 1, Grounding.INFERRED: 0}
    return max(items, key=lambda item: (order[item.grounding], len(item.evidence)))


def _selected_segment(
    artifacts: KnowledgeArtifacts, selected: str, researched_name: str
) -> Segment:
    wanted = {_audience_key(selected), _audience_key(researched_name)}
    exact = [
        item for item in artifacts.audience.segments if _audience_key(item.name) in wanted
    ]
    if len(exact) == 1:
        return exact[0]
    forgiving = [
        item
        for item in artifacts.audience.segments
        if any(_forgiving_audience_match(key, _audience_key(item.name)) for key in wanted)
    ]
    if len(forgiving) == 1:
        return forgiving[0]
    return Segment(name=researched_name)


def _merge_objections(artifacts: KnowledgeArtifacts, objections: list[Objection]) -> None:
    existing = {_audience_key(item.objection) for item in artifacts.audience.objections}
    for objection in reversed(objections):
        key = _audience_key(objection.objection)
        if key and key not in existing:
            artifacts.audience.objections.insert(0, objection)
            existing.add(key)


def _matching_objection(proposed: str, objections: list[Objection]) -> Objection | None:
    choices = [item.objection for item in objections]
    matched = _one_text_match(proposed, choices)
    return next((item for item in objections if item.objection == matched), None)


def _one_text_match(proposed: str, choices: list[str]) -> str:
    wanted = _audience_key(proposed)
    if not wanted:
        return ""
    exact = [choice for choice in choices if _audience_key(choice) == wanted]
    if len(exact) == 1:
        return exact[0]
    contained = [
        choice
        for choice in choices
        if wanted in _audience_key(choice) or _audience_key(choice) in wanted
    ]
    return contained[0] if len(contained) == 1 else ""


def _render_observations(
    lines: list[str], label: str, observations: list[IntelligenceObservation]
) -> None:
    if observations:
        lines.append(label + ":")
        lines.extend(f"- {item.text} (grounding={item.grounding})" for item in observations)


def _forgiving_audience_match(left: str, right: str) -> bool:
    if not left or not right or not (left in right or right in left):
        return False
    smaller = left if len(left) <= len(right) else right
    meaningful = {
        word
        for word in _WORD_RE.findall(smaller)
        if len(word) > 3 and word not in _GENERIC_AUDIENCE_WORDS
    }
    return len(meaningful) >= 2


def _audience_key(value: str) -> str:
    return " ".join(value.casefold().split())


def _compact(value: str, limit: int = 360) -> str:
    compact = " ".join(value.split())
    return compact if len(compact) <= limit else compact[: limit - 1].rstrip() + "…"


def _distinct(items: list[str]) -> list[str]:
    seen: set[str] = set()
    kept: list[str] = []
    for item in items:
        key = _audience_key(item)
        if key and key not in seen:
            kept.append(item)
            seen.add(key)
    return kept
