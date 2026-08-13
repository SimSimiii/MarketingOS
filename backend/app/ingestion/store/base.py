from abc import ABC, abstractmethod

from app.ingestion.documents import KnowledgeDocument


class KnowledgeStore(ABC):
    """Persistence boundary for KnowledgeDocuments. Every method is async so
    a future Postgres+pgvector implementation is a drop-in replacement."""

    @abstractmethod
    async def add_document(self, document: KnowledgeDocument) -> KnowledgeDocument:
        """Stores a document. Raises DuplicateDocumentError if a document
        with the same content hash already exists."""
        raise NotImplementedError

    @abstractmethod
    async def remove_document(self, document_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    async def list_documents(self) -> list[KnowledgeDocument]:
        raise NotImplementedError

    @abstractmethod
    async def get_document(self, document_id: str) -> KnowledgeDocument:
        raise NotImplementedError

    @abstractmethod
    async def search(self, query: str) -> list[KnowledgeDocument]:
        """Keyword search - no embeddings, no ranking model."""
        raise NotImplementedError
