from app.ingestion.assets.base import Asset


class AudioAsset(Asset):
    """Architecture only in this phase - no AudioAnalyzer implementation
    exists yet to consume this."""

    duration_seconds: float
