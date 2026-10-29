"""Research keeps structured audience context and rechecks earlier source leads."""

from types import SimpleNamespace

import pytest

from app.ai.base import ResearchTool
from app.market.audience_research import AudienceResearcher, LocatedSource, SourceTier
from app.market.demand import AudienceSegment, MapAssessment, MapEvidence


@pytest.mark.asyncio
async def test_structured_workflow_and_mapped_leads_survive_without_importing_product_fit():
    class Session:
        async def structured(self, **kwargs):
            self.request = kwargs
            return SimpleNamespace(sources=[
                LocatedSource(url="https://forum.example/thread", tier=SourceTier.BUYER_VOICE),
                *[LocatedSource(url=f"https://other.example/post-{i}") for i in range(10)],
            ])

    session = Session()
    segment = AudienceSegment(
        name="Course creators", who="", organization="A small education business",
        workflow="Requesting feedback from graduates after course completion",
        need="A repeatable voluntary collection request",
        angle="SECRET_PRODUCT_ANGLE", why_them="SECRET_PRODUCT_BRIDGE",
        assessment=MapAssessment(evidence=[
            MapEvidence(claim="Need", quote="I struggle to collect feedback",
                        url="https://forum.example/thread", kind="need"),
            MapEvidence(claim="Another observation", quote="I avoid a difficult ask",
                        url="https://forum.example/thread", kind="need"),
            MapEvidence(claim="Possible caution", quote="Do not force feedback",
                        url="https://guide.example/feedback", kind="counterevidence"),
        ]),
    )
    sources = await AudienceResearcher(session).locate(segment)
    candidate = session.request["variables"]["candidate"]
    for expected in [segment.organization, segment.workflow, segment.need]:
        assert expected in candidate
    assert "SECRET_PRODUCT" not in candidate
    assert session.request["tools"] == [ResearchTool.WEB_SEARCH]
    assert len(sources) == 10
    assert sources[0].url == "https://forum.example/thread"
    assert sources[0].tier is SourceTier.BUYER_VOICE
    assert sources[1].url == "https://guide.example/feedback"
    assert sources[1].tier is SourceTier.INTERPRETATION, "A map lead alone cannot certify buyer voice"
    assert len({source.url for source in sources}) == 10


@pytest.mark.asyncio
async def test_source_failures_remain_visible_in_the_persisted_research():
    from app.market.audience_research import FetchFailure, FetchResult, _corpus, _ResearchDraft
    from tests.market.test_audience_research import fetched, segment

    source = fetched("https://forum.example/thread", SourceTier.BUYER_VOICE,
                     "I collect feedback after course completion.")

    class Fetcher:
        async def fetch(self, candidates):
            return FetchResult(sources=[source], failures=[FetchFailure(
                url="https://unavailable.example/post", error="unavailable",
            )])

    class Researcher(AudienceResearcher):
        async def locate(self, chosen):
            return [LocatedSource(url="https://forum.example/thread")]

        async def synthesise(self, chosen, sources):
            return _ResearchDraft.model_validate({"situation": {
                "text": source.content,
                "evidence": [{"source_id": "S1", "quote": source.content}],
            }}), _corpus(sources)[1]

    result = await Researcher(None, Fetcher()).research(segment())
    assert any("1 readable page(s), 1 unavailable URL(s)" in warning
               for warning in result.interpretation_warnings)
