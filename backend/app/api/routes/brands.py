from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.deps import SessionDep
from app.knowledge.store import ArtifactScope, ArtifactStore
from app.models.brand import Brand
from app.repositories.brand_repository import BrandRepository
from app.schemas.brand import (
    BrandCreateRequest,
    BrandRead,
    BrandStyleUpdate,
    KnowledgeArtifactsRead,
)

router = APIRouter(prefix="/brands", tags=["brands"])


@router.post("", response_model=BrandRead, status_code=status.HTTP_201_CREATED)
def create_brand(data: BrandCreateRequest, session: SessionDep) -> BrandRead:
    """Register a business, so its knowledge is compiled once and reused by
    every campaign for it instead of recompiled per campaign."""
    brand = BrandRepository(session).create(
        Brand(name=data.name, website_url=data.website_url)
    )
    return BrandRead.model_validate(brand)


@router.get("", response_model=list[BrandRead])
def list_brands(session: SessionDep) -> list[BrandRead]:
    return [BrandRead.model_validate(brand) for brand in BrandRepository(session).list_all()]


@router.patch("/{brand_id}/style", response_model=BrandRead)
def update_style(brand_id: UUID, data: BrandStyleUpdate, session: SessionDep) -> BrandRead:
    """Set how this brand's emails look when rendered as HTML.

    Only the fields present in the request are touched, so a client changing
    the colour does not have to resend the footer it never had.
    """
    repository = BrandRepository(session)
    brand = repository.get(brand_id)
    if brand is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Brand not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(brand, field, value)
    return BrandRead.model_validate(repository.update(brand))


@router.get("/{brand_id}/knowledge", response_model=KnowledgeArtifactsRead)
def get_knowledge(brand_id: UUID, session: SessionDep) -> KnowledgeArtifactsRead:
    """The compiled knowledge campaigns for this brand are written from."""
    if BrandRepository(session).get(brand_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Brand not found")

    stored = ArtifactStore(session).load(ArtifactScope(brand_id=brand_id))
    if stored is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Nothing has been compiled for this brand yet - it happens on the first campaign run.",
        )
    artifacts = stored.artifacts
    return KnowledgeArtifactsRead(
        version=stored.version,
        compiled_at=artifacts.compiled_at,
        evidence_count=len(artifacts.evidence.entries),
        segments=[segment.name for segment in artifacts.audience.segments],
        gaps=[f"{gap.missing} - {gap.impact}" for gap in artifacts.gaps.unanswered],
        voice_learned=artifacts.voice.learned,
        artifacts=artifacts.model_dump(mode="json"),
    )


@router.delete("/{brand_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_brand(brand_id: UUID, session: SessionDep) -> None:
    brand = BrandRepository(session).get(brand_id)
    if brand is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Brand not found")
    BrandRepository(session).delete(brand)
