"""Persist already verified official material for a campaign or a brand."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING
from uuid import UUID

from sqlmodel import Session

from app.ingestion.documents import SourceType
from app.knowledge.artifacts import KnowledgeArtifacts
from app.knowledge.store import ArtifactScope, ArtifactStore, StoredArtifacts, fingerprint_documents
from app.models.knowledge_document import KnowledgeDocument
from app.repositories.knowledge_repository import KnowledgeDocumentRepository

if TYPE_CHECKING:
    from app.market.material_research import MaterialRecovery


def persist_recovered_material(
    session: Session, scope: ArtifactScope, recovery: MaterialRecovery,
    artifacts: KnowledgeArtifacts, *, owner_id: UUID | None,
    documents: list[KnowledgeDocument] | None = None,
) -> StoredArtifacts:
    """File verified pages and the enriched ledger without a full compilation.

    A supplied document list is extended in place, preserving the campaign
    gateway's existing snapshot/fingerprint behavior.
    """
    store = ArtifactStore(session)
    documents = store.source_documents(scope) if documents is None else documents
    repository = KnowledgeDocumentRepository(session)
    enriched = artifacts.model_copy(deep=True)
    by_hash = {hashlib.sha256(document.content.encode("utf-8")).hexdigest(): document
               for document in documents}
    persisted_ids: list[str] = []
    source_documents: dict[str, str] = {}
    for source in recovery.sources:
        document = by_hash.get(source.content_hash)
        if document is None:
            document = repository.create(KnowledgeDocument(
                owner_id=owner_id, brand_id=scope.brand_id, campaign_id=scope.campaign_id,
                title=source.title or source.final_url, source_type=SourceType.WEBSITE,
                content=source.content, source_url=source.final_url,
                word_count=len(source.content.split()),
                document_metadata={"automatically_discovered": True,
                                   "recovered_for": recovery.gap, "content_hash": source.content_hash},
            ))
            documents.append(document)
            by_hash[source.content_hash] = document
        document_id = str(document.id)
        persisted_ids.append(document_id)
        source_documents[source.final_url.rstrip("/").lower()] = document_id
    enriched.source_document_ids = [item for item in enriched.source_document_ids if not item.startswith("auto:")]
    for document_id in persisted_ids:
        if document_id not in enriched.source_document_ids:
            enriched.source_document_ids.append(document_id)
    for entry in enriched.evidence.entries:
        if document_id := source_documents.get(entry.source.rstrip("/").lower()):
            entry.document_id = document_id
    return store.save(scope, enriched, fingerprint_documents(documents))
