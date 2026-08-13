from app.core.config import get_settings
from app.ingestion.analyzers.image_analyzer import ImageAnalyzer
from app.ingestion.assets.loader import AssetLoader
from app.ingestion.assets.store import InMemoryAssetStore
from app.ingestion.chunkers.base import Chunker
from app.ingestion.chunkers.heading_chunker import HeadingChunker
from app.ingestion.cleaners.base import Cleaner, CleanerPipeline
from app.ingestion.cleaners.duplicate_cleaner import DuplicateCleaner
from app.ingestion.cleaners.empty_section_cleaner import EmptySectionCleaner
from app.ingestion.cleaners.html_cleaner import HtmlCleaner
from app.ingestion.cleaners.markdown_cleaner import MarkdownCleaner
from app.ingestion.cleaners.whitespace_cleaner import WhitespaceCleaner
from app.ingestion.documents import KnowledgeDocument, RawDocument, SourceType
from app.ingestion.exceptions import AnalyzerNotFoundError, DuplicateDocumentError
from app.ingestion.loaders.registry import LoaderRegistry, default_registry, detect_source_type
from app.ingestion.metadata import compute_content_metrics
from app.ingestion.multimodal_pipeline import MultimodalIngestionPipeline
from app.ingestion.normalizers.base import Normalizer
from app.ingestion.normalizers.default_normalizer import DefaultNormalizer
from app.ingestion.ocr.tesseract_provider import TesseractOCRProvider
from app.ingestion.store.base import KnowledgeStore
from app.ingestion.store.in_memory_store import InMemoryKnowledgeStore
from app.ingestion.vision.claude_vision_provider import ClaudeVisionProvider


def default_cleaners() -> list[Cleaner]:
    return [HtmlCleaner(), MarkdownCleaner(), WhitespaceCleaner(), DuplicateCleaner(), EmptySectionCleaner()]


class IngestionPipeline:
    """Orchestrates Source -> Loader -> RawDocument -> Normalizer -> Cleaner
    chain -> Chunker -> KnowledgeDocument -> KnowledgeStore. Every dependency
    is injected - this class instantiates none of them itself."""

    def __init__(
        self,
        loaders: LoaderRegistry,
        normalizer: Normalizer,
        cleaners: list[Cleaner],
        chunker: Chunker,
        store: KnowledgeStore,
    ) -> None:
        self._loaders = loaders
        self._normalizer = normalizer
        self._cleaner_pipeline = CleanerPipeline(cleaners)
        self._chunker = chunker
        self._store = store

    async def ingest(self, source: str, source_type: SourceType | None = None) -> KnowledgeDocument:
        resolved_type = source_type or detect_source_type(source)
        loader = self._loaders.get(resolved_type)
        return await self.ingest_raw(await loader.load(source))

    async def ingest_raw(self, raw: RawDocument) -> KnowledgeDocument:
        """Everything after loading: normalize, clean, chunk, store.

        Split out so a caller that produced the raw document itself - the site
        crawler, which fetches many pages in one pass - gets the identical
        treatment a single-page load would have given each of them.
        """
        document = await self._normalizer.normalize(raw)

        document.content = self._cleaner_pipeline.apply(document.content)
        document.metadata.update(compute_content_metrics(document.content))
        document.chunks = self._chunker.chunk(document)

        try:
            return await self._store.add_document(document)
        except DuplicateDocumentError as exc:
            existing_id = exc.details["existing_id"]
            return await self._store.get_document(existing_id)


_default_store: KnowledgeStore | None = None
_default_pipeline: IngestionPipeline | None = None
_default_multimodal_pipeline: MultimodalIngestionPipeline | None = None


def get_default_store() -> KnowledgeStore:
    """The single KnowledgeStore shared by the default text and multimodal
    pipelines, so `load()` always writes into one place regardless of source
    type."""
    global _default_store
    if _default_store is None:
        _default_store = InMemoryKnowledgeStore()
    return _default_store


def get_default_pipeline() -> IngestionPipeline:
    """Lazily-built composition root wiring default components. Convenience
    for simple call sites; anything that needs custom wiring should construct
    its own IngestionPipeline instead of using this."""
    global _default_pipeline
    if _default_pipeline is None:
        _default_pipeline = IngestionPipeline(
            loaders=default_registry(),
            normalizer=DefaultNormalizer(),
            cleaners=default_cleaners(),
            chunker=HeadingChunker(),
            store=get_default_store(),
        )
    return _default_pipeline


def get_default_multimodal_pipeline() -> MultimodalIngestionPipeline:
    """Lazily-built composition root for the image pipeline. Video/audio have
    no analyzer yet, so they're deliberately absent from this registry."""
    global _default_multimodal_pipeline
    if _default_multimodal_pipeline is None:
        vision = ClaudeVisionProvider(model=get_settings().anthropic_model)
        ocr = TesseractOCRProvider()
        _default_multimodal_pipeline = MultimodalIngestionPipeline(
            asset_loader=AssetLoader(),
            analyzers={SourceType.IMAGE: ImageAnalyzer(ocr=ocr, vision=vision)},
            store=get_default_store(),
            asset_store=InMemoryAssetStore(),
        )
    return _default_multimodal_pipeline


async def load(
    source: str, source_type: SourceType | None = None
) -> KnowledgeDocument | list[KnowledgeDocument]:
    """`await load("https://example.com")` -> a normalized, stored KnowledgeDocument.
    `await load("product.png")` -> one or more structured KnowledgeDocuments
    describing the image's visual content (routed to the multimodal pipeline).
    Video/audio sources raise AnalyzerNotFoundError - architecture only in
    this phase, no analyzer is registered for them yet."""
    resolved_type = source_type or detect_source_type(source)

    if resolved_type == SourceType.IMAGE:
        return await get_default_multimodal_pipeline().ingest_image(source)

    if resolved_type in (SourceType.VIDEO, SourceType.AUDIO):
        raise AnalyzerNotFoundError(
            f"No analyzer implemented yet for source type '{resolved_type}' - "
            "video/audio are architecture-only in this phase",
            source_type=resolved_type,
        )

    return await get_default_pipeline().ingest(source, resolved_type)
