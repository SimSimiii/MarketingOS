"""What the market API sends to the client.

Read models, not the domain models. The positioning map is deliberately
flattened here: the client renders territories as columns and needs each
reading with its rivals attached, and shipping the internal `ClaimSet` would
make the page's shape depend on how claims happen to be stored.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.knowledge.artifacts import Sophistication
from app.market.audience_research import AudienceResearch
from app.market.capabilities import CapabilityProfileDraft, ProductCapabilityProfile
from app.market.claims import Claim
from app.market.demand import (
    AudienceAdmission,
    AudienceSegment,
    DemandMap,
    MapAssessment,
    MapOptions,
    Researchability,
    SegmentKind,
)
from app.market.positioning import PositioningMap
from app.market.qualification import CompanyQualification
from app.market.radar import MarketSnapshot
from app.market.relevance import RelevanceStatus
from app.market.rivals import RivalProfile
from app.market.store import prospect_contacts, prospect_qualification
from app.models.market import (
    AudienceResearchRow,
    ProductCapabilityProfileRow,
    ProofCandidateRow,
    ProspectRow,
    RadarEventRow,
    Rival,
)


class RivalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    url: str
    kind: str
    why: str
    added_by: str
    muted: bool
    created_at: datetime


class RivalCreate(BaseModel):
    name: str
    url: str = ""
    kind: str = "alternative"
    why: str = ""


class RivalMuteUpdate(BaseModel):
    muted: bool


class ClaimRead(BaseModel):
    text: str
    verbatim: str = ""
    source: str = ""
    axis: str
    specific: bool

    @classmethod
    def of(cls, claim: Claim) -> "ClaimRead":
        return cls(
            text=claim.text,
            verbatim=claim.verbatim,
            source=claim.source,
            axis=str(claim.axis),
            specific=claim.is_specific,
        )


class RivalProfileRead(BaseModel):
    name: str
    url: str
    kind: str
    why: str
    one_liner: str
    promise: str
    pricing: str
    free_entry: str
    icp: str
    verified: bool
    pages_read: int
    unverified_claims: int
    note: str
    checked_at: datetime
    claims: list[ClaimRead] = Field(default_factory=list)
    proof_shown: list[ClaimRead] = Field(default_factory=list)

    @classmethod
    def of(cls, profile: RivalProfile) -> "RivalProfileRead":
        return cls(
            name=profile.name,
            url=profile.url,
            kind=profile.kind,
            why=profile.why,
            one_liner=profile.one_liner,
            promise=profile.promise,
            pricing=profile.pricing,
            free_entry=profile.free_entry,
            icp=profile.icp,
            verified=profile.verified,
            pages_read=profile.pages_read,
            unverified_claims=profile.unverified_claims,
            note=profile.note,
            checked_at=profile.checked_at,
            claims=[ClaimRead.of(claim) for claim in profile.claims.claims],
            proof_shown=[ClaimRead.of(claim) for claim in profile.proof_shown],
        )


class AxisReadingRead(BaseModel):
    axis: str
    territory: str
    only_specific: bool
    ours: list[ClaimRead] = Field(default_factory=list)
    #: Rival name -> what they claim on this axis.
    theirs: dict[str, list[ClaimRead]] = Field(default_factory=dict)


class PositioningRead(BaseModel):
    summary: str
    rivals_profiled: int
    rivals_with_proof: int
    we_have_proof: bool
    proof_deficit: bool
    crowd_words: list[str] = Field(default_factory=list)
    readings: list[AxisReadingRead] = Field(default_factory=list)
    #: The section the strategist is planned against, rendered. Shown to the
    #: user verbatim rather than paraphrased in the UI: the point of the page
    #: is that they can read what the machine was told, and a second wording
    #: of it is a second thing to keep in sync.
    brief_for_strategy: str = ""

    @classmethod
    def of(cls, positioning: PositioningMap) -> "PositioningRead":
        return cls(
            summary=positioning.summary(),
            rivals_profiled=positioning.rivals_profiled,
            rivals_with_proof=positioning.rivals_with_proof,
            we_have_proof=positioning.we_have_proof,
            proof_deficit=positioning.proof_deficit,
            crowd_words=positioning.crowd_words[:40],
            readings=[
                AxisReadingRead(
                    axis=str(reading.axis),
                    territory=str(reading.territory),
                    only_specific=reading.only_specific,
                    ours=[ClaimRead.of(claim) for claim in reading.ours],
                    theirs={
                        name: [ClaimRead.of(claim) for claim in claims]
                        for name, claims in reading.theirs.items()
                    },
                )
                for reading in positioning.readings
            ],
            brief_for_strategy=positioning.render_for_strategy(),
        )


class MarketRead(BaseModel):
    """Everything one page needs about a brand's market."""

    brand_id: UUID
    scanned_at: datetime | None = None
    positioning: PositioningRead | None = None
    profiles: list[RivalProfileRead] = Field(default_factory=list)
    rivals: list[RivalRead] = Field(default_factory=list)
    pending_proof: int = 0
    unseen_alerts: int = 0
    #: How much of the demand side exists, for a nav that has to badge a tab
    #: without fetching the map itself. Counts, not payloads - the audience
    #: page fetches its own.
    audience_segments: int = 0
    prospects: int = 0
    #: Why the page is empty, when it is. A blank market page with no
    #: explanation reads as a broken feature; "nobody has scanned this yet"
    #: reads as a button to press.
    note: str = ""

    @classmethod
    def of(
        cls,
        brand_id: UUID,
        snapshot: MarketSnapshot | None,
        rivals: list[Rival],
        pending_proof: int,
        unseen_alerts: int,
        audience_segments: int = 0,
        prospects: int = 0,
        note: str = "",
    ) -> "MarketRead":
        return cls(
            brand_id=brand_id,
            scanned_at=snapshot.taken_at if snapshot else None,
            positioning=(
                PositioningRead.of(snapshot.positioning) if snapshot else None
            ),
            profiles=[RivalProfileRead.of(profile) for profile in snapshot.rivals]
            if snapshot
            else [],
            rivals=[RivalRead.model_validate(rival) for rival in rivals],
            pending_proof=pending_proof,
            unseen_alerts=unseen_alerts,
            audience_segments=audience_segments,
            prospects=prospects,
            note=note,
        )


class ProofCandidateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    kind: str
    claim: str
    verbatim: str
    url: str
    attributed_to: str
    venue: str
    confidence: float
    caveat: str
    status: str
    evidence_id: str
    found_at: datetime
    decided_at: datetime | None


class ProofDecision(BaseModel):
    approved: bool


class RadarEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    headline: str
    detail: str
    severity: str
    rival: str
    axis: str
    what_to_do: str
    created_at: datetime
    seen_at: datetime | None


class JobStatusRead(BaseModel):
    kind: str
    state: str
    message: str
    log: list[str] = Field(default_factory=list)
    started_at: datetime
    finished_at: datetime | None = None
    error: str = ""
    summary: str = ""
    found: int = 0
    #: Whose market this is. Present so a board of every running job can name
    #: and link each one without a brand lookup per row.
    brand_id: UUID | None = None
    brand_name: str = ""
    #: What this job has spent. Cached input is counted into `input_tokens` -
    #: it is what the quota paid for.
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cost_usd: float = 0.0


class ScanRequest(BaseModel):
    #: Whether to search the web for competitors nobody has named yet. Off
    #: re-reads the existing list only, which is what a weekly refresh wants.
    discover: bool = True




# ------------------------------------------------------------------ demand


class AudienceSegmentRead(BaseModel):
    """One mapped buyer, as the audience page shows it."""

    name: str
    organization: str = ""
    workflow: str = ""
    need: str = ""
    buyer_role: str = ""
    user_role: str = ""
    current_alternative: str = ""
    assessment: MapAssessment = Field(default_factory=MapAssessment)
    kind: str
    #: `cartographer` or `user`. The page badges the second, because an
    #: audience somebody typed and an audience the open web produced are
    #: different claims - and only one of them is editable here.
    added_by: str = "cartographer"
    who: str
    why_them: str
    trigger: str
    pains: list[str] = Field(default_factory=list)
    objection: str
    angle: str
    sophistication: str
    #: Legacy payload field, no longer displayed or used in ranking.
    fit: float
    basis: str
    population: str
    signals: list[str] = Field(default_factory=list)
    where: list[str] = Field(default_factory=list)
    #: Whether this is a buyer the brand's own material would never have
    #: produced. A property on the domain model, and therefore not serialized
    #: for free - it is carried explicitly because it is the one flag the page
    #: sorts and filters by.
    unobvious: bool = False
    researchable: bool = False
    researchability: Researchability = Researchability.UNRESEARCHABLE
    researchability_reasons: list[str] = Field(default_factory=list)
    definition: dict = Field(default_factory=dict)

    @classmethod
    def of(
        cls,
        segment: AudienceSegment,
        admission: AudienceAdmission | None = None,
    ) -> "AudienceSegmentRead":
        admission = admission or segment.admission()
        return cls(
            name=segment.name,
            organization=segment.organization,
            workflow=segment.workflow,
            need=segment.need,
            buyer_role=segment.buyer_role,
            user_role=segment.user_role,
            current_alternative=segment.current_alternative,
            assessment=segment.assessment,
            kind=str(segment.kind),
            added_by=segment.added_by,
            who=segment.who,
            why_them=segment.why_them,
            trigger=segment.trigger,
            pains=list(segment.pains),
            objection=segment.objection,
            angle=segment.angle,
            sophistication=str(segment.sophistication),
            fit=segment.fit,
            basis=segment.basis,
            population=segment.population,
            signals=list(segment.signals),
            where=list(segment.where),
            unobvious=segment.unobvious,
            researchable=admission.researchable,
            researchability=admission.researchability,
            researchability_reasons=list(admission.reasons),
            definition=segment.definition.model_dump(mode="json"),
        )


