from app.ingestion.assets.base import Asset


class ImageAsset(Asset):
    width: int
    height: int
