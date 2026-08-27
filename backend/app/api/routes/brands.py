from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func
from sqlmodel import Session, col, select

from app.api.deps import SessionDep
from app.knowledge.store import ArtifactScope, ArtifactStore
from app.models.brand import Brand
from app.models.campaign import Campaign
from app.models.knowledge_artifacts import KnowledgeArtifactSet
from app.models.knowledge_document import KnowledgeDocument
from app.models.market import MarketScan, ProofCandidateRow, RadarEventRow, Rival
from app.repositories.brand_repository import BrandRepository
from app.schemas.brand import (
    BrandCreateRequest,
    BrandOverviewRead,
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


@router.get("/overview", response_model=list[BrandOverviewRead])
def list_overview(session: SessionDep) -> list[BrandOverviewRead]:
    """Every brand with the state of its own workspace.

    Declared above `/{brand_id}` deliberately: FastAPI matches in declaration
    order, and "overview" would otherwise be handed to the single-brand route
    as a malformed UUID.

    One grouped query per fact instead of one request per card, because the
    alternative - the client fetching knowledge, market and documents for each
    brand in turn - is what makes a list of five businesses feel like five
    pages.
    """
    brands = BrandRepository(session).list_all()
    if not brands:
        return []

    sources = _grouped_count(session, KnowledgeDocument)
    campaigns = _grouped_count(session, Campaign)
    rivals = _grouped_count(session, Rival, col(Rival.muted).is_(False))
    pending = _grouped_count(
        session, ProofCandidateRow, col(ProofCandidateRow.status) == "pending"
    )
    alerts = _grouped_count(
        session,
        RadarEventRow,
        col(RadarEventRow.seen_at).is_(None),
        col(RadarEventRow.severity) == "acts_on_copy",
    )
    versions = _grouped_max(session, KnowledgeArtifactSet, col(KnowledgeArtifactSet.version))
    compiled = _grouped_max(session, KnowledgeArtifactSet, col(KnowledgeArtifactSet.created_at))
    scanned = _grouped_max(session, MarketScan, col(MarketScan.created_at))

    return [
        BrandOverviewRead(
            **BrandRead.model_validate(brand).model_dump(),
            sources=sources.get(brand.id, 0),
            campaigns=campaigns.get(brand.id, 0),
            knowledge_version=versions.get(brand.id),
            compiled_at=_as_datetime(compiled.get(brand.id)),
            rivals=rivals.get(brand.id, 0),
            scanned_at=_as_datetime(scanned.get(brand.id)),
            pending_proof=pending.get(brand.id, 0),
            unseen_alerts=alerts.get(brand.id, 0),
        )
        for brand in brands
    ]


def _grouped_count(session: Session, model: type, *where: object) -> dict[UUID, int]:
    """How many rows of `model` each brand owns. Rows with no brand are not
    counted - a one-off campaign's knowledge belongs to that campaign."""
    statement = (
        select(model.brand_id, func.count())  # type: ignore[attr-defined]
        .where(col(model.brand_id).is_not(None))  # type: ignore[attr-defined]
        .group_by(col(model.brand_id))  # type: ignore[attr-defined]
    )
    for clause in where:
        statement = statement.where(clause)
    return {brand_id: total for brand_id, total in session.exec(statement) if brand_id}


def _grouped_max(session: Session, model: type, column: object) -> dict[UUID, object]:
    statement = (
        select(model.brand_id, func.max(column))  # type: ignore[attr-defined]
        .where(col(model.brand_id).is_not(None))  # type: ignore[attr-defined]
        .group_by(col(model.brand_id))  # type: ignore[attr-defined]
    )
    return {brand_id: value for brand_id, value in session.exec(statement) if brand_id}


def _as_datetime(value: object) -> datetime | None:
    """SQLite hands `max()` over a DATETIME column back as a string."""
    if value is None or isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


@router.get("/{brand_id}", response_model=BrandRead)
def get_brand(brand_id: UUID, session: SessionDep) -> BrandRead:
    """One business, for the pages that are scoped to it."""
    brand = BrandRepository(session).get(brand_id)
    if brand is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Brand not found")
    return BrandRead.model_validate(brand)


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
