"""Metadata changes rebind provenance without recompiling unchanged content."""

from app.ingestion.documents import SourceType
from app.knowledge.artifacts import KnowledgeArtifacts
from app.knowledge.ledger import Evidence, EvidenceContext, EvidenceKind, EvidenceLedger
from app.knowledge.store import (
    build_corpus,
    fingerprint_documents,
    fingerprint_source_context,
    refresh_provenance,
)
from app.market.capabilities import capability_ledger_fingerprint
from app.models.knowledge_document import KnowledgeDocument


def test_capability_read_adapter_uses_the_same_source_context_as_its_creator(tmp_path):
    from sqlmodel import Session, SQLModel, create_engine

    from app.knowledge.store import ArtifactScope, ArtifactStore
    from app.models.brand import Brand
    from app.services.market_service import MarketService

    engine = create_engine(f"sqlite:///{tmp_path / 'source-context.db'}")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as db:
        brand = Brand(name="SyntheticForms")
        db.add(brand)
        db.commit()
        document = KnowledgeDocument(brand_id=brand.id, title="Webhooks", source_type=SourceType.WEBSITE,
            source_url="https://forms.example/webhooks", content="Webhooks send each new submission to your endpoint.")
        db.add(document)
        db.commit()
        artifacts = KnowledgeArtifacts(evidence=EvidenceLedger(entries=[Evidence(
            id="E1", kind=EvidenceKind.FEATURE, claim=document.content, verbatim=document.content,
            document_id=str(document.id), source=document.source_url,
        )]))
        ArtifactStore(db).save(ArtifactScope(brand_id=brand.id), artifacts, fingerprint_documents([document]))
        service = MarketService(db)
        first_row, first = service.ensure_capability_profile(brand.id)
        read = service.store.latest_capability_profile(brand.id)[1]
        assert first.ledger_fingerprint == read.ledger_fingerprint
        assert service.ensure_capability_profile(brand.id)[0].id == first_row.id
        original_payload = dict(first_row.payload)
        document.source_url = "https://forms.example/current-webhooks"
        db.add(document)
        db.commit()
        second_row, second = service.ensure_capability_profile(brand.id)
        assert second_row.id != first_row.id
        assert second.ledger_fingerprint == service.store.latest_capability_profile(brand.id)[1].ledger_fingerprint
        assert first_row.payload == original_payload
    engine.dispose()


def test_source_edit_changes_context_identity_but_not_content_identity():
    document = KnowledgeDocument(title="Pricing", source_type=SourceType.WEBSITE,
        source_url="https://example.com/old-pricing", content="Uploads are included in the annual plan.")
    artifacts = KnowledgeArtifacts(evidence=EvidenceLedger(entries=[Evidence(
        id="E1", kind=EvidenceKind.FEATURE, claim=document.content, verbatim=document.content,
        source=document.source_url, document_id=str(document.id),
        context=EvidenceContext(conditions="annual plan", verification="quote_verified"),
    )]))
    previous = refresh_provenance(artifacts, [document])
    content_id = fingerprint_documents([document])
    context_id = fingerprint_source_context([document])
    document.source_url = "https://example.com/current-pricing"
    updated = refresh_provenance(previous, [document])
    assert fingerprint_documents([document]) == content_id
    assert fingerprint_source_context([document]) != context_id
    assert updated.evidence.entries[0].source == document.source_url
    assert updated.evidence.entries[0].context.conditions == "annual plan"
    assert updated.evidence.entries[0].context.verification == "source_metadata_changed_review_required"
    assert capability_ledger_fingerprint(previous.evidence) != capability_ledger_fingerprint(updated.evidence)
    assert previous.evidence.entries[0].source != document.source_url


def test_identical_content_keeps_all_sources_without_another_extraction_document():
    first = KnowledgeDocument(title="Official", source_type=SourceType.WEBSITE,
        source_url="https://example.com/guide", content="An endpoint processes each new response.")
    second = KnowledgeDocument(title="Copy", source_type=SourceType.MARKDOWN,
        source_url="https://example.com/manual", content=first.content)
    corpus = build_corpus([first, second])
    assert len(corpus.documents) == 1
    assert set(corpus.documents[0].source_aliases) == {first.source_url, second.source_url}
    artifacts = KnowledgeArtifacts(evidence=EvidenceLedger(entries=[Evidence(
        id="E1", kind=EvidenceKind.FEATURE, claim=first.content, verbatim=first.content,
        source=first.source_url, document_id=str(first.id),
    )]))
    updated = refresh_provenance(artifacts, [first, second])
    assert len(updated.evidence.entries[0].source_references) == 2
    assert len(updated.evidence.entries) == 1, "Copies are provenance, not independent corroboration."
