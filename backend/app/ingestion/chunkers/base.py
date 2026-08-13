from abc import ABC, abstractmethod

from app.ingestion.documents import Chunk, KnowledgeDocument


class Chunker(ABC):
    """Splits a KnowledgeDocument's content into Chunks. Pure text-splitting -
    no embeddings, no vector math."""

    @abstractmethod
    def chunk(self, document: KnowledgeDocument) -> list[Chunk]:
        raise NotImplementedError
