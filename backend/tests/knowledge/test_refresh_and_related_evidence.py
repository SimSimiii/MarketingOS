from datetime import UTC, datetime, timedelta

from app.ingestion.documents import SourceType
from app.knowledge.decision_context import select_evidence
from app.knowledge.ledger import Evidence, EvidenceContext, EvidenceKind, EvidenceLedger
from app.knowledge.store import build_corpus, fingerprint_documents
from app.models.knowledge_document import KnowledgeDocument


def test_refetched_url_replaces_old_material_without_deleting_history():
    now = datetime.now(UTC)
    old = KnowledgeDocument(title="Pricing", source_type=SourceType.WEBSITE,
        source_url="https://example.com/pricing", content="An old plan costs $10.", created_at=now-timedelta(days=1))
    new = KnowledgeDocument(title="Pricing", source_type=SourceType.WEBSITE,
        source_url=old.source_url, content="The current plan costs $20.", created_at=now)
    for rows in ([old, new], [new, old]):
        corpus = build_corpus(rows)
        assert [doc.content for doc in corpus.documents] == [new.content]
        assert fingerprint_documents(rows) == fingerprint_documents([new])
    assert old.content == "An old plan costs $10."


def test_distinct_sources_and_explicit_uploads_keep_conflicting_terms():
    rows = [KnowledgeDocument(title="Terms", source_type=kind, source_url=url, content=text)
            for kind, url, text in [(SourceType.WEBSITE,"https://example.com/a","Old website wording."),
                                    (SourceType.WEBSITE,"https://example.com/b","Other website wording."),
                                    (SourceType.MARKDOWN,"https://example.com/a","Uploaded wording.")]]
    assert len(build_corpus(rows).documents) == 3


def test_cost_and_counting_questions_retrieve_existing_terms_and_mechanisms_within_cap():
    facts = [Evidence(id=f"F{i:02}", kind=EvidenceKind.FEATURE,
        claim="Founder trusts site numbers and cost decisions", verbatim="Founder trusts site numbers and cost decisions") for i in range(60)]
    facts += [Evidence(id="ANNUAL",kind=EvidenceKind.PRICE,claim="Yearly billing discount: two months free",
                      verbatim="Yearly billing discount: two months free"),
              Evidence(id="RENEW",kind=EvidenceKind.PRICE,claim="Annual renewal and cancellation terms",
                      verbatim="Annual renewal and cancellation terms"),
              Evidence(id="BOTS",kind=EvidenceKind.FEATURE,claim="Automatic bot filtering excludes nonhuman requests",
                      verbatim="Automatic bot filtering excludes nonhuman requests")]
    result = select_evidence(EvidenceLedger(entries=facts), "Founder cannot trust the numbers and finds the cost expensive", cap=12)
    assert len(result.ledger.entries) == 12
    assert {"ANNUAL","BOTS"} <= result.ledger.ids


def test_a_short_problem_keeps_its_mechanism_among_a_longer_problem_without_promoting_outcomes():
    common = "Analytics traffic reports filters campaigns website"
    facts = [Evidence(id=f"F{i:02}",kind=EvidenceKind.FEATURE,claim=common,verbatim=common,
        context=EvidenceContext(source_kind="vendor_statement",claim_scope="capability")) for i in range(60)]
    facts += [Evidence(id="HOST",kind=EvidenceKind.FEATURE,
        claim="A hosted service without self-hosted server maintenance",
        verbatim="A hosted service without self-hosted server maintenance",
        context=EvidenceContext(source_kind="official_documentation",claim_scope="capability")),
        Evidence(id="OUTCOME",kind=EvidenceKind.FEATURE,claim="Self-hosted maintenance hosted service",
            verbatim="Self-hosted maintenance hosted service",
            context=EvidenceContext(source_kind="customer_statement",claim_scope="customer_outcome"))]
    ledger = EvidenceLedger(entries=facts)
    short = "Stop self-hosted maintenance"
    query = common+" "+short
    assert "HOST" not in select_evidence(ledger,query,cap=8).ledger.ids
    selected = select_evidence(ledger,query,problem_queries=[common,short],cap=8).ledger
    assert len(selected.entries) == 8
    assert "HOST" in selected.ids
    assert "OUTCOME" not in selected.ids
    assert "HOST" not in select_evidence(ledger,query,problem_queries=[short],excluded_ids={"HOST"},cap=8).ledger.ids