class DemandMapRead(BaseModel):
    summary: str
    options: MapOptions = Field(default_factory=MapOptions)
    validation_note: str = ""
    reading: str = ""
    note: str = ""
    searched: list[str] = Field(default_factory=list)
    mapped_at: datetime
    segments: list[AudienceSegmentRead] = Field(default_factory=list)

    @classmethod
    def of(cls, demand: DemandMap) -> "DemandMapRead":
        return cls(
            summary=demand.summary(),
            options=demand.options,
            validation_note=demand.validation_note,
            reading=demand.reading,
            note=demand.note,
            searched=demand.searched[:12],
            mapped_at=demand.mapped_at,
            # Validated priorities first, then researchability; stable ties.
            segments=[
                AudienceSegmentRead.of(item, demand.admission_for(item))
                for item in demand.ranked
            ],
        )


class ContactRead(BaseModel):
    kind: str
    value: str
    label: str
    source: str
    #: Always true in anything that reaches the client. Unverified contacts
    #: are dropped, never shipped marked - see `demand._verify_contacts`. The
    #: field is carried anyway so the page can say *why* it is safe to paste
    #: these into a mail merge.
    verified: bool


class ProspectRead(BaseModel):
    id: UUID
    segment: str
    name: str
    url: str
    what_they_do: str
    why_them: str
    verbatim: str
    #: The legacy propensity estimate. V2 deliberately withholds it for an
    #: unreadable company: "unverified" is not a low score, and displaying a
    #: percentage there would manufacture precision from missing evidence.
    fit: float | None
    caveat: str
    verified: bool
    pages_read: int
    #: How many contact details the extractor reported that were nowhere on
    #: their site. Shown, because a row that had to discard three is a row
    #: whose other claims deserve the same suspicion.
    invented_contacts: int
    note: str
    status: str
    found_at: datetime
    decided_at: datetime | None
    contacts: list[ContactRead] = Field(default_factory=list)
    qualification: dict | None = None

    @classmethod
    def of(
        cls,
        row: ProspectRow,
        *,
        qualification: CompanyQualification | None = None,
    ) -> "ProspectRead":
        qualification = qualification or prospect_qualification(row)
        return cls(
            id=row.id,
            segment=row.segment,
            name=row.name,
            url=row.url,
            what_they_do=row.what_they_do,
            why_them=row.why_them,
            verbatim=row.verbatim,
            # V2 replaces the blended percentage with categorical dimensions.
            # The numeric value survives only for legacy rows so old stored
            # prospects remain readable without presenting it as new truth.
            fit=None if qualification is not None else row.fit,
            caveat=row.caveat,
            verified=row.verified,
            pages_read=row.pages_read,
            invented_contacts=row.invented_contacts,
            note=row.note,
            status=row.status,
            found_at=row.found_at,
            decided_at=row.decided_at,
            contacts=[
                ContactRead(
                    kind=str(contact.kind),
                    value=contact.value,
                    label=contact.label,
                    source=contact.source,
                    verified=contact.verified,
                )
                for contact in prospect_contacts(row)
            ],
            qualification=(
                qualification.model_dump(mode="json")
                if qualification is not None
                else None
            ),
        )


