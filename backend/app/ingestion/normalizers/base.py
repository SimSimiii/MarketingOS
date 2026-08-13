from abc import ABC, abstractmethod

from app.ingestion.documents import KnowledgeDocument, RawDocument


class Normalizer(ABC):
    """Turns a RawDocument into the canonical KnowledgeDocument."""

    @abstractmethod
    async def normalize(self, raw: RawDocument) -> KnowledgeDocument:
        raise NotImplementedError
