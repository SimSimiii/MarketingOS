"""What the market API sends to the client.

Read models, not the domain models. The positioning map is deliberately
flattened here: the client renders territories as columns and needs each
reading with its rivals attached, and shipping the internal `ClaimSet` would
make the page's shape depend on how claims happen to be stored.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.market.claims import Claim
from app.market.demand import AudienceSegment, DemandMap
from app.market.positioning import PositioningMap
from app.market.radar import MarketSnapshot
from app.market.rivals import RivalProfile
from app.market.store import prospect_contacts
from app.models.market import ProofCandidateRow, ProspectRow, RadarEventRow, Rival


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
    kind: str
    who: str
    why_them: str
    trigger: str
    pains: list[str] = Field(default_factory=list)
    objection: str
    angle: str
    sophistication: str
    #: An estimate, and rendered as one everywhere. See
    #: `app.market.demand.AudienceSegment.fit`: nobody has sent these emails,
    #: so a rate shipped without `basis` beside it is a number the user can
    #: only over-trust or ignore.
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

    @classmethod
    def of(cls, segment: AudienceSegment) -> "AudienceSegmentRead":
        return cls(
            name=segment.name,
            kind=str(segment.kind),
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
        )


class DemandMapRead(BaseModel):
    summary: str
    reading: str = ""
    note: str = ""
    searched: list[str] = Field(default_factory=list)
    mapped_at: datetime
    segments: list[AudienceSegmentRead] = Field(default_factory=list)

    @classmethod
    def of(cls, demand: DemandMap) -> "DemandMapRead":
        return cls(
            summary=demand.summary(),
            reading=demand.reading,
            note=demand.note,
            searched=demand.searched[:12],
            mapped_at=demand.mapped_at,
            # Best fit first. The order is the recommendation, and re-sorting
            # it in the client would be a second place that decides which
            # segment the user reads first.
            segments=[AudienceSegmentRead.of(item) for item in demand.ranked],
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
    fit: float
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

    @classmethod
    def of(cls, row: ProspectRow) -> "ProspectRead":
        return cls(
            id=row.id,
            segment=row.segment,
            name=row.name,
            url=row.url,
            what_they_do=row.what_they_do,
            why_them=row.why_them,
            verbatim=row.verbatim,
            fit=row.fit,
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
        )


class AudienceRead(BaseModel):
    """Everything the audience page shows, in one request."""

    brand_id: UUID
    map: DemandMapRead | None = None
    prospects: list[ProspectRead] = Field(default_factory=list)
    #: Why the page is empty, when it is.
    note: str = ""


class MapAudienceRequest(BaseModel):
    """Nothing to configure yet, and the shape exists so there is somewhere to
    put the first thing that is - a body added later does not change the
    method or the client call."""


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


def prospect_reads(rows: list[ProspectRow]) -> list[ProspectRead]:
    return [ProspectRead.of(row) for row in rows]


def proof_reads(rows: list[ProofCandidateRow]) -> list[ProofCandidateRead]:
    return [ProofCandidateRead.model_validate(row) for row in rows]


def radar_reads(rows: list[RadarEventRow]) -> list[RadarEventRead]:
    return [RadarEventRead.model_validate(row) for row in rows]