class CapabilityProfileRead(ProductCapabilityProfile):
    id: UUID
    brand_id: UUID
    created_at: datetime

    @classmethod
    def of(cls, row: ProductCapabilityProfileRow) -> "CapabilityProfileRead":
        return cls.model_validate(
            {
                **row.payload,
                "id": row.id,
                "brand_id": row.brand_id,
                "version": row.version,
                "created_at": row.created_at,
            }
        )


class AudienceResearchRead(AudienceResearch):
    """A verified research payload plus its persistence receipt."""

    id: UUID
    brand_id: UUID
    audience_key: str
    version: int
    source_map_id: UUID | None = None
    source_map_version: int | None = None
    created_at: datetime

    @classmethod
    def of(cls, row: AudienceResearchRow) -> "AudienceResearchRead":
        return cls.model_validate(
            {
                **row.payload,
                "id": row.id,
                "brand_id": row.brand_id,
                "audience_key": row.audience_key,
                "version": row.version,
                "source_map_id": row.source_map_id,
                "source_map_version": row.source_map_version,
                "created_at": row.created_at,
            }
        )


class AudienceRead(BaseModel):
    """Everything the audience page shows, in one request."""

    brand_id: UUID
    map: DemandMapRead | None = None
    prospects: list[ProspectRead] = Field(default_factory=list)
    research: list[AudienceResearchRead] = Field(default_factory=list)
    relevance: list[RelevanceStatus] = Field(default_factory=list)
    capability_profile: CapabilityProfileRead | None = None
    #: Why the page is empty, when it is.
    note: str = ""


class MapAudienceRequest(MapOptions):
    """Optional search scope; an empty body keeps the one-click workflow."""


