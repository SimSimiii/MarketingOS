from app.ingestion.assets.image_asset import ImageAsset


class WebsiteScreenshotAsset(ImageAsset):
    url: str | None = None
