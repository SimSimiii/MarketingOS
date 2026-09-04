"""Deterministic audience and company qualification.

Models may extract candidate signals from fetched pages.  They do not decide
eligibility: every hard override and every missing-evidence outcome lives here.
"""

from __future__ import annotations

import hashlib
import json
import re
from enum import StrEnum

from pydantic import BaseModel, Field

from app.market.capabilities import CapabilityState, ProductCapabilityProfile, normalize_code


class QualificationClass(StrEnum):
    QUALIFIED = "QUALIFIED"
    ADJACENT = "ADJACENT"
    EXCLUDED = "EXCLUDED"
    UNVERIFIED = "UNVERIFIED"


class QualificationDimension(StrEnum):
    STRONG = "strong"
    PARTIAL = "partial"
    MISMATCH = "mismatch"
    UNKNOWN = "unknown"


class Reachability(StrEnum):
    REACHABLE = "reachable"
    UNREACHABLE = "unreachable"
    UNKNOWN = "unknown"


class EvidenceCompleteness(StrEnum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    MISSING = "missing"


class SignalGrounding(StrEnum):
    DIRECT = "direct"
    INFERENCE = "inference"
    MISSING = "missing"


class AudienceRequirement(BaseModel):
    code: str
    description: str = ""


class AudienceExclusion(BaseModel):
    code: str
    description: str = ""
    outcome: QualificationClass = QualificationClass.EXCLUDED


class AudienceDefinition(BaseModel):
    """The machine-readable half of a mapped audience.

    Defaults keep every stored V1 demand map readable. An empty definition is
    deliberately insufficient for a company to become QUALIFIED.
    """

    schema_version: int = 2
    required_structural_signals: list[AudienceRequirement] = Field(default_factory=list)
    required_workflow_signals: list[AudienceRequirement] = Field(default_factory=list)
    required_product_capabilities: list[str] = Field(default_factory=list)
    optional_signals: list[AudienceRequirement] = Field(default_factory=list)
    hard_disqualifiers: list[AudienceExclusion] = Field(default_factory=list)
    eligible_subsegments: list[str] = Field(default_factory=list)
    excluded_subsegments: list[str] = Field(default_factory=list)
    max_team_size: int | None = Field(default=None, ge=1)


class CompanySignal(BaseModel):
    code: str
    value: str = "true"
    grounding: SignalGrounding = SignalGrounding.DIRECT
    quote: str = ""
    source_identifier: str = ""

    @property
    def positive(self) -> bool:
        return self.value.casefold().strip() in {"1", "true", "yes", "present", "required"}


COMPANY_REQUIREMENT_EXTRACTOR_VERSION = 2
COMPANY_REQUIREMENT_NORMALIZER_VERSION = 2
COMPANY_QUALIFIER_VERSION = 2


class CompanyCapabilityRequirement(BaseModel):
    """A company-published need mapped by the extractor to the active catalogue."""

    capability_id: str
    evidence_state: SignalGrounding = SignalGrounding.DIRECT
    quote: str = ""
    source_url: str = ""
    reasoning: str = ""


class UnmappedCompanyRequirement(BaseModel):
    """A directly evidenced need for which the active catalogue has no ID."""

    raw_requirement: str
    evidence_state: SignalGrounding = SignalGrounding.DIRECT
    quote: str = ""
    source_url: str = ""
    mapped_capability_id: None = None
    reasoning: str = ""


class CapabilityRequirementMatch(BaseModel):
    """The deterministic comparison receipt for one mapped requirement."""

    capability_id: str
    display_name: str
    company_evidence_state: SignalGrounding
    quote: str
    source_url: str
    reasoning: str = ""
    product_capability_state: CapabilityState
    reason_code: str


class CompanyQualificationIdentity(BaseModel):
    capability_profile_version: int = 0
    capability_catalog_fingerprint: str = ""
    requirement_extractor_version: int = 0
    requirement_normalizer_version: int = 0
    qualifier_version: int = 0


class CompanyQualification(BaseModel):
    classification: QualificationClass
    audience_structure_fit: QualificationDimension
    product_capability_fit: QualificationDimension
    evidence_completeness: EvidenceCompleteness
    reachability: Reachability
    reason_codes: list[str] = Field(default_factory=list)
    hard_disqualifiers_triggered: list[str] = Field(default_factory=list)
    evidence: list[CompanySignal] = Field(default_factory=list)
    requirements: list[CompanyCapabilityRequirement] = Field(default_factory=list)
    unmapped_requirements: list[UnmappedCompanyRequirement] = Field(default_factory=list)
    capability_matches: list[CapabilityRequirementMatch] = Field(default_factory=list)
    identity: CompanyQualificationIdentity = Field(default_factory=CompanyQualificationIdentity)

    def stale_reasons(self, profile: ProductCapabilityProfile) -> list[str]:
        expected = qualification_identity(profile)
        reasons: list[str] = []
        if (
            self.identity.capability_catalog_fingerprint
            != expected.capability_catalog_fingerprint
        ):
            reasons.append("capability_catalog_changed")
        if self.identity.requirement_extractor_version != expected.requirement_extractor_version:
            reasons.append("company_requirement_extractor_changed")
        if self.identity.requirement_normalizer_version != expected.requirement_normalizer_version:
            reasons.append("company_requirement_normalizer_changed")
        if self.identity.qualifier_version != expected.qualifier_version:
            reasons.append("company_qualifier_changed")
        return reasons


def qualification_identity(profile: ProductCapabilityProfile) -> CompanyQualificationIdentity:
    return CompanyQualificationIdentity(
        capability_profile_version=profile.version,
        capability_catalog_fingerprint=_capability_catalog_fingerprint(profile),
        requirement_extractor_version=COMPANY_REQUIREMENT_EXTRACTOR_VERSION,
        requirement_normalizer_version=COMPANY_REQUIREMENT_NORMALIZER_VERSION,
        qualifier_version=COMPANY_QUALIFIER_VERSION,
    )


def _capability_catalog_fingerprint(profile: ProductCapabilityProfile) -> str:
    """Identity of the semantic namespace, deliberately excluding states."""
    payload = [
        {
            "capability_id": item.id,
            "display_name": item.label,
            "description": item.description,
            "aliases": item.aliases,
        }
        for item in sorted(profile.capabilities, key=lambda item: item.id)
    ]
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def stale_company_qualification(
    qualification: CompanyQualification, profile: ProductCapabilityProfile
) -> CompanyQualification:
    """Expose an old extraction as stale without trusting its old conclusion."""
    stale = qualification.stale_reasons(profile)
    if not stale:
        return qualification
    return qualification.model_copy(
        update={
            "classification": QualificationClass.UNVERIFIED,
            "audience_structure_fit": QualificationDimension.UNKNOWN,
            "product_capability_fit": QualificationDimension.UNKNOWN,
            "reason_codes": ["company_qualification_stale", *stale],
            "hard_disqualifiers_triggered": [],
        }
    )


def qualify_company(
    *,
    definition: AudienceDefinition,
    profile: ProductCapabilityProfile,
    evidence: list[CompanySignal],
    requirements: list[CompanyCapabilityRequirement] | None = None,
    unmapped_requirements: list[UnmappedCompanyRequirement] | None = None,
    site_verified: bool,
    pages_read: int,
    reachable: bool,
) -> CompanyQualification:
    """Classify a company without a blended score or model-authored override."""
    requirements = requirements or []
    unmapped_requirements = unmapped_requirements or []
    identity = qualification_identity(profile)
    if not site_verified or pages_read <= 0:
        return CompanyQualification(
            classification=QualificationClass.UNVERIFIED,
            audience_structure_fit=QualificationDimension.UNKNOWN,
            product_capability_fit=QualificationDimension.UNKNOWN,
            evidence_completeness=EvidenceCompleteness.MISSING,
            reachability=Reachability.UNKNOWN,
            reason_codes=["site_unreadable"],
            evidence=evidence,
            requirements=requirements,
            unmapped_requirements=unmapped_requirements,
            identity=identity,
        )

    validated = [
        item.model_copy(update={"code": normalize_code(item.code)})
        for item in evidence
        if normalize_code(item.code)
    ]
    direct = {
        normalize_code(item.code): item
        for item in validated
        if item.grounding is SignalGrounding.DIRECT and item.quote.strip()
    }
    reasons: list[str] = []
    triggered: list[str] = []

    required_structure = [normalize_code(item.code) for item in definition.required_structural_signals]
    required_workflow = [normalize_code(item.code) for item in definition.required_workflow_signals]
    required = [*required_structure, *required_workflow]
    present = [code for code in required if code in direct and direct[code].positive]
    contradicted = [code for code in required if code in direct and not direct[code].positive]
    missing = [code for code in required if code not in direct]

    if contradicted:
        structure_fit = QualificationDimension.MISMATCH
        reasons.extend(f"required_signal_conflicted:{code}" for code in contradicted)
    elif required and len(present) == len(required):
        structure_fit = QualificationDimension.STRONG
    elif present:
        structure_fit = QualificationDimension.PARTIAL
        reasons.extend(f"required_signal_missing:{code}" for code in missing)
    else:
        structure_fit = QualificationDimension.UNKNOWN
        reasons.extend(f"required_signal_missing:{code}" for code in missing)

    validated_requirements: list[CompanyCapabilityRequirement] = []
    validated_unmapped = list(unmapped_requirements)
    matches: list[CapabilityRequirementMatch] = []
    for requirement in requirements:
        capability_id = normalize_code(requirement.capability_id)
        capability = profile.capability(capability_id)
        if capability is None:
            validated_unmapped.append(
                UnmappedCompanyRequirement(
                    raw_requirement=requirement.capability_id,
                    evidence_state=requirement.evidence_state,
                    quote=requirement.quote,
                    source_url=requirement.source_url,
                    reasoning=requirement.reasoning,
                )
            )
            continue
        normalized = requirement.model_copy(update={"capability_id": capability_id})
        validated_requirements.append(normalized)
        if (
            normalized.evidence_state is not SignalGrounding.DIRECT
            or not normalized.quote.strip()
        ):
            continue
        if capability.state is CapabilityState.UNSUPPORTED:
            reason_code = f"unsupported_required_capability:{capability_id}"
        elif capability.state is CapabilityState.UNKNOWN:
            reason_code = f"unknown_required_capability:{capability_id}"
        else:
            reason_code = f"supported_required_capability:{capability_id}"
        matches.append(
            CapabilityRequirementMatch(
                capability_id=capability_id,
                display_name=capability.label,
                company_evidence_state=normalized.evidence_state,
                quote=normalized.quote,
                source_url=normalized.source_url,
                reasoning=normalized.reasoning,
                product_capability_state=capability.state,
                reason_code=reason_code,
            )
        )

    unsupported_matches = [
        item for item in matches
        if item.product_capability_state is CapabilityState.UNSUPPORTED
    ]
    unknown_matches = [
        item for item in matches
        if item.product_capability_state is CapabilityState.UNKNOWN
    ]
    direct_unmapped = [
        item for item in validated_unmapped
        if item.evidence_state is SignalGrounding.DIRECT and item.quote.strip()
    ]
    for match in unsupported_matches:
        reasons.append(match.reason_code)
        triggered.append(match.reason_code)
    reasons.extend(match.reason_code for match in unknown_matches)
    if direct_unmapped:
        reasons.append("unmapped_company_requirement")

    definition_capabilities = [
        normalize_code(item) for item in definition.required_product_capabilities
        if normalize_code(item)
    ]
    directly_mapped = {item.capability_id for item in matches}
    unresolved_definition_capabilities = [
        capability_id
        for capability_id in definition_capabilities
        if profile.state_of(capability_id) is not CapabilityState.VERIFIED
        and capability_id not in directly_mapped
    ]
    reasons.extend(
        f"required_capability_not_directly_evidenced:{capability_id}"
        for capability_id in unresolved_definition_capabilities
    )
    if unsupported_matches:
        capability_fit = QualificationDimension.MISMATCH
    elif unknown_matches or direct_unmapped or unresolved_definition_capabilities:
        capability_fit = QualificationDimension.UNKNOWN
    elif matches or definition_capabilities:
        capability_fit = QualificationDimension.STRONG
    else:
        capability_fit = QualificationDimension.UNKNOWN

    exclusions = {normalize_code(item.code): item for item in definition.hard_disqualifiers}
    excluded = bool(unsupported_matches)
    adjacent = False
    for code, exclusion in exclusions.items():
        signal = direct.get(code)
        if signal is not None and signal.positive:
            triggered.append(code)
            reasons.append(f"hard_disqualifier:{code}")
            if exclusion.outcome is QualificationClass.EXCLUDED:
                excluded = True
            elif exclusion.outcome is QualificationClass.ADJACENT:
                adjacent = True

    if definition.max_team_size is not None:
        size = _integer_value(direct.get("team_size"))
        if size is not None and size > definition.max_team_size:
            triggered.append("team_above_threshold")
            reasons.append(
                f"team_above_threshold:{size}>{definition.max_team_size}"
            )
            excluded = True

    if required:
        completeness = (
            EvidenceCompleteness.COMPLETE
            if not missing
            else EvidenceCompleteness.PARTIAL
            if present
            else EvidenceCompleteness.MISSING
        )
    else:
        completeness = EvidenceCompleteness.PARTIAL if direct else EvidenceCompleteness.MISSING

    if excluded:
        classification = QualificationClass.EXCLUDED
    elif adjacent:
        classification = QualificationClass.ADJACENT
    elif (
        required
        and structure_fit is QualificationDimension.STRONG
        and capability_fit is not QualificationDimension.MISMATCH
        and not unknown_matches
        and not direct_unmapped
        and not unresolved_definition_capabilities
        and completeness is EvidenceCompleteness.COMPLETE
    ):
        classification = QualificationClass.QUALIFIED
        reasons.append("all_required_signals_verified")
    else:
        classification = QualificationClass.UNVERIFIED
        reasons.append("insufficient_direct_evidence_for_qualification")

    auditable = list(validated)
    auditable.extend(
        CompanySignal(
            code=code,
            value="",
            grounding=SignalGrounding.MISSING,
        )
        for code in missing
        if code not in {item.code for item in auditable}
    )
    return CompanyQualification(
        classification=classification,
        audience_structure_fit=structure_fit,
        product_capability_fit=capability_fit,
        evidence_completeness=completeness,
        reachability=Reachability.REACHABLE if reachable else Reachability.UNREACHABLE,
        reason_codes=list(
            dict.fromkeys(
                [*(item.reason_code for item in unsupported_matches), *reasons]
            )
        ),
        hard_disqualifiers_triggered=list(dict.fromkeys(triggered)),
        evidence=auditable,
        requirements=validated_requirements,
        unmapped_requirements=validated_unmapped,
        capability_matches=matches,
        identity=identity,
    )


def _integer_value(signal: CompanySignal | None) -> int | None:
    if signal is None:
        return None
    found = re.search(r"\d+", signal.value)
    return int(found.group()) if found else None