class UserAudienceRequest(BaseModel):
    """One audience the user is describing themselves.

    Four required lines, and they are four rather than one because they are
    exactly what `AudienceSegment.admission` reads as a situation: who they
    are, what they are doing when the problem bites, and what they need to
    change. A free-text paragraph would be kinder to type and would leave the
    admission check nothing to hold on to.

    `signals` and `where` are what research actually spends its search on, and
    they are optional here on purpose. An audience saved without them is not
    researchable, the deterministic receipt says so in the same words it uses
    for a mapped one, and the user can come back and finish it - which beats a
    form that refuses to save half an idea.

    Nothing else is required. Everything below `where` is the detail that makes
    a campaign to this buyer read differently from a campaign to any other, and
    all of it can be added later.
    """

    name: str = Field(min_length=1, max_length=120)
    #: The kind of organisation or person. "Three-person Shopify stores
    #: selling refurbished laptops", not "e-commerce".
    organization: str = Field(min_length=1, max_length=400)
    #: What they are doing when this matters. "Answering warranty questions by
    #: hand out of a shared inbox".
    workflow: str = Field(min_length=1, max_length=400)
    #: What they need to change about it.
    need: str = Field(min_length=1, max_length=400)
    #: How you would recognise one from the outside, without asking them.
    signals: list[str] = Field(default_factory=list, max_length=10)
    #: Named places they are findable in bulk. A directory, a register, an
    #: exhibitor list - "LinkedIn" on its own is refused by admission.
    where: list[str] = Field(default_factory=list, max_length=10)

    kind: SegmentKind = SegmentKind.CORE
    sophistication: Sophistication = Sophistication.PROBLEM_AWARE
    who: str = Field(default="", max_length=600)
    why_them: str = Field(default="", max_length=600)
    trigger: str = Field(default="", max_length=400)
    pains: list[str] = Field(default_factory=list, max_length=10)
    objection: str = Field(default="", max_length=600)
    angle: str = Field(default="", max_length=600)
    population: str = Field(default="", max_length=200)
    buyer_role: str = Field(default="", max_length=200)
    user_role: str = Field(default="", max_length=200)
    current_alternative: str = Field(default="", max_length=400)

    @field_validator("*", mode="before")
    @classmethod
    def _tidy(cls, value: object) -> object:
        """Tidy before the length rules, not after.

        `mode="after"` would let a name of three spaces satisfy `min_length`
        and then be stripped to nothing on the way out - stored, unfindable,
        and reported as a conflict rather than as the empty field it is.
        Blank list entries are typing rather than content for the same reason:
        admission counts signals, and a blank one would count.
        """
        if isinstance(value, str):
            return " ".join(value.split())
        if isinstance(value, list):
            return [" ".join(str(item).split()) for item in value if str(item).strip()]
        return value

    def as_segment(self) -> AudienceSegment:
        """The draft as the one segment shape the whole pipeline already reads.

        `definition` is left empty and that is honest rather than lazy: it is
        the machine-readable qualification contract, an empty one is
        deliberately insufficient to call a company QUALIFIED, and inventing
        requirement codes out of prose would make a hand-written audience look
        more checkable than it is.
        """
        return AudienceSegment(
            **self.model_dump(exclude={"sophistication", "kind"}),
            kind=self.kind,
            sophistication=self.sophistication,
            added_by="user",
        )


class ResearchAudienceRequest(BaseModel):
    segment: str = Field(min_length=1)


class RelevanceDossierRequest(BaseModel):
    segment: str = Field(min_length=1)


class CapabilityProfileRequest(CapabilityProfileDraft):
    """Editable product truth; evidence ids are validated before persistence."""


class ProspectSearchRequest(BaseModel):
    #: Which mapped segment to fill. Required: a prospect list that is not for
    #: a particular buyer is a list nobody can write one email to.
    segment: str
    limit: int = Field(default=10, ge=1, le=25)
    #: Whether to read each organisation's own pages for a published way in.
    #: Off returns names only and costs one call instead of one per company -
    #: which is what somebody testing whether a segment is real wants, as
    #: against somebody sending mail on Monday.
    with_contacts: bool = True


class ProspectDecision(BaseModel):
    #: `kept` or `dismissed`.
    status: str


def prospect_reads(
    rows: list[ProspectRow],
    qualifications: dict[UUID, CompanyQualification] | None = None,
) -> list[ProspectRead]:
    return [
        ProspectRead.of(
            row,
            qualification=(qualifications or {}).get(row.id),
        )
        for row in rows
    ]


def proof_reads(rows: list[ProofCandidateRow]) -> list[ProofCandidateRead]:
    return [ProofCandidateRead.model_validate(row) for row in rows]


def radar_reads(rows: list[RadarEventRow]) -> list[RadarEventRead]:
    return [RadarEventRead.model_validate(row) for row in rows]
