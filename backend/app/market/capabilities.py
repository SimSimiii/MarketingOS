"""Persistable product truth used by qualification and relevance V2.

The Evidence Ledger remains the authority for positive customer-facing claims.
This module gives those facts a small capability catalogue and makes the
negative/unknown side inspectable too.  A missing ledger entry can never make a
capability supported, and it cannot manufacture a product-specific unsupported
boundary either. Those boundaries are carried in the brand's versioned profile.
"""

from __future__ import annotations

import hashlib
import json
import re
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field

from app.knowledge.ledger import Evidence, EvidenceLedger


class CapabilityState(StrEnum):
    VERIFIED = "verified"
    UNSUPPORTED = "unsupported"
    UNKNOWN = "unknown"


class ClaimVisibility(StrEnum):
    CUSTOMER = "customer"
    INTERNAL = "internal"


class CapabilityEvidence(BaseModel):
    """One existing ledger fact that establishes a positive capability."""

    evidence_id: str
    claim: str
    quote: str
    source_identifier: str = ""


class ProductCapability(BaseModel):
    id: str
    label: str
    description: str = ""
    state: CapabilityState = CapabilityState.UNKNOWN
    evidence: list[CapabilityEvidence] = Field(default_factory=list)
    #: Alternative customer vocabulary used by the research extractor. These
    #: belong to the profile, not the qualifier, so another product may use a
    #: completely different catalogue and language.
    aliases: list[str] = Field(default_factory=list)
    customer_copy_visibility: ClaimVisibility = ClaimVisibility.INTERNAL
    note: str = ""


class ProductClaim(BaseModel):
    text: str
    visibility: ClaimVisibility = ClaimVisibility.CUSTOMER
    evidence_ids: list[str] = Field(default_factory=list)
    reason: str = ""


class ScopeBoundary(BaseModel):
    id: str
    statement: str
    capability_ids: list[str] = Field(default_factory=list)
    source_identifier: str = "system_policy"
    supporting_quote: str = ""


class ProductCapabilityProfile(BaseModel):
    """A versioned product truth snapshot.

    ``version`` is assigned by the persistence store. ``schema_version``
    versions the payload shape independently from the row history.
    """

    schema_version: int = 2
    version: int = 1
    knowledge_id: UUID
    knowledge_version: int
    ledger_fingerprint: str = ""
    capabilities: list[ProductCapability] = Field(default_factory=list)
    constraints: list[ScopeBoundary] = Field(default_factory=list)
    claims: list[ProductClaim] = Field(default_factory=list)

    def capability(self, capability_id: str) -> ProductCapability | None:
        wanted = normalize_code(capability_id)
        return next((item for item in self.capabilities if item.id == wanted), None)

    def state_of(self, capability_id: str) -> CapabilityState:
        found = self.capability(capability_id)
        return found.state if found is not None else CapabilityState.UNKNOWN

    def extraction_catalog(self) -> list[dict[str, object]]:
        """The exact catalogue company research is allowed to map against."""
        return [
            {
                "capability_id": item.id,
                "display_name": item.label,
                "description": item.description or item.note,
                "state": str(item.state),
                "aliases": item.aliases,
                "customer_copy_visibility": str(item.customer_copy_visibility),
            }
            for item in self.capabilities
        ]

    @property
    def allowed_claims(self) -> list[ProductClaim]:
        return [
            item
            for item in self.claims
            if item.visibility is ClaimVisibility.CUSTOMER and item.evidence_ids
        ]

    @property
    def internal_claims(self) -> list[ProductClaim]:
        return [item for item in self.claims if item.visibility is ClaimVisibility.INTERNAL]


class CapabilityProfileDraft(BaseModel):
    """The editable part of a profile accepted by the API.

    Knowledge pointers and the row version are server-owned. Customer claims
    are still resolved against the current Evidence Ledger before persistence.
    """

    capabilities: list[ProductCapability] = Field(default_factory=list)
    constraints: list[ScopeBoundary] = Field(default_factory=list)
    claims: list[ProductClaim] = Field(default_factory=list)


