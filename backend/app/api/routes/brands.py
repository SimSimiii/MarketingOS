from datetime import datetime
from uuid import UUID

import httpx
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func
from sqlmodel import Session, col, select

from app.api.deps import AIProviderDep, PrincipalDep, SessionDep
from app.core.public_http import fetch_page, public_client
from app.ingestion.exceptions import LoaderError
from app.ingestion.loaders.site_identity import read_identity
from app.knowledge.store import ArtifactScope, ArtifactStore
from app.models.background_job import BackgroundJob
from app.models.brand import Brand
from app.models.campaign import Campaign
from app.models.knowledge_artifacts import KnowledgeArtifactSet
from app.models.knowledge_document import KnowledgeDocument
from app.models.market import MarketScan, ProofCandidateRow, RadarEventRow, Rival
from app.repositories.brand_repository import BrandRepository
from app.schemas.brand import (
    BrandCreateRequest,
    BrandIdentityRead,
    BrandOverviewRead,
    BrandRead,
    BrandStyleUpdate,
    DraftReviewJobRead,
    DraftReviewRequest,
    KnowledgeArtifactsRead,
)
from app.services import draft_review
from app.services.knowledge_compilation import (
    CompilationRequest,
    CompilationStatus,
    start_compilation,
)
from app.services.knowledge_compilation import job_for as compilation_job_for

router = APIRouter(prefix="/brands", tags=["brands"])


@router.post("/{brand_id}/draft-review", response_model=DraftReviewJobRead, status_code=202)
async def review_draft(
    brand_id: UUID, data: DraftReviewRequest, session: SessionDep,
    provider: AIProviderDep, principal: PrincipalDep,
) -> DraftReviewJobRead:
    brand = BrandRepository(session, principal).get(brand_id)
    if brand is None:
        raise HTTPException(404, "Brand not found")
    return draft_review.launch(session, brand, provider, data)


@router.get("/{brand_id}/draft-review/{job_id}", response_model=DraftReviewJobRead)
def read_draft_review(
    brand_id: UUID, job_id: UUID, session: SessionDep, principal: PrincipalDep,
) -> DraftReviewJobRead:
    if BrandRepository(session, principal).get(brand_id) is None:
        raise HTTPException(404, "Brand not found")
    job = session.get(BackgroundJob, job_id)
    if job is None or job.brand_id != brand_id or job.category != draft_review.CATEGORY:
        raise HTTPException(404, "Draft review not found")
    return draft_review.snapshot(job)


@router.get("/{brand_id}/draft-review", response_model=DraftReviewJobRead | None)
def latest_draft_review(
    brand_id: UUID, session: SessionDep, principal: PrincipalDep,
) -> DraftReviewJobRead | None:
    if BrandRepository(session, principal).get(brand_id) is None:
        raise HTTPException(404, "Brand not found")
    job = session.exec(select(BackgroundJob).where(
        BackgroundJob.brand_id == brand_id, BackgroundJob.category == draft_review.CATEGORY,
    ).order_by(col(BackgroundJob.created_at).desc())).first()
    return draft_review.snapshot(job) if job is not None else None


