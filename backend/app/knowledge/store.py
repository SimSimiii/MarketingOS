"""Where compiled knowledge lives, and how a run decides whether to recompile.

Compilation is the expensive part of the system and the part that changes
least: a company's pricing page is the same page it was during their last
campaign. So artifacts are stored against the business, keyed by a fingerprint
of the material that produced them, and a run that finds the fingerprint
unchanged reads last time's work instead of paying for it again.
"""

import hashlib
from dataclasses import dataclass
from uuid import UUID

from sqlmodel import Session

from app.knowledge.artifacts import KnowledgeArtifacts
from app.knowledge.corpus import Document, SourceCorpus
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


def fingerprint_documents(documents: list[KnowledgeDocument]) -> str:
    """Identity of the material, not of the rows.

    Hashing content rather than ids or timestamps means re-uploading the same
    page does not invalidate perfectly good artifacts, while a single edited
    sentence does.
    """
    digest = hashlib.sha256()
    for document in sorted(documents, key=lambda item: str(item.id)):
        digest.update(str(document.id).encode())
        digest.update(hashlib.sha256(document.content.encode("utf-8")).digest())
    return digest.hexdigest()


class ArtifactStore:
    """Reads and writes compiled knowledge for one scope."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._documents = KnowledgeDocumentRepository(session)
        self._artifacts = KnowledgeArtifactRepository(session)

    def source_documents(self, scope: ArtifactScope) -> list[KnowledgeDocument]:
        if scope.brand_id is not None:
            return self._documents.list_for_brand(scope.brand_id)
        assert scope.campaign_id is not None
        return self._documents.list_for_campaign(scope.campaign_id)

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
        return StoredArtifacts(
            artifacts=KnowledgeArtifacts.model_validate(row.payload),
            version=row.version,
            fingerprint=row.source_fingerprint,
        )

    def save(
        self, scope: ArtifactScope, artifacts: KnowledgeArtifacts, fingerprint: str
    ) -> StoredArtifacts:
        previous = self.load(scope)
        version = (previous.version + 1) if previous else 1
        artifacts.version = version
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
    return SourceCorpus.from_documents(
        [
            Document(
                id=str(document.id),
                title=document.title,
                content=document.content,
                source=document.source_url or document.title,
                source_type=str(document.source_type),
            )
            for document in documents
            if document.content.strip()
        ]
    )
