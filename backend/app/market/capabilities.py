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

from app.knowledge.corpus import fold
from app.knowledge.ledger import Evidence, EvidenceKind, EvidenceLedger, category_of
from app.knowledge.product_scope import is_product_subject
from app.knowledge.taxonomy import FactCategory

DERIVATION_VERSION = 3


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
    #: Ledger entries that were attached to this capability and do not mention
    #: it. Recorded rather than dropped in silence, because "nobody attached
    #: evidence" and "the evidence attached was about something else" are the
    #: two readings of an empty list, and only the second is a mistake somebody
    #: needs to go and fix. Recomputed on every normalisation; never input.
    unlicensed_evidence_ids: list[str] = Field(default_factory=list)
    origin: str = "maintained"


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
    derivation_version: int = 0
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

    def discovery_context(self) -> dict:
        """Product-specific catalogue, without duplicating the whole claim ledger."""
        return {"capabilities": [
                    {"id": item.id, "label": item.label, "state": str(item.state),
                     **({"scope": item.description} if item.description else {}),
                     **({"aliases": item.aliases} if item.aliases else {}),
                     **({"note": item.note} if item.state is not CapabilityState.VERIFIED else {})}
                    for item in self.capabilities],
                "constraints": [item.model_dump(mode="json") for item in self.constraints]}

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
        (r"\bper[- ]agent api keys?\b", r"\bagent (?:usage caps?|rate limits?)\b"),
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


#: Words that describe every capability in a catalogue and therefore identify
#: none of them. They are dropped when a capability outside the derivation
#: hints has to license evidence from its own vocabulary: on this product's own
#: ledger, "agent" alone appears in most entries, so allowing it would license
#: the whole ledger for any capability whose label contains the word.
_GENERIC_TERMS = frozenset(
    {
        "agent", "agents", "api", "apis", "app", "apps", "automatic", "based",
        "built", "custom", "data", "deep", "feature", "features", "full",
        "hosted", "layer", "level", "managed", "native", "platform", "product",
        "products", "provider", "runtime", "saas", "service", "services",
        "support", "supported", "system", "tool", "tools", "user", "users",
        "your",
    }
)

#: Appended to a capability's note when filtering emptied its evidence. Fixed
#: text so re-normalising an already-demoted capability cannot stack copies.
UNLICENSED_NOTE = (
    "Demoted to unknown: attached quotations do not establish current capability support."
)


def capability_patterns(capability: ProductCapability) -> tuple[str, ...]:
    """What a ledger entry has to say for it to license this capability.

    Curated patterns win where the catalogue has them, because they carry the
    vocabulary a reader would actually use - `rag` and `retrieval augmented`
    for a knowledge base, which share no words with the label. A catalogue
    entry this product invented has no curated pattern, so it licenses from its
    own words instead: the label and aliases the user wrote are the only
    statement of what the capability means, and `aliases` exists precisely to
    carry the customer's vocabulary for it.
    """
    hint = _EVIDENCE_DERIVATION_HINTS.get(normalize_code(capability.id))
    if hint is not None:
        aliases = tuple(rf"\b{re.escape(fold(alias))}\b" for alias in capability.aliases if alias.strip())
        return (*hint[1], *aliases)
    terms: list[str] = []
    for phrase in (capability.label, capability.id.replace("_", " "), *capability.aliases):
        cleaned = re.sub(r"[^a-z0-9]+", " ", phrase.casefold()).strip()
        if not cleaned:
            continue
        if " " in cleaned or (len(cleaned) > 3 and cleaned not in _GENERIC_TERMS):
            terms.append(cleaned)
    return tuple(rf"\b{re.escape(term)}\b" for term in dict.fromkeys(terms))


