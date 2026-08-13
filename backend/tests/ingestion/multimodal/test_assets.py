from datetime import UTC, datetime

import pytest

from app.ingestion.assets.base import Asset
from app.ingestion.assets.image_asset import ImageAsset
from app.ingestion.assets.loader import AssetLoader
from app.ingestion.assets.store import InMemoryAssetStore
from app.ingestion.assets.website_screenshot_asset import WebsiteScreenshotAsset
from app.ingestion.exceptions import AssetNotFoundError, LoaderError


def test_asset_has_required_fields():
    asset = Asset(
        source="x.png",
        filename="x.png",
        mime_type="image/png",
        size=100,
        checksum="abc",
        created_at=datetime.now(UTC),
    )
    assert asset.id
    assert asset.metadata == {}


def test_image_asset_adds_dimensions():
    asset = ImageAsset(
        source="x.png",
        filename="x.png",
        mime_type="image/png",
        size=100,
        checksum="abc",
        created_at=datetime.now(UTC),
        width=800,
        height=600,
    )
    assert asset.width == 800
    assert asset.height == 600


def test_website_screenshot_asset_is_an_image_asset_with_url():
    asset = WebsiteScreenshotAsset(
        source="shot.png",
        filename="shot.png",
        mime_type="image/png",
        size=100,
        checksum="abc",
        created_at=datetime.now(UTC),
        width=1280,
        height=720,
        url="https://example.com",
    )
    assert isinstance(asset, ImageAsset)
    assert asset.url == "https://example.com"


def test_asset_loader_computes_metadata_from_file(png_path):
    asset, content = AssetLoader().load_image(str(png_path))

    assert asset.filename == "product.png"
    assert asset.mime_type == "image/png"
    assert asset.width == 12
    assert asset.height == 8
    assert asset.size == len(content)
    assert len(asset.checksum) == 64  # sha256 hex digest


def test_asset_loader_missing_file_raises_loader_error(tmp_path):
    with pytest.raises(LoaderError):
        AssetLoader().load_image(str(tmp_path / "missing.png"))


def test_asset_loader_rejects_non_image_bytes(tmp_path):
    path = tmp_path / "fake.png"
    path.write_bytes(b"not an image")
    with pytest.raises(LoaderError):
        AssetLoader().load_image(str(path))


@pytest.mark.asyncio
async def test_asset_store_add_then_get():
    store = InMemoryAssetStore()
    asset = Asset(
        source="x.png",
        filename="x.png",
        mime_type="image/png",
        size=1,
        checksum="abc",
        created_at=datetime.now(UTC),
    )
    await store.add_asset(asset)
    fetched = await store.get_asset(asset.id)
    assert fetched == asset


@pytest.mark.asyncio
async def test_asset_store_get_missing_raises():
    store = InMemoryAssetStore()
    with pytest.raises(AssetNotFoundError):
        await store.get_asset("missing-id")


@pytest.mark.asyncio
async def test_asset_store_list_assets():
    store = InMemoryAssetStore()
    asset1 = Asset(
        source="a.png", filename="a.png", mime_type="image/png", size=1,
        checksum="a", created_at=datetime.now(UTC),
    )
    asset2 = Asset(
        source="b.png", filename="b.png", mime_type="image/png", size=1,
        checksum="b", created_at=datetime.now(UTC),
    )
    await store.add_asset(asset1)
    await store.add_asset(asset2)
    assert {a.id for a in await store.list_assets()} == {asset1.id, asset2.id}
