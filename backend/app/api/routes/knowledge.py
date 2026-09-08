from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.api.deps import KnowledgeServiceDep, PrincipalDep, SessionDep
from app.ingestion.exceptions import IngestionError
from app.repositories.brand_repository import BrandRepository
from app.repositories.campaign_repository import CampaignRepository
from app.schemas.knowledge import (
    KnowledgeBaseRead,
    KnowledgeDocumentRead,
    KnowledgeDocumentSummary,
    KnowledgeSourceCreate,
)
from app.services.knowledge_compilation import CompilationJob, jobs
from app.services.knowledge_service import UnsupportedSourceError

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

#: Refuse oversized uploads before reading them into memory.
MAX_UPLOAD_BYTES = 20 * 1024 * 1024


def _guard_scope(
    session: SessionDep,
    principal: PrincipalDep,
    brand_id: UUID | None,
    campaign_id: UUID | None,
) -> None:
    """A source is filed against a brand or a campaign; both are owned roots.

    Unlike the market router this cannot be a router-level dependency: the
    scope arrives in a JSON body on one route and as multipart form fields on
    another, and a dependency only sees the path and the query string.
    """
    if brand_id is not None and BrandRepository(session, principal).get(brand_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Brand not found")
    if campaign_id is not None and CampaignRepository(session, principal).get(campaign_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Campaign not found")


@router.get("/jobs", response_model=list[CompilationJob])
def list_compilation_jobs(session: SessionDep, principal: PrincipalDep) -> list[CompilationJob]:
    brand_ids = {brand.id for brand in BrandRepository(session, principal).list_all()}
    return sorted(
        (job for job in jobs.values() if job.brand_id in brand_ids),
        key=lambda job: (job.state == "running", job.started_at),
        reverse=True,
    )


@router.post("", response_model=list[KnowledgeDocumentRead], status_code=status.HTTP_201_CREATED)
async def add_source(
    data: KnowledgeSourceCreate,
    service: KnowledgeServiceDep,
    session: SessionDep,
    principal: PrincipalDep,
) -> list[KnowledgeDocumentRead]:
    """Add product knowledge from a web page or pasted text."""
    _guard_scope(session, principal, data.brand_id, data.campaign_id)
    try:
        documents = await service.ingest_source(
            source=data.url or data.content or "",
            campaign_id=data.campaign_id,
            brand_id=data.brand_id,
            title=data.title,
            crawl=data.crawl,
            max_pages=data.max_pages,
        )
    except UnsupportedSourceError as exc:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, str(exc)) from exc
    except IngestionError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    return [KnowledgeDocumentRead.model_validate(document) for document in documents]


@router.post(
    "/upload", response_model=list[KnowledgeDocumentRead], status_code=status.HTTP_201_CREATED
)
async def upload_file(
    service: KnowledgeServiceDep,
    session: SessionDep,
    principal: PrincipalDep,
    file: UploadFile = File(...),
    campaign_id: UUID | None = Form(default=None),
    brand_id: UUID | None = Form(default=None),
    title: str | None = Form(default=None),
) -> list[KnowledgeDocumentRead]:
    """Upload a product document or image (PDF, DOCX, markdown, screenshot).

    Images are read by the vision + OCR pipeline; only the extracted
    knowledge is kept, never the binary.
    """
    _guard_scope(session, principal, brand_id, campaign_id)
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"File exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit",
        )
    try:
        documents = await service.ingest_upload(
            filename=file.filename or "upload.txt",
            data=data,
            campaign_id=campaign_id,
            brand_id=brand_id,
            title=title,
        )
    except UnsupportedSourceError as exc:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, str(exc)) from exc
    except IngestionError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    return [KnowledgeDocumentRead.model_validate(document) for document in documents]


@router.get("", response_model=list[KnowledgeDocumentSummary])
def list_documents(
    service: KnowledgeServiceDep,
    session: SessionDep,
    principal: PrincipalDep,
    campaign_id: UUID | None = None,
    brand_id: UUID | None = None,
) -> list[KnowledgeDocumentSummary]:
    """Metadata only - see KnowledgeDocumentSummary. Fetch one by id for text."""
    _guard_scope(session, principal, brand_id, campaign_id)
    return [
        KnowledgeDocumentSummary.model_validate(document)
        for document in service.list_documents(campaign_id, brand_id)
    ]


@router.get("/base", response_model=KnowledgeBaseRead)
def get_knowledge_base(
    service: KnowledgeServiceDep,
    session: SessionDep,
    principal: PrincipalDep,
    brand_id: UUID | None = None,
    campaign_id: UUID | None = None,
) -> KnowledgeBaseRead:
    """Everything compiled about one business, classified onto shelves.

    Declared above `/{document_id}` deliberately: FastAPI matches routes in
    declaration order, and "base" would otherwise be handed to the document
    route as a malformed UUID and 422 instead of resolving here.
    """
    if brand_id is None and campaign_id is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Pass either `brand_id` or `campaign_id` - knowledge belongs to one business.",
        )
    _guard_scope(session, principal, brand_id, campaign_id)
    base = service.knowledge_base(brand_id=brand_id, campaign_id=campaign_id)
    if base is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Nothing has been compiled here yet - it happens on the first campaign run.",
        )
    return KnowledgeBaseRead.from_base(base, brand_id=brand_id, campaign_id=campaign_id)


@router.get("/{document_id}", response_model=KnowledgeDocumentRead)
def get_document(
    document_id: UUID,
    service: KnowledgeServiceDep,
    session: SessionDep,
    principal: PrincipalDep,
) -> KnowledgeDocumentRead:
    document = service.get_document(document_id)
    if document is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Knowledge document not found")
    _guard_scope(session, principal, document.brand_id, document.campaign_id)
    return KnowledgeDocumentRead.model_validate(document)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: UUID,
    service: KnowledgeServiceDep,
    session: SessionDep,
    principal: PrincipalDep,
) -> None:
    document = service.get_document(document_id)
    if document is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Knowledge document not found")
    _guard_scope(session, principal, document.brand_id, document.campaign_id)
    service.delete_document(document)
