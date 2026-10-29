"""Where compiled knowledge lives, and how a run decides whether to recompile.

Compilation is the expensive part of the system and the part that changes
least: a company's pricing page is the same page it was during their last
campaign. So artifacts are stored against the business, keyed by a fingerprint
of the material that produced them, and a run that finds the fingerprint
unchanged reads last time's work instead of paying for it again.
"""

import hashlib
import json
from dataclasses import dataclass
from uuid import UUID

from sqlmodel import Session

from app.ingestion.documents import SourceType
from app.knowledge.artifacts import KnowledgeArtifacts
from app.knowledge.corpus import Document, SourceCorpus, fold
from app.models.campaign import Campaign
from app.models.knowledge_artifacts import KnowledgeArtifactSet
from app.models.knowledge_document import KnowledgeDocument
from app.repositories.knowledge_artifact_repository import KnowledgeArtifactRepository
from app.repositories.knowledge_repository import KnowledgeDocumentRepository


@dataclass(frozen=True)
class ArtifactScope:
    """Whose knowledge this is. Exactly one of the two ids is set."""

    brand_id: UUID | None = None
    campaign_id: UUID | None = None

    @classmethod
    def for_campaign(cls, campaign: Campaign) -> "ArtifactScope":
        """A campaign attached to a brand shares that brand's knowledge; one
        without a brand keeps its own, which is the right default for a
        one-off and the reason `brand_id` is optional on Campaign."""
        if campaign.brand_id is not None:
            return cls(brand_id=campaign.brand_id)
        return cls(campaign_id=campaign.id)

    @property
    def is_brand(self) -> bool:
        return self.brand_id is not None

    def describe(self) -> str:
        return "brand" if self.is_brand else "campaign"


@dataclass(frozen=True)
class StoredArtifacts:
    artifacts: KnowledgeArtifacts
    version: int
    fingerprint: str


def current_documents(documents: list[KnowledgeDocument]) -> list[KnowledgeDocument]:
    """Read the latest fetched version of each URL, keeping stored history."""
    latest: dict[tuple, KnowledgeDocument] = {}
    others: list[KnowledgeDocument] = []
    for doc in documents:
        if doc.source_type != SourceType.WEBSITE or not doc.source_url:
            others.append(doc)
            continue
        key = (doc.brand_id, doc.campaign_id, doc.source_url)
        existing = latest.get(key)
        if existing is None or (doc.created_at.replace(tzinfo=None), str(doc.id)) > (
            existing.created_at.replace(tzinfo=None), str(existing.id)
        ):
            latest[key] = doc
    return [doc for doc in documents if doc in others or latest.get(
        (doc.brand_id, doc.campaign_id, doc.source_url)
    ) is doc]


def fingerprint_documents(documents: list[KnowledgeDocument]) -> str:
    """Identity of the material, not of the rows.

    Hashing content rather than ids or timestamps means re-uploading the same
    page does not invalidate perfectly good artifacts, while a single edited
    sentence does. Duplicates collapse for the same reason: a second, identical
    copy of a page teaches the compiler nothing the first one did not, so a run
    that re-crawled a site it had already read reuses its artifacts instead of
    paying to reach the same conclusions. Row ids deliberately play no part -
    including them made every re-ingest look like new material, which is the
    one case this is here to forgive.
    """
    digest = hashlib.sha256()
    for content_hash in sorted(
        {hashlib.sha256(document.content.encode("utf-8")).hexdigest() for document in current_documents(documents)}
    ):
        digest.update(content_hash.encode())
    return digest.hexdigest()


def fingerprint_source_context(documents: list[KnowledgeDocument]) -> str:
    """Cheap provenance identity, separate from expensive content extraction."""
    rows = sorted({(hashlib.sha256(doc.content.encode("utf-8")).hexdigest(),
                    doc.source_url or doc.title, str(doc.source_type),
                    json.dumps(doc.document_metadata or {}, sort_keys=True, default=str)) for doc in current_documents(documents)})
    return hashlib.sha256(json.dumps(rows, ensure_ascii=False).encode("utf-8")).hexdigest()