_EVIDENCE_DERIVATION_HINTS: dict[str, tuple[str, tuple[str, ...]]] = {
    "rest_api": (
        "Callable REST endpoint",
        (r"\brest\b", r"\bapi endpoint\b", r"\bhttp endpoint\b"),
    ),
    "text_chat_agent": (
        "Hosted text/chat agent layer",
        (r"\btext agent\b", r"\bchat agent\b", r"\bchatbot\b", r"\bagent api\b"),
    ),
    "knowledge_base": (
        "Knowledge base / RAG context",
        (r"\bknowledge base\b", r"\brag\b", r"\bretrieval augmented\b"),
    ),
    "guardrails": (
        "Agent guardrails",
        (r"\bguardrails?\b", r"\bsafety rules?\b"),
    ),
    "per_client_configuration": (
        "Reusable per-client agent configuration",
        (
            r"\bper[- ](?:client|customer|tenant)\b",
            r"\bmulti[- ]tenant\b",
            r"\breusable (?:agent )?configuration\b",
        ),
    ),
    "agent_api_keys": (
        "Per-agent API keys and usage caps",
        (r"\bper[- ]agent api keys?\b", r"\busage caps?\b", r"\brate limits?\b"),
    ),
    "run_history_analytics": (
        "Agent run history and analytics",
        (r"\brun history\b", r"\bagent analytics\b", r"\busage analytics\b"),
    ),
    "byok": (
        "Bring your own model key",
        (r"\bbyok\b", r"\bbring your own (?:api )?key\b"),
    ),
    "voice_telephony": (
        "Voice and telephony runtime",
        (r"\bvoice agent\b", r"\btelephony\b", r"\bphone calls?\b", r"\bsip\b"),
    ),
    "full_saas_backend": (
        "Full SaaS backend replacement",
        (r"\bfull (?:saas )?backend\b", r"\breplace(?:s|ment)? your (?:entire )?backend\b"),
    ),
    "hipaa_compliance": (
        "HIPAA compliance",
        (r"\bhipaa\b",),
    ),
    "deep_vertical_integrations": (
        "Deep domain-specific operational integrations",
        (r"\bvertical integrations?\b", r"\bdomain[- ]specific integrations?\b"),
    ),
}


