"""Commercial excerpts must keep an amount together with its entitlement."""

from app.knowledge.corpus import Document, SourceCorpus


def test_many_commercial_sections_do_not_slice_the_pricing_row_into_prefixes():
    prices = "$15/month Up to 100,000 monthly pageviews $25/month Up to 200,000 monthly pageviews $45/month Up to 500,000 monthly pageviews"
    content = "# Pricing\n\n" + "Read about our plans and billing.\n\n" * 160
    content += "## Rates\n\n" + prices
    content += "\n\n## Billing questions\n\n" + "Each plan includes the same tools.\n\n" * 160
    corpus = SourceCorpus.from_documents([Document(id="p", title="Pricing", content=content)])
    digest = corpus.digest(3300)
    assert prices in digest
    assert len(digest) < 3500  # document heading and explicit excerpt metadata
    assert "excerpt from" in digest