def refresh_provenance(artifacts: KnowledgeArtifacts, documents: list[KnowledgeDocument]) -> KnowledgeArtifacts:
    documents = current_documents(documents)
    fingerprint = fingerprint_source_context(documents)
    if artifacts.source_context_fingerprint == fingerprint:
        return artifacts
    updated = artifacts.model_copy(deep=True)
    material = [(doc, fold(doc.content)) for doc in documents]
    metadata_changed = bool(artifacts.source_context_fingerprint)
    for entry in updated.evidence.entries:
        quote = fold(entry.verbatim)
        matching = [doc for doc, text in material if len(quote) >= 12 and quote in text]
        entry.source_references = [{"document_id": str(doc.id), "source": doc.source_url or doc.title,
                                    "source_type": str(doc.source_type)}
                                   for doc in sorted(matching, key=lambda doc: (doc.source_url or doc.title, str(doc.id)))]
        original = next((doc for doc in matching if str(doc.id) == entry.document_id), None)
        if original is not None:
            entry.source = original.source_url or original.title
        if metadata_changed and matching and entry.context is not None:
            entry.context.verification = "source_metadata_changed_review_required"
    updated.source_context_fingerprint = fingerprint
    return updated


class ArtifactStore:
    """Reads and writes compiled knowledge for one scope."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._documents = KnowledgeDocumentRepository(session)
        self._artifacts = KnowledgeArtifactRepository(session)

    def source_documents(self, scope: ArtifactScope) -> list[KnowledgeDocument]:
        if scope.brand_id is not None:
            return current_documents(self._documents.list_for_brand(scope.brand_id))
        assert scope.campaign_id is not None
        return current_documents(self._documents.list_for_campaign(scope.campaign_id))

    def corpus_for(self, scope: ArtifactScope) -> SourceCorpus:
        return build_corpus(self.source_documents(scope))

    def load(self, scope: ArtifactScope) -> StoredArtifacts | None:
        row = (
            self._artifacts.latest_for_brand(scope.brand_id)
            if scope.brand_id is not None
            else self._artifacts.latest_for_campaign(scope.campaign_id)  # type: ignore[arg-type]
        )
        if row is None or not row.payload:
            return None
        artifacts = refresh_provenance(
            KnowledgeArtifacts.model_validate(row.payload), self.source_documents(scope)
        )
        if not artifacts.is_empty:
            # Gaps are derived rules, not model output. Cached knowledge must
            # use the same rules as a fresh compile without buying new calls.
            from app.knowledge.compiler import find_gaps

            artifacts.gaps = find_gaps(artifacts, sources=self.corpus_for(scope).documents)
        return StoredArtifacts(
            artifacts=artifacts,
            version=row.version,
            fingerprint=row.source_fingerprint,
        )

    def save(
        self, scope: ArtifactScope, artifacts: KnowledgeArtifacts, fingerprint: str
    ) -> StoredArtifacts:
        previous = self.load(scope)
        version = (previous.version + 1) if previous else 1
        artifacts.version = version
        artifacts = refresh_provenance(artifacts, self.source_documents(scope))
        self._artifacts.create(
            KnowledgeArtifactSet(
                brand_id=scope.brand_id,
                campaign_id=scope.campaign_id,
                version=version,
                source_fingerprint=fingerprint,
                payload=artifacts.model_dump(mode="json"),
            )
        )
        return StoredArtifacts(artifacts=artifacts, version=version, fingerprint=fingerprint)


def build_corpus(documents: list[KnowledgeDocument]) -> SourceCorpus:
    """Turn stored rows into the retrievable corpus the roles read.

    Chunking happens here rather than at ingestion time on purpose: it is
    string splitting over a few hundred kilobytes, it costs nothing next to a
    single model call, and doing it at read time means changing the chunking
    strategy does not require a migration or a re-ingest.
    """
    # Legacy imports can contain duplicates even though ingestion now deduplicates.
    # Match the fingerprint's content identity and preserve the first citation source.
    unique: dict[str, KnowledgeDocument] = {}
    aliases: dict[str, set[str]] = {}
    for document in current_documents(documents):
        if document.content.strip():
            unique.setdefault(document.content, document)
            aliases.setdefault(document.content, set()).add(document.source_url or document.title)
    return SourceCorpus.from_documents(
        [
            Document(
                id=str(document.id),
                title=document.title,
                content=document.content,
                source=document.source_url or document.title,
                source_type=str(document.source_type),
                source_aliases=tuple(sorted(aliases[document.content])),
                source_issues=tuple((document.document_metadata or {}).get("content_issues", [])),
            )
            for document in unique.values()
        ]
    )
