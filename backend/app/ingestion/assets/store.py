from abc import ABC, abstractmethod

from app.ingestion.assets.base import Asset
from app.ingestion.exceptions import AssetNotFoundError


class AssetStore(ABC):
    """Persistence boundary for Asset metadata. Never stores raw bytes."""

    @abstractmethod
    async def add_asset(self, asset: Asset) -> Asset:
        raise NotImplementedError

    @abstractmethod
    async def get_asset(self, asset_id: str) -> Asset:
        raise NotImplementedError

    @abstractmethod
    async def list_assets(self) -> list[Asset]:
        raise NotImplementedError


class InMemoryAssetStore(AssetStore):
    """Dict-backed AssetStore. No persistence beyond process lifetime, and no
    binary content - only the Asset metadata objects themselves."""

    def __init__(self) -> None:
        self._assets: dict[str, Asset] = {}

    async def add_asset(self, asset: Asset) -> Asset:
        self._assets[asset.id] = asset
        return asset

    async def get_asset(self, asset_id: str) -> Asset:
        try:
            return self._assets[asset_id]
        except KeyError as exc:
            raise AssetNotFoundError(f"No asset with id '{asset_id}'", asset_id=asset_id) from exc

    async def list_assets(self) -> list[Asset]:
        return list(self._assets.values())
