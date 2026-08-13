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


class BrandRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    website_url: str | None
    logo_url: str | None = None
    primary_color: str | None = None
    footer_lines: list[str] | None = None
    created_at: UtcDatetime
    updated_at: UtcDatetime


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
