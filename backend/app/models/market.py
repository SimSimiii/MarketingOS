"""Where market intelligence lives between runs.

Six tables, and the split between them is the important part: they have
different lifetimes and different owners, and folding them into one payload
would break whichever one is inconvenient that week.

A **rival** is edited by the user. They add the competitor the scout missed
and mute the one that is not really a competitor, and those decisions must
survive every rescan - so the list is rows, not part of a compiled blob.

A **scan** is a compiled reading of the whole market at one moment. Versioned
and never overwritten, exactly like `KnowledgeArtifactSet`, because the radar's
entire product is the difference between two of them and a store that keeps
only the latest cannot produce one.

A **proof candidate** is a decision waiting for a human, and then a decision
that was made. It outlives every scan and every recompile: a user who approved
a customer quotation in March must not have to approve it again because they
uploaded a new pricing page in April.

A **radar event** is a fact about what changed. Kept rather than recomputed
because the diff that produced it compared two snapshots that may since have
been superseded, and a feed that silently rewrites its own history is worse
than no feed.

An **audience map** is a compiled reading of who would buy this, versioned for
the same reason a scan is: the useful question a month from now is which
segments the market added and which the map dropped, and only a store that
keeps both can answer it.

A **prospect** is a named organisation, and it is rows rather than part of the
map because the user works on it. They dismiss the one that is obviously too
big and keep the eleven they will write to on Monday, and those decisions must
survive the next search - a list that re-offers a dismissed company is a list
somebody stops reading.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class Rival(SQLModel, table=True):
    """One competitor on a brand's list, however it got there."""

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    brand_id: UUID = Field(foreign_key="brand.id", index=True)
    name: str
    url: str = ""
    #: `alternative`, `incumbent` or `status_quo` - see prompts/rival_scan.md.
    kind: str = "alternative"
    why: str = ""
    #: `user` or `scout`. Shown in the UI, because "we found this" and "you
    #: told us this" are different claims and the user should know which they
    #: are looking at.
    added_by: str = "scout"
    #: A competitor the user does not accept as one. Kept rather than deleted:
    #: the scout would only find it again on the next scan, and a mute is a
    #: decision the user should not have to make twice.
    muted: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class MarketScan(SQLModel, table=True):
    """One compiled reading of a brand's competitive position."""

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    brand_id: UUID = Field(foreign_key="brand.id", index=True)
    version: int = 1
    #: Serialized app.market.radar.MarketSnapshot - the rival profiles and the
    #: positioning map computed from them.
    payload: dict = Field(default_factory=dict, sa_column=Column(JSON))
    #: How many rivals were read and how many claims survived verification.
    #: Denormalized so a list of scans can be rendered without deserializing
    #: every payload.
    rivals_profiled: int = 0
    claims_verified: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ProofCandidateRow(SQLModel, table=True):
    """Something the web says about this brand, and what the user decided."""

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    brand_id: UUID = Field(foreign_key="brand.id", index=True)
    kind: str = "mention"
    claim: str = ""
    verbatim: str = ""
    url: str = ""
    attributed_to: str = ""
    venue: str = ""
    confidence: float = 0.5
    caveat: str = ""
    #: `pending`, `approved` or `rejected`.
    status: str = Field(default="pending", index=True)
    #: The ledger id this became when approved (P1, P2, ...). Assigned once and
    #: never reused, so a shipped email's citation keeps pointing at the fact
    #: it was written from.
    evidence_id: str = ""
    found_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    decided_at: datetime | None = None


class RadarEventRow(SQLModel, table=True):
    """One thing that changed between two scans."""

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    brand_id: UUID = Field(foreign_key="brand.id", index=True)
    headline: str = ""
    detail: str = ""
    #: `acts_on_copy`, `notable` or `routine`.
    severity: str = Field(default="routine", index=True)
    rival: str = ""
    axis: str = ""
    what_to_do: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    seen_at: datetime | None = None


class AudienceMapRow(SQLModel, table=True):
    """One compiled reading of who would buy this brand's product."""

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    brand_id: UUID = Field(foreign_key="brand.id", index=True)
    version: int = 1
    #: Serialized app.market.demand.DemandMap.
    payload: dict = Field(default_factory=dict, sa_column=Column(JSON))
    #: How many segments were mapped and how many of them the brand's own
    #: material would never have produced. Denormalized so a list of maps
    #: renders without deserializing every payload - and because the second
    #: number is the one that says whether the map was worth running.
    segments: int = 0
    unobvious_segments: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ProspectRow(SQLModel, table=True):
    """One named organisation that could buy this, and what the user did with it."""

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    brand_id: UUID = Field(foreign_key="brand.id", index=True)
    #: The segment name this was found for. A plain string rather than a
    #: foreign key: segments live inside a versioned map payload, and a
    #: prospect must not be orphaned by the next remap - the name is what the
    #: user recognises, and a name that no longer matches any segment is a
    #: readable state rather than a dangling reference.
    segment: str = Field(default="", index=True)
    name: str = ""
    url: str = ""
    what_they_do: str = ""
    why_them: str = ""
    verbatim: str = ""
    fit: float = 0.5
    #: Serialized list[app.market.demand.Contact]. Stored as a payload rather
    #: than a table because nothing queries across contacts: they are read
    #: with their prospect, exported with their prospect, and meaningless
    #: apart from it.
    contacts: list = Field(default_factory=list, sa_column=Column(JSON))
    caveat: str = ""
    verified: bool = False
    pages_read: int = 0
    invented_contacts: int = 0
    note: str = ""
    #: `new`, `kept` or `dismissed`.
    status: str = Field(default="new", index=True)
    found_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    decided_at: datetime | None = None
