"""The process-owned and deterministic trust boundary for audience research."""

import hashlib
from datetime import UTC, datetime

import httpx
import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.ai.base import ResearchTool
from app.knowledge.artifacts import Grounding
from app.market.audience_research import (
    AudienceProblem,
    AudienceResearch,
    AudienceResearcher,
    AudienceResearchError,
    BuyerPhrase,
    EvidenceReference,
    FetchedSource,
    FixedURLFetcher,
    LocatedSource,
    SourcedObservation,
    SourceTier,
    URLSafetyError,
    _ResearchDraft,
    bounded_sources,
    validate_public_url,
    verify_research,
)
from app.market.demand import AudienceSegment, DemandMap, SegmentKind
from app.market.store import MarketStore
from app.models.brand import Brand
from app.services import market_service
from app.services.market_service import JobStatus
from tests.market.conftest import ScriptedProvider


async def public_resolver(_host: str) -> list[str]:
    return ["93.184.216.34"]


def segment(**overrides: object) -> AudienceSegment:
    payload: dict = {
        "name": "Repair shops answering warranty requests",
        "kind": SegmentKind.ADJACENT,
        "who": "small repair shops answering warranty requests by hand in a shared inbox",
        "signals": ["warranty pages listing repair turnaround times"],
        "where": ["UK Repair Association member directory"],
    }
    payload.update(overrides)
    return AudienceSegment(**payload)


def fetched(url: str, tier: SourceTier, content: str) -> FetchedSource:
    return FetchedSource(
        requested_url=url,
        final_url=url,
        title="Source",
        tier=tier,
        fetched_at=datetime.now(UTC),
        content_hash=hashlib.sha256(content.encode()).hexdigest(),
        content=content,
    )


