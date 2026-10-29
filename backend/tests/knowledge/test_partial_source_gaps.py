from app.knowledge.artifacts import KnowledgeArtifacts, OfferSheet
from app.knowledge.compiler import find_gaps
from app.knowledge.corpus import Document


def test_free_entry_does_not_hide_unreadable_paid_plan_rows():
    artifacts = KnowledgeArtifacts(offer=OfferSheet(free_entry="A free plan is available"))
    source = Document(id="pricing", title="Plans", source="https://example.test/pricing",
                      content="Compare paid plans\n\n" + "null:\n\n" * 20)
    gaps = find_gaps(artifacts, sources=[source]).gaps
    assert not any(gap.id == "G-price" for gap in gaps)
    assert any("Dynamic values" in gap.missing and source.source in gap.missing for gap in gaps)
    artifacts.gaps = find_gaps(artifacts, sources=[source])
    assert any(gap.id.startswith("G-source-") for gap in find_gaps(artifacts).gaps)
    assert not any(gap.id.startswith("G-source-") for gap in find_gaps(artifacts, sources=[]).gaps)


def test_failed_crawl_metadata_survives_even_with_substantive_homepage():
    source = Document(id="home", title="Home", source="https://example.test/",
                      content="A substantive product page. " * 20, source_issues=("partial_crawl",))
    assert any("corpus is partial" in gap.missing for gap in find_gaps(KnowledgeArtifacts(), sources=[source]).gaps)
