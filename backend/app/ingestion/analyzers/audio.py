from abc import ABC, abstractmethod

from pydantic import BaseModel

from app.ingestion.assets.audio_asset import AudioAsset
from app.ingestion.documents import KnowledgeDocument


class Transcript(BaseModel):
    text: str
    detected_language: str | None = None


class SpeechToTextProvider(ABC):
    """Architecture only in this phase - no implementation."""

    @abstractmethod
    async def transcribe(self, audio: bytes) -> Transcript:
        raise NotImplementedError


class AudioAnalyzer(ABC):
    """Architecture only in this phase - no implementation. Would use a
    SpeechToTextProvider to produce KnowledgeDocuments for an AudioAsset."""

    @abstractmethod
    async def analyze(self, asset: AudioAsset, content: bytes) -> list[KnowledgeDocument]:
        raise NotImplementedError