def normalize_code(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")


def derive_capability_profile(
    ledger: EvidenceLedger,
    *,
    knowledge_id: UUID,
    knowledge_version: int,
    previous: ProductCapabilityProfile | None = None,
) -> ProductCapabilityProfile:
    """Create a conservative deterministic profile from the current ledger.

    Only positively evidenced catalogue entries are introduced automatically.
    Unsupported and unknown boundaries are product truth supplied in an
    existing/user-maintained profile; absence of evidence never manufactures
    either state. When knowledge changes, the previous product-specific
    catalogue is revalidated and carried forward instead of being replaced by
    a universal catalogue.
    """
    capabilities: list[ProductCapability] = []
    for capability_id, (label, patterns) in _EVIDENCE_DERIVATION_HINTS.items():
        matched = [entry for entry in ledger.entries if _matches(entry, patterns)]
        if not matched:
            continue
        capabilities.append(
            ProductCapability(
                id=capability_id,
                label=label,
                description=label,
                state=CapabilityState.VERIFIED,
                evidence=[_capability_evidence(entry) for entry in matched],
                note="Verified by the current Evidence Ledger.",
            )
        )

    constraints: list[ScopeBoundary] = []
    if previous is not None:
        refreshed = normalize_capability_profile(
            CapabilityProfileDraft(
                capabilities=previous.capabilities,
                constraints=previous.constraints,
                claims=previous.claims,
            ),
            ledger=ledger,
            knowledge_id=knowledge_id,
            knowledge_version=knowledge_version,
            version=previous.version + 1,
        )
        by_capability_id = {item.id: item for item in refreshed.capabilities}
        for item in capabilities:
            by_capability_id.setdefault(item.id, item)
        capabilities = list(by_capability_id.values())
        constraints = refreshed.constraints

    claims = [
        ProductClaim(
            text=entry.claim,
            visibility=ClaimVisibility.CUSTOMER,
            evidence_ids=[entry.id],
            reason="Licensed by the current Evidence Ledger.",
        )
        for entry in ledger.entries
    ]
    claims.extend(
        ProductClaim(
            text=f"{item.label}: {item.state}.",
            visibility=ClaimVisibility.INTERNAL,
            reason=item.note,
        )
        for item in capabilities
        if item.state is not CapabilityState.VERIFIED
    )
    return ProductCapabilityProfile(
        knowledge_id=knowledge_id,
        knowledge_version=knowledge_version,
        ledger_fingerprint=capability_ledger_fingerprint(ledger),
        capabilities=capabilities,
        constraints=constraints,
        claims=claims,
    )


def normalize_capability_profile(
    draft: CapabilityProfileDraft | ProductCapabilityProfile,
    *,
    ledger: EvidenceLedger,
    knowledge_id: UUID,
    knowledge_version: int,
    version: int = 1,
) -> ProductCapabilityProfile:
    """Resolve positive support and customer claims against the current ledger."""
    by_id = {entry.id: entry for entry in ledger.entries}
    capabilities: list[ProductCapability] = []
    seen: set[str] = set()
    for proposed in draft.capabilities:
        capability_id = normalize_code(proposed.id)
        if not capability_id or capability_id in seen:
            continue
        seen.add(capability_id)
        evidence_ids = [
            item.evidence_id
            for item in proposed.evidence
            if item.evidence_id in by_id
        ]
        evidence = [_capability_evidence(by_id[item]) for item in dict.fromkeys(evidence_ids)]
        state = proposed.state
        if state is CapabilityState.VERIFIED and not evidence:
            state = CapabilityState.UNKNOWN
        capabilities.append(
            ProductCapability(
                id=capability_id,
                label=proposed.label.strip() or capability_id.replace("_", " ").title(),
                description=proposed.description.strip(),
                state=state,
                evidence=evidence,
                aliases=list(
                    dict.fromkeys(
                        alias.strip() for alias in proposed.aliases if alias.strip()
                    )
                ),
                customer_copy_visibility=proposed.customer_copy_visibility,
                note=proposed.note.strip(),
            )
        )

    claims: list[ProductClaim] = []
    for claim in draft.claims:
        evidence_ids = [item for item in dict.fromkeys(claim.evidence_ids) if item in by_id]
        if claim.visibility is ClaimVisibility.CUSTOMER and not evidence_ids:
            continue
        if not claim.text.strip():
            continue
        claims.append(claim.model_copy(update={"evidence_ids": evidence_ids}))

    return ProductCapabilityProfile(
        version=version,
        knowledge_id=knowledge_id,
        knowledge_version=knowledge_version,
        ledger_fingerprint=capability_ledger_fingerprint(ledger),
        capabilities=capabilities,
        constraints=[item for item in draft.constraints if item.statement.strip()],
        claims=claims,
    )


def capability_ledger_fingerprint(ledger: EvidenceLedger) -> str:
    payload = [
        {
            "id": item.id,
            "claim": item.claim,
            "verbatim": item.verbatim,
            "source": item.source,
            "document_id": item.document_id,
        }
        for item in ledger.entries
    ]
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _matches(entry: Evidence, patterns: tuple[str, ...]) -> bool:
    text = f"{entry.claim}\n{entry.verbatim}".casefold()
    return any(re.search(pattern, text) for pattern in patterns)


def _capability_evidence(entry: Evidence) -> CapabilityEvidence:
    return CapabilityEvidence(
        evidence_id=entry.id,
        claim=entry.claim,
        quote=entry.verbatim,
        source_identifier=entry.source or entry.document_id or "",
    )
