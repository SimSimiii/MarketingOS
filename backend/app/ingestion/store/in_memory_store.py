from app.ingestion.documents import KnowledgeDocument
from app.ingestion.exceptions import DocumentNotFoundError, DuplicateDocumentError
from app.ingestion.store.base import KnowledgeStore


class InMemoryKnowledgeStore(KnowledgeStore):
    """Dict-backed KnowledgeStore. No persistence beyond process lifetime."""

    def __init__(self) -> None:
        self._documents: dict[str, KnowledgeDocument] = {}
        self._hash_to_id: dict[str, str] = {}

    async def add_document(self, document: KnowledgeDocument) -> KnowledgeDocument:
        content_hash = document.metadata.get("content_hash")
        if content_hash and content_hash in self._hash_to_id:
            existing_id = self._hash_to_id[content_hash]
            raise DuplicateDocumentError(
                f"Document with content hash '{content_hash}' already exists",
                existing_id=existing_id,
            )

        self._documents[document.id] = document
        if content_hash:
            self._hash_to_id[content_hash] = document.id
        return document

    async def remove_document(self, document_id: str) -> None:
        document = self._documents.pop(document_id, None)
        if document is None:
            raise DocumentNotFoundError(f"No document with id '{document_id}'", document_id=document_id)
        content_hash = document.metadata.get("content_hash")
        if content_hash:
            self._hash_to_id.pop(content_hash, None)

    async def list_documents(self) -> list[KnowledgeDocument]:
        return list(self._documents.values())

    async def get_document(self, document_id: str) -> KnowledgeDocument:
        try:
            return self._documents[document_id]
        except KeyError as exc:
            raise DocumentNotFoundError(
                f"No document with id '{document_id}'", document_id=document_id
            ) from exc

    async def search(self, query: str) -> list[KnowledgeDocument]:
        terms = [term for term in query.lower().split() if term]
        if not terms:
            return []

        scored: list[tuple[int, KnowledgeDocument]] = []
        for document in self._documents.values():
            haystack = f"{document.title}\n{document.content}".lower()
            score = sum(haystack.count(term) for term in terms)
            if score > 0:
                scored.append((score, document))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [document for _, document in scored]
