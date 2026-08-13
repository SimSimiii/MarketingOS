"""Retrieval, which is what replaced newest-first truncation."""

from app.knowledge.corpus import Document, SourceCorpus, split_document

PRICING = """# Pricing

Team is $29 per month, billed annually.

## Enterprise

Custom pricing, starts around $2,000 a month with a dedicated engineer.
"""

HOME = """# Notewright

Release notes without the Friday afternoon.

## How it works

Point it at a branch. It reads the commits you already pushed.
"""


def corpus() -> SourceCorpus:
    return SourceCorpus.from_documents(
        [
            Document(id="d1", title="Home", content=HOME, source="https://x.com"),
            Document(id="d2", title="Pricing", content=PRICING, source="https://x.com/pricing"),
        ]
    )


def test_a_document_is_split_at_its_headings():
    chunks = split_document(Document(id="d", title="Pricing", content=PRICING))
    headings = [chunk.heading for chunk in chunks]
    assert "Pricing" in headings
    assert "Enterprise" in headings


def test_a_long_section_is_packed_rather_than_left_as_one_blob():
    """A heading-only split leaves a single-heading page indivisible, which is
    the same all-or-nothing problem retrieval exists to remove."""
    body = "# One heading\n\n" + "\n\n".join(f"Paragraph number {n} of some length here." * 6 for n in range(20))
    chunks = split_document(Document(id="d", title="Long", content=body))
    assert len(chunks) > 1
    assert all(len(chunk.content) < 2_000 for chunk in chunks)


def test_search_finds_the_section_that_answers_the_question():
    """The failure the old truncation guaranteed: a price halfway down a page
    that no model could ever see."""
    hits = corpus().search("what does the enterprise plan cost", limit=2)
    assert hits
    assert "2,000" in hits[0].content


def test_rare_terms_outweigh_common_ones():
    hits = corpus().search("enterprise", limit=1)
    assert hits[0].heading == "Enterprise"


def test_search_on_nothing_returns_nothing():
    assert corpus().search("") == []
    assert SourceCorpus().search("anything") == []


def test_the_digest_gives_every_document_a_share_of_the_budget():
    """Compiling means having looked at all of it once, so the first document
    must not be able to eat the whole budget."""
    documents = [
        Document(id=str(n), title=f"Doc {n}", content=f"# Doc {n}\n\n" + ("word " * 4_000))
        for n in range(4)
    ]
    digest = SourceCorpus.from_documents(documents).digest(budget_chars=8_000)
    for n in range(4):
        assert f"Doc {n}" in digest


def test_the_full_text_is_available_for_checks_that_must_not_miss_anything():
    assert "2,000" in corpus().text
    assert "Point it at a branch" in corpus().text
