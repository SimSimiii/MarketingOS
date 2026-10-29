"""What counts as new material, and what is the same page twice.

The fingerprint is the only thing standing between a user who chose "reuse
what's already compiled" and a compile they did not ask for, so these are
tests about identity: two rows holding the same words are one fact about the
business, however many times it was filed.
"""

from types import SimpleNamespace

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.ingestion.documents import SourceType
from app.knowledge.store import fingerprint_documents
from app.models.brand import Brand
from app.models.knowledge_document import KnowledgeDocument
from app.services.knowledge_service import KnowledgeService

SITE = "Notewright drafts a release note in about nine seconds. Team is $29/month."


def test_identical_page_refreshes_collection_warnings_without_changing_facts(session, brand):
    page = SimpleNamespace(content=SITE, source=SourceType.WEBSITE, url="https://example.test/",
                           title="Home", metadata={"content_issues": ["partial_crawl"]})
    first = KnowledgeService(session)._persist(page, None, brand.id, None)
    original_date = first.created_at
    assert first.document_metadata["content_issues"] == ["partial_crawl"]
    page.metadata = {"content_issues": []}
    refreshed = KnowledgeService(session)._persist(page, None, brand.id, None)
    assert refreshed.id == first.id and refreshed.created_at == original_date
    assert refreshed.content == SITE and refreshed.document_metadata["content_issues"] == []


def test_cached_gap_rules_refresh_without_changing_saved_evidence_or_version(session, brand):
    from app.knowledge.artifacts import Gap, GapReport, KnowledgeArtifacts
    from app.knowledge.ledger import Evidence, EvidenceKind, EvidenceLedger
    from app.knowledge.store import ArtifactScope, ArtifactStore
    from app.models.knowledge_artifacts import KnowledgeArtifactSet

    artifacts = KnowledgeArtifacts(
        evidence=EvidenceLedger(entries=[Evidence(
            id="E1", kind=EvidenceKind.PRICE, claim="Bag costs 45€.", verbatim="Bag 45€",
        )]),
        gaps=GapReport(gaps=[Gap(id="G-price", missing="No price found", impact="Cannot name a price")]),
    )
    store = ArtifactStore(session)
    scope = ArtifactScope(brand_id=brand.id)
    saved = store.save(scope, artifacts, "same-sources")
    loaded = store.load(scope)
    assert loaded is not None
    assert loaded.version == saved.version == 1
    assert loaded.fingerprint == "same-sources"
    assert loaded.artifacts.evidence.model_dump() == saved.artifacts.evidence.model_dump()
    assert "G-price" not in {gap.id for gap in loaded.artifacts.gaps.gaps}
    row = session.exec(select(KnowledgeArtifactSet)).one()
    assert row.payload["gaps"]["gaps"][0]["id"] == "G-price"


def document(content: str) -> KnowledgeDocument:
    return KnowledgeDocument(title="Home", source_type=SourceType.WEBSITE, content=content)


@pytest.fixture
def session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture
def brand(session: Session) -> Brand:
    brand = Brand(name="Notewright")
    session.add(brand)
    session.commit()
    session.refresh(brand)
    return brand


def test_the_same_page_filed_twice_does_not_change_the_fingerprint():
    """The bug this exists for: the fingerprint used to include the row id, so
    re-adding a brand's website - which happens every time a campaign is
    created for it - invalidated artifacts that were still perfectly good."""
    once = [document(SITE)]
    twice = [document(SITE), document(SITE)]

    assert fingerprint_documents(once) == fingerprint_documents(twice)


def test_an_edited_sentence_changes_the_fingerprint():
    assert fingerprint_documents([document(SITE)]) != fingerprint_documents(
        [document(SITE.replace("$29", "$39"))]
    )


def test_new_material_changes_the_fingerprint():
    assert fingerprint_documents([document(SITE)]) != fingerprint_documents(
        [document(SITE), document("Solo is $9/month.")]
    )


def test_the_order_documents_come_back_in_does_not_matter():
    """Nothing promises the repository returns rows in a stable order, and a
    fingerprint that depended on it would recompile at random."""
    a, b = document(SITE), document("Solo is $9/month.")
    assert fingerprint_documents([a, b]) == fingerprint_documents([b, a])


@pytest.mark.asyncio
async def test_ingesting_the_same_text_twice_files_it_once(session: Session, brand: Brand):
    first = await KnowledgeService(session).ingest_source(SITE, brand_id=brand.id)
    second = await KnowledgeService(session).ingest_source(SITE, brand_id=brand.id)

    assert [doc.id for doc in first] == [doc.id for doc in second]
    assert len(KnowledgeService(session).list_documents(brand_id=brand.id)) == 1


@pytest.mark.asyncio
async def test_genuinely_new_material_is_still_filed(session: Session, brand: Brand):
    await KnowledgeService(session).ingest_source(SITE, brand_id=brand.id)
    await KnowledgeService(session).ingest_source("Solo is $9/month.", brand_id=brand.id)

    assert len(KnowledgeService(session).list_documents(brand_id=brand.id)) == 2


@pytest.mark.asyncio
async def test_one_brands_material_does_not_deduplicate_another_brands(
    session: Session, brand: Brand
):
    """Two companies can say the same thing. Filing it under one of them is
    not a reason for the other to be missing it."""
    other = Brand(name="Foldwork")
    session.add(other)
    session.commit()
    session.refresh(other)

    await KnowledgeService(session).ingest_source(SITE, brand_id=brand.id)
    await KnowledgeService(session).ingest_source(SITE, brand_id=other.id)

    assert len(KnowledgeService(session).list_documents(brand_id=brand.id)) == 1
    assert len(KnowledgeService(session).list_documents(brand_id=other.id)) == 1