def licenses(entry: Evidence, capability: ProductCapability, *, company_name: str = "") -> bool:
    """Whether this ledger fact is about this capability at all.

    The check the editor never had. A capability's state decides whether a
    prospect is qualified or excluded and whether an audience is compatible,
    and until this existed the only thing standing behind `verified` was that
    the attached evidence id existed somewhere in the ledger - so a fact about
    uptime could license guardrails, and did.
    """
    if capability.id.startswith("fact_"):
        return (capability.id == _fact_id(entry) and capability.label == entry.claim
                and _product_fact(entry, company_name=company_name))
    if entry.context and entry.context.source_kind in {"third_party", "vendor_comparison"}:
        return False
    if category_of(entry) in {FactCategory.COMPANY, FactCategory.MARKET, FactCategory.BRAND,
                              FactCategory.PROOF, FactCategory.COMMERCIAL}:
        return False
    if entry.context and (
        entry.context.claim_scope not in {"", "unknown", "capability"}
        or (company_name and entry.context.subject
            and not is_product_subject(entry.context.subject, company_name))
    ):
        return False
    return _matches(entry, capability_patterns(capability))


def _fact_id(entry: Evidence) -> str:
    identity = f"{fold(entry.claim)}\n{fold(entry.verbatim)}"
    return "fact_" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]


def _product_fact(entry: Evidence, *, company_name: str = "") -> bool:
    """Retain the actual scoped fact; never generalise a keyword into a feature."""
    if entry.kind not in {EvidenceKind.FEATURE, EvidenceKind.GUARANTEE, EvidenceKind.INTEGRATION}:
        return False
    context = entry.context
    if (context is None or context.claim_scope != "capability" or not context.subject.strip()
            or context.source_kind in {"third_party", "vendor_comparison", "customer_statement"}
            or category_of(entry) in {FactCategory.COMPANY, FactCategory.MARKET,
                                      FactCategory.BRAND, FactCategory.PROOF,
                                      FactCategory.COMMERCIAL}):
        return False
    # A mention of our product inside a third party's workflow does not
    # establish that we own that workflow. The asserted subject must be ours.
    if company_name and not is_product_subject(context.subject, company_name):
        return False
    return len(fold(entry.verbatim)) >= 12 and not re.search(
        r"\b(?:not supported|unsupported|not available|does not support|do not support|"
        r"coming soon|roadmap|planned)\b", fold(entry.verbatim)
    )


