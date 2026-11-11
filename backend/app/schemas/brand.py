from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, StringConstraints

from app.marketing.gates import GateIssue
from app.marketing.grounding import GroundingDecision
from app.schemas.types import UtcDatetime


class DraftReviewRequest(BaseModel):
    text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=16000)]
    destination: HttpUrl | None = None


class DraftReviewRead(BaseModel):
    approved: bool
    decision: GroundingDecision | None = None
    issues: list[GateIssue]
    sources: dict[str, str] = Field(default_factory=dict)


class DraftReviewJobRead(BaseModel):
    id: UUID
    state: Literal["running", "completed", "failed"]
    result: DraftReviewRead | None = None
    error: str = ""


class BrandCreateRequest(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    website_url: str | None = None


class BrandStyleUpdate(BaseModel):
    """How this brand's email looks once it is rendered.

    Every field optional, and a brand with none of them set still produces a
    good email - its name set as a wordmark, a neutral blue. Crawling the
    brand's own site fills the logo and colour it declares, when it declares
    usable ones; see app.ingestion.loaders.site_identity.
    """

    logo_url: str | None = None
    primary_color: str | None = None
    footer_lines: list[str] | None = None
    unsubscribe_url: str | None = None


class BrandIdentityRead(BaseModel):
    """What the brand's own site declares about its look - a suggestion for
    the appearance form, never saved by the request that found it."""

    logo_url: str | None = None
    primary_color: str | None = None
    #: Why something the site declared was not used, in words the owner can
    #: act on - "the logo is an SVG", "the theme colour is too pale".
    notes: list[str] = []


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
