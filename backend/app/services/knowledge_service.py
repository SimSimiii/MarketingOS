import logging
import tempfile
from functools import cached_property
from pathlib import Path
from uuid import UUID

from sqlmodel import Session

from app.core.config import get_settings
from app.ingestion.analyzers.image_analyzer import ImageAnalyzer
from app.ingestion.assets.loader import AssetLoader
from app.ingestion.assets.store import InMemoryAssetStore
from app.ingestion.chunkers.heading_chunker import HeadingChunker
from app.ingestion.documents import KnowledgeDocument as IngestedDocument
from app.ingestion.documents import SourceType
from app.ingestion.loaders.registry import default_registry, detect_source_type
from app.ingestion.loaders.site_crawler import DEFAULT_MAX_PAGES, SiteCrawler
from app.ingestion.multimodal_pipeline import MultimodalIngestionPipeline
from app.ingestion.normalizers.default_normalizer import DefaultNormalizer
from app.ingestion.ocr.tesseract_provider import TesseractOCRProvider
from app.ingestion.pipeline import IngestionPipeline, default_cleaners
from app.ingestion.store.in_memory_store import InMemoryKnowledgeStore
from app.ingestion.vision.claude_vision_provider import ClaudeVisionProvider
from app.models.knowledge_document import KnowledgeDocument
from app.repositories.knowledge_repository import KnowledgeDocumentRepository

logger = logging.getLogger("marketingos.knowledge")

#: Loaders exist for these, but no analyzer does yet - reject them at the door
#: with a clear message rather than failing deep inside the pipeline.
UNSUPPORTED_SOURCE_TYPES = (SourceType.VIDEO, SourceType.AUDIO)


class UnsupportedSourceError(Exception):
    """Raised when the user submits a source MarketingOS cannot read yet."""


class KnowledgeService:
    """Turns whatever the user hands over - their website, a PDF, a screenshot
    of their landing page - into normalized knowledge.

    The ingestion engine does the reading (no LLM for text; vision + OCR for
    images); this service decides where the result is stored. Distilling it
    into artifacts a campaign can be written from is a separate job entirely -
    see app.knowledge.compiler.
    """

    def __init__(self, session: Session) -> None:
        self._documents = KnowledgeDocumentRepository(session)

    # The ingestion machinery is built lazily: this service is a per-request
    # FastAPI dependency, and most requests only list or delete documents.
    # Eagerly wiring up loaders, cleaners, a chunker, an OCR provider and a
    # vision provider on every one of those was pure waste.

    @cached_property
    def _store(self) -> InMemoryKnowledgeStore:
        # A fresh in-memory store per instance: SQL is the real persistence,
        # the ingestion store is only the pipeline's outbox.
        return InMemoryKnowledgeStore()

    @cached_property
    def _pipeline(self) -> IngestionPipeline:
        return IngestionPipeline(
            loaders=default_registry(),
            normalizer=DefaultNormalizer(),
            cleaners=default_cleaners(),
            chunker=HeadingChunker(),
            store=self._store,
        )

    @cached_property
    def _multimodal(self) -> MultimodalIngestionPipeline:
        return MultimodalIngestionPipeline(
            asset_loader=AssetLoader(),
            analyzers={
                SourceType.IMAGE: ImageAnalyzer(
                    ocr=TesseractOCRProvider(),
                    vision=ClaudeVisionProvider(model=get_settings().anthropic_model),
                )
            },
            store=self._store,
            asset_store=InMemoryAssetStore(),
        )

    async def ingest_source(
        self,
        source: str,
        campaign_id: UUID | None = None,
        brand_id: UUID | None = None,
        title: str | None = None,
        source_type: SourceType | None = None,
        crawl: bool = True,
        max_pages: int = DEFAULT_MAX_PAGES,
    ) -> list[KnowledgeDocument]:
        """Ingest a URL or raw pasted text, and persist the result.

        A website is crawled rather than fetched, because "add your website"
        almost always means the home page, and the home page is the page most
        carefully written to say nothing checkable. Prices live on /pricing and
        proof lives on /customers; a campaign grounded only in a hero section
        has nothing specific to say.
        """
        resolved = source_type or detect_source_type(source)
        self._reject_unsupported(resolved)

        if resolved == SourceType.WEBSITE and crawl:
            return await self._ingest_site(source, campaign_id, brand_id, max_pages)

        ingested = await self._pipeline.ingest(source, resolved)
        return [self._persist(ingested, campaign_id, brand_id, title)]

    async def _ingest_site(
        self,
        url: str,
        campaign_id: UUID | None,
        brand_id: UUID | None,
        max_pages: int,
    ) -> list[KnowledgeDocument]:
        pages = await SiteCrawler(max_pages=max_pages).crawl(url)
        documents: list[KnowledgeDocument] = []
        for raw in pages:
            ingested = await self._pipeline.ingest_raw(raw)
            documents.append(self._persist(ingested, campaign_id, brand_id, None))
        logger.info("crawled %s into %d document(s)", url, len(documents))
        return documents

    async def ingest_upload(
        self,
        filename: str,
        data: bytes,
        campaign_id: UUID | None = None,
        brand_id: UUID | None = None,
        title: str | None = None,
    ) -> list[KnowledgeDocument]:
        """Ingest an uploaded file (PDF, DOCX, markdown, screenshot...).

        The bytes go to a temporary file because loaders work on paths, and
        are deleted immediately after: we keep the extracted knowledge, never
        the binary.
        """
        resolved = detect_source_type(filename)
        self._reject_unsupported(resolved)

        with tempfile.NamedTemporaryFile(
            suffix=Path(filename).suffix or ".txt", delete=False
        ) as handle:
            handle.write(data)
            temp_path = handle.name
        try:
            if resolved == SourceType.IMAGE:
                ingested = await self._multimodal.ingest_image(temp_path)
            else:
                ingested = [await self._pipeline.ingest(temp_path, resolved)]
        finally:
            Path(temp_path).unlink(missing_ok=True)

        return [
            self._persist(
                document, campaign_id, brand_id, title if len(ingested) == 1 else None
            )
            for document in ingested
        ]

    def list_documents(
        self, campaign_id: UUID | None = None, brand_id: UUID | None = None
    ) -> list[KnowledgeDocument]:
        if brand_id is not None:
            return self._documents.list_for_brand(brand_id)
        if campaign_id is None:
            return self._documents.list()
        return self._documents.list_for_campaign(campaign_id)

    def get_document(self, document_id: UUID) -> KnowledgeDocument | None:
        return self._documents.get(document_id)

    def delete_document(self, document: KnowledgeDocument) -> None:
        self._documents.delete(document)

    # --------------------------------------------------------------- internals

    @staticmethod
    def _reject_unsupported(source_type: SourceType) -> None:
        if source_type in UNSUPPORTED_SOURCE_TYPES:
            raise UnsupportedSourceError(
                f"MarketingOS cannot read {source_type} sources yet - "
                "send a website, a document or an image."
            )

    def _persist(
        self,
        ingested: IngestedDocument,
        campaign_id: UUID | None,
        brand_id: UUID | None,
        title: str | None,
    ) -> KnowledgeDocument:
        metadata = dict(ingested.metadata)
        return self._documents.create(
            KnowledgeDocument(
                campaign_id=campaign_id,
                brand_id=brand_id,
                title=title or ingested.title,
                source_type=ingested.source,
                content=ingested.content,
                source_url=ingested.url,
                word_count=int(metadata.get("word_count", 0)),
                document_metadata=metadata,
            )
        )