def normalize_code(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")


def derive_capability_profile(
    ledger: EvidenceLedger,
    *,
    knowledge_id: UUID,
    knowledge_version: int,
    previous: ProductCapabilityProfile | None = None,
    company_name: str = "",
) -> ProductCapabilityProfile:
    """Create a conservative deterministic profile from the current ledger.

    Each derived entry preserves one product-specific ledger assertion and its
    scope. Domain vocabulary is used only to validate maintained legacy IDs,
    never to turn a keyword match into a broader capability automatically.
    Unsupported and unknown boundaries are product truth supplied in an
    existing/user-maintained profile; absence of evidence never manufactures
    either state. When knowledge changes, the previous product-specific
    catalogue is revalidated and carried forward instead of being replaced by
    a universal catalogue.
    """
    capabilities: list[ProductCapability] = []
    seen: set[str] = set()
    for entry in ledger.entries:
        if not _product_fact(entry, company_name=company_name) or _fact_id(entry) in seen:
            continue
        seen.add(_fact_id(entry))
        scope = entry.context
        context = "; ".join(filter(None, (
            f"Source: {scope.source_kind}" if scope else "Scope not documented.",
            f"Subject: {scope.subject}" if scope and scope.subject else "",
            scope.conditions if scope else "", scope.temporal_scope if scope else "",
            scope.limitations if scope else "",
        )))
        capabilities.append(
            ProductCapability(
                id=_fact_id(entry),
                label=entry.claim,
                description=context,
                state=CapabilityState.VERIFIED,
                evidence=[_capability_evidence(entry)],
                note="Atomic product fact from the current Evidence Ledger; preserve its scope.",
                origin="derived",
            )
        )

    constraints: list[ScopeBoundary] = []
    if previous is not None:
        refreshed = normalize_capability_profile(
            CapabilityProfileDraft(
                capabilities=[item for item in previous.capabilities if item.origin != "derived"
                              and not (previous.derivation_version == 0
                                       and item.state != CapabilityState.UNSUPPORTED
                                       and item.id in _EVIDENCE_DERIVATION_HINTS
                                       and item.note.replace(UNLICENSED_NOTE, "").strip()
                                       == "Verified by the current Evidence Ledger.")],
                constraints=previous.constraints,
                claims=previous.claims,
            ),
            ledger=ledger,
            knowledge_id=knowledge_id,
            knowledge_version=knowledge_version,
            version=previous.version + 1,
            company_name=company_name,
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
        derivation_version=DERIVATION_VERSION,
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
    company_name: str = "",
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
        evidence_ids = [item.evidence_id for item in proposed.evidence]
        # Two separate questions, and only the first was ever asked here: does
        # this evidence id exist, and does that fact say anything about this
        # capability. An entry that fails the second is kept visible rather
        # than dropped, so an editor can see what was rejected and why.
        licensed: list[str] = []
        unlicensed: list[str] = list(proposed.unlicensed_evidence_ids)
        for item in dict.fromkeys(evidence_ids):
            target = licensed if item in by_id and licenses(
                by_id[item], proposed, company_name=company_name
            ) else unlicensed
            target.append(item)
        unlicensed = [item for item in dict.fromkeys(unlicensed) if item not in licensed]
        evidence = [_capability_evidence(by_id[item]) for item in licensed]
        state = proposed.state
        note = proposed.note.replace(UNLICENSED_NOTE, "").strip()
        if state is CapabilityState.VERIFIED and not evidence:
            state = CapabilityState.UNKNOWN
        if state is CapabilityState.UNKNOWN and not evidence and unlicensed:
            note = f"{note} {UNLICENSED_NOTE}".strip()
        capabilities.append(
            ProductCapability(
                id=capability_id,
                label=proposed.label.strip() or capability_id.replace("_", " ").title(),
                description=proposed.description.strip(),
                state=state,
                evidence=evidence,
                unlicensed_evidence_ids=unlicensed,
                aliases=list(
                    dict.fromkeys(
                        alias.strip() for alias in proposed.aliases if alias.strip()
                    )
                ),
                customer_copy_visibility=proposed.customer_copy_visibility,
                note=note,
                origin=proposed.origin,
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
        derivation_version=getattr(draft, "derivation_version", DERIVATION_VERSION),
        capabilities=capabilities,
        constraints=[item for item in draft.constraints if item.statement.strip()],
        claims=claims,
    )


def capability_ledger_fingerprint(ledger: EvidenceLedger) -> str:
    payload = [
        {
            "id": item.id,
            "kind": str(item.kind),
            "claim": item.claim,
            "verbatim": item.verbatim,
            "source": item.source,
            "document_id": item.document_id,
            "context": item.context.model_dump(mode="json") if item.context else None,
            "source_references": item.source_references,
        }
        for item in sorted(ledger.entries, key=lambda item: item.id)
    ]
    encoded = json.dumps({"derivation": DERIVATION_VERSION, "ledger": payload},
                         ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _matches(entry: Evidence, patterns: tuple[str, ...]) -> bool:
    # A paraphrase mentioning a capability cannot license an unrelated quote.
    text = fold(entry.verbatim)
    for sentence in re.split(r"[.!?;\n]", text):
        if not any(re.search(pattern, sentence) for pattern in patterns):
            continue
        if re.search(
            r"\b(?:not supported|unsupported|not available|does not support|do not support|"
            r"no support for|planned|coming soon|roadmap|"
            r"ne .{0,35} pas|non disponible|non pris en charge)\b", sentence,
        ):
            continue
        for pattern in patterns:
            for match in re.finditer(pattern, sentence):
                if not re.search(r"\b(?:no|without|lacks?)\s+(?:any\s+)?$", sentence[:match.start()]):
                    return True
    return False


def _capability_evidence(entry: Evidence) -> CapabilityEvidence:
    return CapabilityEvidence(
        evidence_id=entry.id,
        claim=entry.claim,
        quote=entry.verbatim,
        source_identifier=entry.source or entry.document_id or "",
    )
