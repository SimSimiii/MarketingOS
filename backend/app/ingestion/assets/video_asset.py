from app.ingestion.assets.base import Asset


class VideoAsset(Asset):
    """Architecture only in this phase - no VideoAnalyzer implementation
    exists yet to consume this."""

    duration_seconds: float
    fps: float
