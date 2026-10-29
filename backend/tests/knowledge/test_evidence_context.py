"""Synthetic, contrasting offers: fact presence never erases its scope."""

import pytest

from app.knowledge.artifacts import KnowledgeArtifacts
from app.knowledge.base import build_knowledge_base
from app.knowledge.compiler import KnowledgeCompiler
from app.knowledge.corpus import Document, SourceCorpus
from app.knowledge.ledger import Evidence, EvidenceContext, EvidenceKind, EvidenceLedger
from app.marketing.preflight import assess
from tests.knowledge.test_compiler import compiler_provider, evidence_answer, voice_answer
from tests.marketing.conftest import make_session


@pytest.mark.asyncio
async def test_compilation_preserves_offer_terms_and_verifies_only_quote_presence():
    quote = "Pro includes exports for €29 per seat per month, billed annually, excluding VAT."
    context = {
        "subject": "Pro plan", "source_kind": "vendor_statement", "claim_scope": "offer",
        "conditions": "EUR; per seat; monthly equivalent; billed annually; excluding VAT",
        "temporal_scope": "Pricing page dated 2025; current price unknown",
        "limitations": "Exports are included; this is not the standalone price of exports",
        "verification": "independently proved current and universally available",
    }
    provider = compiler_provider(evidence=evidence_answer({
        "kind": "price", "claim": quote, "verbatim": quote,
        "document_id": "d1", "context": context,
    }), voice=voice_answer())
    ledger, _ = await KnowledgeCompiler(make_session(provider))._evidence(
        SourceCorpus.from_documents([Document(
            id="d1", title="Synthetic pricing", content=quote,
            source="https://synthetic.example/pricing",
        )])
    )
    entry = ledger.entries[0]
    assert entry.context.subject == "Pro plan"
    assert entry.context.conditions == context["conditions"]
    assert entry.context.temporal_scope == context["temporal_scope"]
    assert entry.context.verification == "quote_verified_in_material"
    rendered = ledger.render()
    assert "not the standalone price" in rendered
    assert "current price unknown" in rendered
    assert "https://synthetic.example/pricing" in rendered


def test_legacy_artifacts_remain_readable_with_unknown_scope():
    entry = Evidence.model_validate({
        "id": "E1", "kind": "feature", "claim": "Includes exports",
        "verbatim": "Pro includes exports.",
    })
    assert entry.context is None
    rendered = EvidenceLedger(entries=[entry]).render()
    assert "context not recorded" in rendered
    assert "do not claim novelty or current terms without dated support" in rendered


@pytest.mark.asyncio
async def test_compiler_binds_quotes_to_their_named_source_and_recovers_unique_missing_ids():
    docs = SourceCorpus.from_documents([
        Document(id="d1", title="Manual", content="The press tray is stainless steel.",
                 source="https://synthetic.example/manual"),
        Document(id="d2", title="Pricing", content="The press is available for EUR 390.",
                 source="https://synthetic.example/pricing"),
    ])
    provider = compiler_provider(evidence=evidence_answer(
        {"claim": "Wrong source", "verbatim": "The press is available for EUR 390.",
         "document_id": "d1"},
        {"claim": "Unknown source", "verbatim": "The press is available for EUR 390.",
         "document_id": "missing"},
        {"claim": "Recovered source", "verbatim": "The press is available for EUR 390."},
    ), voice=voice_answer())
    ledger, intake = await KnowledgeCompiler(make_session(provider))._evidence(docs)
    assert [entry.claim for entry in ledger.entries] == ["Recovered source"]
    assert ledger.entries[0].document_id == "d2"
    assert ledger.entries[0].source == "https://synthetic.example/pricing"
    assert intake.unverifiable == 2


@pytest.mark.parametrize("claim", [
    "The app exports the selected invoices as CSV.",
    "The press has an adjustable stainless steel fruit tray.",
])
def test_a_documented_capability_needs_no_testimonial_to_pass_preflight(claim):
    entry = Evidence(
        id="E1", kind=EvidenceKind.FEATURE, claim=claim, verbatim=claim,
        source="https://synthetic.example/manual",
        context=EvidenceContext(source_kind="official_documentation", claim_scope="capability"),
    )
    artifacts = KnowledgeArtifacts(evidence=EvidenceLedger(entries=[entry]))
    posture = assess(artifacts)
    assert posture.has_checkable
    assert not posture.has_proof
    assert not posture.nothing_to_argue_from
    assert "do not establish time saved" in posture.render_for_strategy()
    base_entry = build_knowledge_base(artifacts).entries[0]
    assert base_entry.context == entry.context


def test_customer_results_and_vendor_comparisons_keep_their_subject_and_limits():
    ledger = EvidenceLedger(entries=[
        Evidence(
            id="E1", kind=EvidenceKind.METRIC, claim="A bakery reported 20% less waste",
            verbatim="Our pilot bakery reported 20% less waste during May.",
            context=EvidenceContext(
                subject="Pilot bakery", source_kind="customer_statement",
                claim_scope="customer_outcome", conditions="one pilot bakery",
                temporal_scope="May", limitations="not an expected result for all bakeries",
            ),
        ),
        Evidence(
            id="E2", kind=EvidenceKind.FEATURE, claim="Vendor says Rival lacks offline mode",
            verbatim="Unlike Rival, we offer offline mode.",
            context=EvidenceContext(
                subject="Rival", source_kind="vendor_comparison", claim_scope="comparison",
                limitations="vendor assertion; Rival's current capability not independently checked",
            ),
        ),
    ])
    roundtrip = EvidenceLedger.model_validate_json(ledger.model_dump_json())
    assert roundtrip.entries[0].context.subject == "Pilot bakery"
    assert roundtrip.entries[1].context.source_kind == "vendor_comparison"
    assert "not an expected result for all bakeries" in roundtrip.render()
    assert "not independently checked" in roundtrip.render()
