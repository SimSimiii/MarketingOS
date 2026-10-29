import pytest

from app.knowledge.artifacts import BusinessProfile, CallToAction, KnowledgeArtifacts, OfferSheet
from app.knowledge.corpus import Document
from app.knowledge.ledger import Evidence, EvidenceContext, EvidenceKind, EvidenceLedger
from app.knowledge.quoted_terms import retain_billing_links, with_question


@pytest.mark.parametrize("label", ["Get 2 months free (switch to yearly)", "Save 20% with annual billing"])
def test_literal_billing_terms_keep_the_entire_condition_without_a_model(label):
    doc = Document(id="pricing", title="Pricing", source="https://example.com/pricing",
                   content=f"[{label}](#pricing) [Show more plans](#pricing)")
    entries = []
    retain_billing_links(doc, entries)
    retain_billing_links(doc, entries)
    assert len(entries) == 1
    assert entries[0].claim == label
    assert entries[0].verbatim == f"[{label}](#pricing)"
    assert entries[0].context.conditions == label
    assert entries[0].document_id == doc.id


@pytest.mark.parametrize("text,title", [
    ("```md\n[Get 2 months free (switch to yearly)](#pricing)\n```", "Pricing"),
    ("We compared [Get 2 months free (switch to yearly)](#pricing).", "Pricing"),
    ("[Get 2 months free (switch to yearly)](#pricing)", "A comparison blog"),
    ("[Get a free yearly report](#report)", "Pricing"),
])
def test_code_prose_and_noncommercial_links_do_not_create_offers(text, title):
    entries = []
    retain_billing_links(Document(id="d", title=title, content=text), entries)
    assert entries == []


def test_faq_answer_keeps_its_adjacent_question_and_full_answer():
    quote = "Open the dashboard demo."
    answer = quote + " It is sample traffic, not your own data."
    doc = Document(id="d", title="FAQ", content="Can I explore before signing up?\n\n"+answer)
    assert with_question(quote, doc) == doc.content
    assert with_question(quote, Document(id="d", title="FAQ", content="Unrelated section\n\n"+answer)) == quote


@pytest.mark.parametrize("excluded,source_kind,destination,expected", [
    (False, "official_documentation", "https://example.com/demo", True),
    (True, "official_documentation", "https://example.com/demo", False),
    (False, "third_party", "https://example.com/demo", False),
    (False, "official_documentation", "https://example.com/demo/other", False),
])
def test_action_access_facts_are_bound_to_the_exact_offered_url(excluded, source_kind, destination, expected):
    fact = Evidence(id="DEMO", kind=EvidenceKind.FEATURE, claim="Inspect the demo before signup",
        verbatim="Inspect [the dashboard](https://example.com/demo) before signing up.",
        context=EvidenceContext(subject="Widget demo", source_kind=source_kind,
            claim_scope="capability", verification="quote_verified_in_material"))
    artifacts = KnowledgeArtifacts(business=BusinessProfile(company_name="Widget"),
        evidence=EvidenceLedger(entries=[fact]),
        offer=OfferSheet(calls_to_action=[CallToAction(label="Demo",url="https://example.com/demo")]))
    selected = artifacts.evidence_for_action(destination, excluded_ids={"DEMO"} if excluded else set())
    assert bool(selected.entries) is expected
