from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.api.deps import KnowledgeServiceDep
from app.ingestion.exceptions import IngestionError
from app.schemas.knowledge import (
    KnowledgeBaseRead,
    KnowledgeDocumentRead,
    KnowledgeDocumentSummary,
    KnowledgeSourceCreate,
)
from app.services.knowledge_service import UnsupportedSourceError

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

#: Refuse oversized uploads before reading them into memory.
MAX_UPLOAD_BYTES = 20 * 1024 * 1024


@router.post("", response_model=list[KnowledgeDocumentRead], status_code=status.HTTP_201_CREATED)
async def add_source(
    data: KnowledgeSourceCreate, service: KnowledgeServiceDep
) -> list[KnowledgeDocumentRead]:
    """Add product knowledge from a web page or pasted text."""
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
    file: UploadFile = File(...),
    campaign_id: UUID | None = Form(default=None),
    brand_id: UUID | None = Form(default=None),
    title: str | None = Form(default=None),
) -> list[KnowledgeDocumentRead]:
    """Upload a product document or image (PDF, DOCX, markdown, screenshot).

    Images are read by the vision + OCR pipeline; only the extracted
    knowledge is kept, never the binary.
    """
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
    campaign_id: UUID | None = None,
    brand_id: UUID | None = None,
) -> list[KnowledgeDocumentSummary]:
    """Metadata only - see KnowledgeDocumentSummary. Fetch one by id for text."""
    return [
        KnowledgeDocumentSummary.model_validate(document)
        for document in service.list_documents(campaign_id, brand_id)
    ]


@router.get("/base", response_model=KnowledgeBaseRead)
def get_knowledge_base(
    service: KnowledgeServiceDep,
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
    base = service.knowledge_base(brand_id=brand_id, campaign_id=campaign_id)
    if base is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Nothing has been compiled here yet - it happens on the first campaign run.",
        )
    return KnowledgeBaseRead.from_base(base, brand_id=brand_id, campaign_id=campaign_id)


@router.get("/{document_id}", response_model=KnowledgeDocumentRead)
def get_document(document_id: UUID, service: KnowledgeServiceDep) -> KnowledgeDocumentRead:
    document = service.get_document(document_id)
    if document is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Knowledge document not found")
    return KnowledgeDocumentRead.model_validate(document)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: UUID, service: KnowledgeServiceDep) -> None:
    document = service.get_document(document_id)
    if document is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Knowledge document not found")
    service.delete_document(document)
