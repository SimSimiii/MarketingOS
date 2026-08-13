from app.ingestion.analyzers.base import BaseAnalyzer
from app.ingestion.assets.loader import AssetLoader
from app.ingestion.assets.store import AssetStore
from app.ingestion.documents import KnowledgeDocument, SourceType
from app.ingestion.exceptions import AnalyzerNotFoundError
from app.ingestion.store.base import KnowledgeStore


class MultimodalIngestionPipeline:
    """Orchestrates Asset -> Analyzer -> KnowledgeDocument(s) -> KnowledgeStore
    (+ AssetStore). Every dependency is injected - this class instantiates
    none of them itself."""

    def __init__(
        self,
        asset_loader: AssetLoader,
        analyzers: dict[SourceType, BaseAnalyzer],
        store: KnowledgeStore,
        asset_store: AssetStore,
    ) -> None:
        self._asset_loader = asset_loader
        self._analyzers = analyzers
        self._store = store
        self._asset_store = asset_store

    async def ingest_image(self, path: str) -> list[KnowledgeDocument]:
        analyzer = self._analyzers.get(SourceType.IMAGE)
        if analyzer is None:
            raise AnalyzerNotFoundError(
                f"No analyzer registered for source type '{SourceType.IMAGE}'",
                source_type=SourceType.IMAGE,
            )

        asset, content = self._asset_loader.load_image(path)
        await self._asset_store.add_asset(asset)

        documents = await analyzer.analyze(asset, content)
        for document in documents:
            await self._store.add_document(document)
        return documents
