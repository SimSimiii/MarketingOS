from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.types import UtcDatetime


class BrandCreateRequest(BaseModel):
    name: str
    website_url: str | None = None


class BrandStyleUpdate(BaseModel):
    """How this brand's email looks once it is rendered.

    Every field optional, and a brand with none of them set still produces a
    good email - it renders in the typographic tier, which is the right
    default for the cold sequences this system mostly writes anyway.
    """

    logo_url: str | None = None
    primary_color: str | None = None
    footer_lines: list[str] | None = None
    unsubscribe_url: str | None = None


class BrandRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    website_url: str | None
    logo_url: str | None = None
    primary_color: str | None = None
    footer_lines: list[str] | None = None
    unsubscribe_url: str | None = None
    created_at: UtcDatetime
    updated_at: UtcDatetime


class BrandOverviewRead(BrandRead):
    """One brand as the brand list shows it: the state of its own workspace.

    Counts rather than payloads, and computed in aggregate rather than per
    brand, because this is the page that answers "which of my businesses needs
    me today" - it should not cost one knowledge compile read per card to
    render. Everything here is scoped to the brand: there is no such thing as
    a source, a competitor or an alert that belongs to all of them.
    """

    sources: int = 0
    campaigns: int = 0
    #: Latest compiled knowledge version, or None when nothing was compiled
    #: yet - which happens on the first campaign run, not on registration.
    knowledge_version: int | None = None
    compiled_at: UtcDatetime | None = None
    #: Competitors the user has not muted. Muted ones stay on the list but are
    #: not part of what this brand is measured against.
    rivals: int = 0
    scanned_at: UtcDatetime | None = None
    pending_proof: int = 0
    unseen_alerts: int = 0


class KnowledgeArtifactsRead(BaseModel):
    """What the system currently knows about a business, and how it knows it.

    Exposed because the artifacts are the campaign's foundation: a user who
    can see that we found no pricing and no testimonials understands why the
    copy is not naming numbers, and can fix it by uploading one page.
    """

    version: int
    compiled_at: UtcDatetime
    evidence_count: int
    segments: list[str]
    gaps: list[str]
    voice_learned: bool
    #: The full artifact bundle, for a client that wants to render the detail.
    artifacts: dict
