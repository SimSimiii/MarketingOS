from app.knowledge.ledger import Evidence, EvidenceIndex, EvidenceKind, EvidenceLedger


def test_a_discount_does_not_license_revenue_growth():
    index = EvidenceIndex(EvidenceLedger(), "Our discount is 30%.")
    assert index.unsupported("Our customers increase revenue by 30%.")
    assert not index.unsupported("Get a 30% discount.")


def test_the_compilers_paraphrase_cannot_create_a_new_number():
    index = EvidenceIndex(EvidenceLedger(entries=[Evidence(
        id="E1", kind=EvidenceKind.METRIC,
        claim="Revenue increased by 90%", verbatim="Revenue increased by 30%",
    )]))
    assert index.unsupported("Revenue increased by 90%")
    assert not index.unsupported("Revenue increased by 30%")
def test_number_cannot_be_transferred_between_explicit_named_subjects():
    from app.knowledge.ledger import EvidenceIndex, EvidenceLedger

    index = EvidenceIndex(EvidenceLedger(), "Acme's revenue grew by 30%.")
    assert index.unsupported("Beta's revenue grew by 30%.")
    assert not index.unsupported("Acme's revenue increased by 30%.")