@pytest.mark.asyncio
async def test_locator_searches_but_synthesis_is_closed_over_successful_fetches(
    provider: ScriptedProvider, session
) -> None:
    good_quote = "We answer the same warranty questions every morning before opening."
    good_html = (
        f"<html><title>Repair forum</title><body><p>{good_quote} "
        "The thread continues with more detail about that routine.</p></body></html>"
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "good.example":
            return httpx.Response(200, text=good_html, headers={"content-type": "text/html"})
        return httpx.Response(503, text="unavailable")

    provider.push(
        "audience_research_locator",
        {
            "sources": [
                {"url": "https://good.example/thread", "tier": 1},
                {"url": "https://failed.example/thread", "tier": 1},
            ]
        },
    )
    provider.push(
        "audience_research_synthesis",
        {
            "situation": {
                "text": "They clear repetitive warranty questions before opening.",
                "evidence": [{"source_id": "S1", "quote": good_quote}],
            }
        },
    )
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    researcher = AudienceResearcher(
        session,
        fetcher=FixedURLFetcher(client=client, resolver=public_resolver),
    )

    result = await researcher.research(
        segment(
            why_them="SECRET PRODUCT FIT",
            angle="SECRET CAMPAIGN ANGLE",
            objection="SECRET PRODUCT OBJECTION",
        )
    )
    await client.aclose()

    assert provider.tools_used_by("audience_research_locator") == [ResearchTool.WEB_SEARCH]
    assert provider.tools_used_by("audience_research_synthesis") == []
    synthesis = next(
        request for request in provider.requests if request.template == "audience_research_synthesis"
    )
    prompts = "\n".join(
        (request.system_prompt or "") + request.messages[0].content
        for request in provider.requests
    )
    assert "SECRET PRODUCT" not in prompts
    assert "SECRET CAMPAIGN" not in prompts
    assert good_quote in (synthesis.system_prompt or "")
    assert "unavailable" not in (synthesis.system_prompt or "")
    assert [source.final_url for source in result.sources] == ["https://good.example/thread"]


@pytest.mark.asyncio
async def test_fixed_url_fetcher_deduplicates_caps_does_not_crawl_and_isolates_failures() -> None:
    requested: list[str] = []
    body = (
        "<html><body><p>" + "Repair technicians describe their daily workflow here. " * 4
        + "</p><a href='https://linked.example/should-not-run'>next</a></body></html>"
    )

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        if request.url.host == "bad.example":
            return httpx.Response(500)
        return httpx.Response(200, text=body, headers={"content-type": "text/html"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    result = await FixedURLFetcher(
        client=client, resolver=public_resolver, max_urls=2
    ).fetch(
        [
            LocatedSource(url="https://good.example/post", tier=1),
            LocatedSource(url="https://good.example/post#comments", tier=1),
            LocatedSource(url="file:///etc/passwd", tier=1),
            LocatedSource(url="https://bad.example/post", tier=2),
            LocatedSource(url="https://over-cap.example/post", tier=2),
        ]
    )
    await client.aclose()

    assert len(result.sources) == 1
    assert len(result.failures) == 1
    assert requested == ["https://good.example/post", "https://bad.example/post"]
    assert all("linked.example" not in url and "over-cap" not in url for url in requested)


@pytest.mark.asyncio
async def test_unsafe_urls_are_rejected_before_http() -> None:
    async def private_resolver(_host: str) -> list[str]:
        return ["127.0.0.1"]

    with pytest.raises(URLSafetyError):
        await validate_public_url("http://localhost/admin", public_resolver)
    with pytest.raises(URLSafetyError):
        await validate_public_url("https://public-looking.example", private_resolver)
    assert bounded_sources([LocatedSource(url="javascript:alert(1)")]) == []


def test_verification_enforces_source_identity_tiers_language_and_domains() -> None:
    first = (
        "We answer the same warranty questions every morning. "
        "Calling it a ticket backlog makes it sound fancier than it is."
    )
    same_domain = "Every morning starts with the same warranty questions from customers."
    other_domain = "The same warranty questions take over the first hour of every day."
    behaviour = "The vacancy requires experience with shared inbox triage and warranty claims."
    interpretation = "Analysts infer that repair shops are becoming more software-aware."
    sources = [
        fetched("https://example.com/thread", SourceTier.BUYER_VOICE, first),
        fetched("https://www.example.com/review", SourceTier.BUYER_VOICE, same_domain),
        fetched("https://other.example/post", SourceTier.BUYER_VOICE, other_domain),
        fetched("https://jobs.example/vacancy", SourceTier.BEHAVIOURAL, behaviour),
        fetched("https://analyst.example/report", SourceTier.INTERPRETATION, interpretation),
    ]
    draft = _ResearchDraft(
        problems=[
            AudienceProblem(
                statement="Warranty questions repeatedly consume the start of the day.",
                evidence=[
                    EvidenceReference(source_id="S1", quote=first.split(". ")[0] + "."),
                    EvidenceReference(source_id="S2", quote=same_domain),
                    EvidenceReference(source_id="S3", quote=other_domain),
                ],
                cost="They lose 3 hours each morning.",
                cost_evidence=EvidenceReference(source_id="S1", quote=first),
            ),
            AudienceProblem(
                statement="A fabricated problem cites the wrong source.",
                evidence=[EvidenceReference(source_id="S2", quote=first)],
            ),
            AudienceProblem(
                statement="A job advert alone cannot ground a buyer problem.",
                evidence=[EvidenceReference(source_id="S4", quote=behaviour)],
            ),
        ],
        buyer_phrases=[
            BuyerPhrase(
                text="ticket backlog",
                evidence=EvidenceReference(source_id="S1", quote=first),
            ),
            BuyerPhrase(
                text="shared inbox triage",
                evidence=EvidenceReference(source_id="S4", quote=behaviour),
            ),
            BuyerPhrase(
                text="words the buyer never used",
                evidence=EvidenceReference(source_id="S1", quote=first),
            ),
        ],
        incumbent_behaviour=[
            SourcedObservation(text="They triage a shared inbox.", evidence=[
                EvidenceReference(source_id="S4", quote=behaviour)
            ])
        ],
        signals=[
            SourcedObservation(
                text="They appear more software-aware.",
                evidence=[EvidenceReference(source_id="S5", quote=interpretation)],
            ),
            SourcedObservation(
                text="Analysts interpret the hiring pattern as growing awareness.",
                evidence=[EvidenceReference(source_id="S5", quote=interpretation)],
                inference_basis="This is an analyst interpretation, not buyer testimony.",
            ),
        ],
        triggers=[
            SourcedObservation(
                text="They receive 40 warranty requests before changing tools.",
                evidence=[EvidenceReference(source_id="S4", quote=behaviour)],
            )
        ],
    )

    verified = verify_research(segment(), draft, sources)

    assert len(verified.problems) == 1
    assert verified.problems[0].id == "P1"
    assert verified.problems[0].grounding is Grounding.GROUNDED
    assert verified.problems[0].corroboration == 2
    assert verified.problems[0].cost == ""
    assert [phrase.text for phrase in verified.buyer_phrases] == ["ticket backlog"]
    assert verified.incumbent_behaviour[0].grounding is Grounding.GROUNDED
    assert [item.grounding for item in verified.signals] == [Grounding.INFERRED]
    assert verified.triggers == []
    assert verified.dropped_claims >= 6


def test_a_supported_numerical_cost_is_retained() -> None:
    quote = "We lose 3 hours every Monday answering repeat warranty questions."
    source = fetched("https://buyer.example/post", SourceTier.BUYER_VOICE, quote)
    reference = EvidenceReference(source_id="S1", quote=quote)
    draft = _ResearchDraft(
        problems=[
            AudienceProblem(
                statement="Repeat questions consume scheduled work time.",
                evidence=[reference],
                cost="3 hours every Monday",
                cost_evidence=reference,
            )
        ]
    )

    verified = verify_research(segment(), draft, [source])

    assert verified.problems[0].cost == "3 hours every Monday"


def database():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        brand = Brand(name="Helpdesk")
        session.add(brand)
        session.commit()
        session.refresh(brand)
        MarketStore(session).save_map(brand.id, DemandMap(segments=[segment()]))
        return engine, brand.id


@pytest.mark.asyncio
async def test_successful_background_refresh_appends_versions(monkeypatch) -> None:
    engine, brand_id = database()

    class SuccessfulResearcher:
        def __init__(self, _session) -> None:
            pass

        async def research(self, chosen, *, on_progress=None) -> AudienceResearch:
            if on_progress:
                on_progress("verified")
            return AudienceResearch(
                audience_name=chosen.name,
                candidate_kind=str(chosen.kind),
            )

    monkeypatch.setattr(market_service, "AudienceResearcher", SuccessfulResearcher)
    for _ in range(2):
        await market_service._run_audience_research(
            brand_id,
            ScriptedProvider(),
            engine,
            JobStatus(kind="audience_research", brand_id=brand_id),
            segment=segment().name,
        )

    with Session(engine) as session:
        store = MarketStore(session)
        latest = store.latest_research_row(brand_id, segment().name)
        assert latest is not None and latest.version == 2
        assert [row.version for row in store.research_history(brand_id, segment().name)] == [
            2,
            1,
        ]


@pytest.mark.asyncio
async def test_total_fetch_failure_persists_nothing(monkeypatch) -> None:
    engine, brand_id = database()

    class FailingResearcher:
        def __init__(self, _session) -> None:
            pass

        async def research(self, _chosen, *, on_progress=None):
            raise AudienceResearchError("None of the located sources could be fetched")

    monkeypatch.setattr(market_service, "AudienceResearcher", FailingResearcher)
    status = JobStatus(kind="audience_research", brand_id=brand_id)

    await market_service._run_audience_research(
        brand_id,
        ScriptedProvider(),
        engine,
        status,
        segment=segment().name,
    )

    with Session(engine) as session:
        assert MarketStore(session).latest_research_row(brand_id, segment().name) is None
    assert status.state == "failed"
    assert "None of the located sources" in status.error
