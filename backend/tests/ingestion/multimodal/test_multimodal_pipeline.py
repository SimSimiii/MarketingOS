import pytest

from app.ingestion.analyzers.image_analyzer import ImageAnalyzer
from app.ingestion.assets.loader import AssetLoader
from app.ingestion.assets.store import InMemoryAssetStore
from app.ingestion.documents import SourceType
from app.ingestion.exceptions import AnalyzerNotFoundError
from app.ingestion.multimodal_pipeline import MultimodalIngestionPipeline
from app.ingestion.store.in_memory_store import InMemoryKnowledgeStore


def make_pipeline(fake_ocr, fake_vision) -> tuple[MultimodalIngestionPipeline, InMemoryKnowledgeStore, InMemoryAssetStore]:
    store = InMemoryKnowledgeStore()
    asset_store = InMemoryAssetStore()
    pipeline = MultimodalIngestionPipeline(
        asset_loader=AssetLoader(),
        analyzers={SourceType.IMAGE: ImageAnalyzer(ocr=fake_ocr, vision=fake_vision)},
        store=store,
        asset_store=asset_store,
    )
    return pipeline, store, asset_store


@pytest.mark.asyncio
async def test_ingest_image_stores_document_and_asset(png_path, fake_ocr, fake_vision):
    pipeline, store, asset_store = make_pipeline(fake_ocr, fake_vision)

    documents = await pipeline.ingest_image(str(png_path))

    assert len(documents) == 1
    stored = await store.get_document(documents[0].id)
    assert stored.asset_id is not None

    stored_asset = await asset_store.get_asset(stored.asset_id)
    assert stored_asset.filename == "product.png"


@pytest.mark.asyncio
async def test_ingest_image_raises_when_no_analyzer_registered(png_path, fake_ocr, fake_vision):
    pipeline = MultimodalIngestionPipeline(
        asset_loader=AssetLoader(),
        analyzers={},  # no IMAGE analyzer registered
        store=InMemoryKnowledgeStore(),
        asset_store=InMemoryAssetStore(),
    )

    with pytest.raises(AnalyzerNotFoundError):
        await pipeline.ingest_image(str(png_path))


@pytest.mark.asyncio
async def test_load_routes_video_and_audio_to_not_implemented_error(tmp_path):
    from app.ingestion.pipeline import load

    video_path = tmp_path / "clip.mp4"
    video_path.write_bytes(b"fake video bytes")

    with pytest.raises(AnalyzerNotFoundError):
        await load(str(video_path))

    audio_path = tmp_path / "clip.mp3"
    audio_path.write_bytes(b"fake audio bytes")

    with pytest.raises(AnalyzerNotFoundError):
        await load(str(audio_path))
