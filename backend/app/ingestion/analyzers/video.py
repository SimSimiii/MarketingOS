from abc import ABC, abstractmethod

from app.ingestion.assets.video_asset import VideoAsset
from app.ingestion.documents import KnowledgeDocument


class FrameExtractor(ABC):
    """Architecture only in this phase - no implementation. Would pull
    representative frames out of a VideoAsset for image-style analysis."""

    @abstractmethod
    async def extract_frames(self, asset: VideoAsset, content: bytes) -> list[bytes]:
        raise NotImplementedError


class VideoAnalyzer(ABC):
    """Architecture only in this phase - no implementation. Would combine a
    FrameExtractor with image analysis (and eventually audio/transcript
    analysis) to produce KnowledgeDocuments for a video."""

    @abstractmethod
    async def analyze(self, asset: VideoAsset, content: bytes) -> list[KnowledgeDocument]:
        raise NotImplementedError