@router.get("/{brand_id}/knowledge/compile", response_model=CompilationStatus)
def compilation_status(
    brand_id: UUID, session: SessionDep, principal: PrincipalDep
) -> CompilationStatus:
    if BrandRepository(session, principal).get(brand_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Brand not found")
    return compilation_job_for(brand_id) or CompilationStatus()


@router.post("/{brand_id}/knowledge/compile", response_model=CompilationStatus, status_code=202)
async def compile_knowledge(
    brand_id: UUID, session: SessionDep, provider: AIProviderDep, principal: PrincipalDep,
    data: CompilationRequest | None = None,
) -> CompilationStatus:
    brand = BrandRepository(session, principal).get(brand_id)
    if brand is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Brand not found")
    documents = ArtifactStore(session).source_documents(ArtifactScope(brand_id=brand_id))
    if not any(document.content.strip() for document in documents):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Add sources before compiling.")
    return start_compilation(
        brand_id, session.get_bind(), provider, brand.name, model=data.model if data else None
    )


@router.post("", response_model=BrandRead, status_code=status.HTTP_201_CREATED)
def create_brand(
    data: BrandCreateRequest, session: SessionDep, principal: PrincipalDep
) -> BrandRead:
    """Register a business, so its knowledge is compiled once and reused by
    every campaign for it instead of recompiled per campaign."""
    brand = BrandRepository(session, principal).create(
        Brand(name=data.name, website_url=data.website_url, owner_id=principal.owner_id)
    )
    return BrandRead.model_validate(brand)


@router.get("", response_model=list[BrandRead])
def list_brands(session: SessionDep, principal: PrincipalDep) -> list[BrandRead]:
    brands = BrandRepository(session, principal).list_all()
    return [BrandRead.model_validate(brand) for brand in brands]


@router.get("/overview", response_model=list[BrandOverviewRead])
def list_overview(session: SessionDep, principal: PrincipalDep) -> list[BrandOverviewRead]:
    """Every brand with the state of its own workspace.

    Declared above `/{brand_id}` deliberately: FastAPI matches in declaration
    order, and "overview" would otherwise be handed to the single-brand route
    as a malformed UUID.

    One grouped query per fact instead of one request per card, because the
    alternative - the client fetching knowledge, market and documents for each
    brand in turn - is what makes a list of five businesses feel like five
    pages.
    """
    brands = BrandRepository(session, principal).list_all()
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
def get_brand(brand_id: UUID, session: SessionDep, principal: PrincipalDep) -> BrandRead:
    """One business, for the pages that are scoped to it."""
    brand = BrandRepository(session, principal).get(brand_id)
    if brand is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Brand not found")
    return BrandRead.model_validate(brand)


@router.patch("/{brand_id}/style", response_model=BrandRead)
def update_style(
    brand_id: UUID, data: BrandStyleUpdate, session: SessionDep, principal: PrincipalDep
) -> BrandRead:
    """Set how this brand's emails look when rendered as HTML.

    Only the fields present in the request are touched, so a client changing
    the colour does not have to resend the footer it never had.
    """
    repository = BrandRepository(session, principal)
    brand = repository.get(brand_id)
    if brand is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Brand not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(brand, field, value)
    return BrandRead.model_validate(repository.update(brand))


@router.post("/{brand_id}/style/detect", response_model=BrandIdentityRead)
async def detect_style(
    brand_id: UUID, session: SessionDep, principal: PrincipalDep
) -> BrandIdentityRead:
    """Read the logo and colour the brand's own home page declares.

    A suggestion, not a save: the appearance page fills its form with it and
    the owner decides, because a site can declare a logo that is wrong for
    an email in ways only a person looking at it will catch. Crawling the
    site fills an empty brand automatically; this is how a brand crawled
    before that existed, or one whose owner wants to look first, gets it.
    """
    brand = BrandRepository(session, principal).get(brand_id)
    if brand is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Brand not found")
    if not brand.website_url:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Add the brand's website first.")
    try:
        html, url = await read_home_page(brand.website_url)
    except (httpx.HTTPError, LoaderError) as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, f"Could not read {brand.website_url}: {exc}"
        ) from exc
    identity = read_identity(html, url)
    return BrandIdentityRead(
        logo_url=identity.logo_url or None,
        primary_color=identity.theme_color or None,
        notes=list(identity.notes),
    )


async def read_home_page(url: str) -> tuple[str, str]:
    """The page's HTML and the address it finally answered from."""
    async with public_client() as client:
        response = await fetch_page(client, url)
        response.raise_for_status()
    return response.text, str(response.url)


@router.get("/{brand_id}/knowledge", response_model=KnowledgeArtifactsRead)
def get_knowledge(
    brand_id: UUID, session: SessionDep, principal: PrincipalDep
) -> KnowledgeArtifactsRead:
    """The compiled knowledge campaigns for this brand are written from."""
    if BrandRepository(session, principal).get(brand_id) is None:
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
def delete_brand(brand_id: UUID, session: SessionDep, principal: PrincipalDep) -> None:
    brand = BrandRepository(session, principal).get(brand_id)
    if brand is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Brand not found")
    from sqlalchemy import select
    from sqlalchemy.exc import IntegrityError
    from sqlmodel import SQLModel

    from app.services.market_service import all_jobs

    if (compilation_job_for(brand_id) is not None and compilation_job_for(brand_id).state == "running") or any(
        job.brand_id == brand_id and job.state == "running" for job in all_jobs()
    ):
        raise HTTPException(409, "Wait for this brand's jobs to finish before deleting it.")
    from sqlalchemy import delete

    session.execute(delete(BackgroundJob).where(BackgroundJob.brand_id == brand_id, ~BackgroundJob.active))
    for table in SQLModel.metadata.tables.values():
        for foreign_key in table.foreign_keys:
            if foreign_key.target_fullname == "brand.id" and session.execute(select(foreign_key.parent).where(
                    foreign_key.parent == brand_id
                ).limit(1)).first() is not None:
                raise HTTPException(409, "This brand still has data. Remove its dependencies first.")
    try:
        BrandRepository(session, principal).delete(brand)
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(409, "This brand is still in use.") from exc
