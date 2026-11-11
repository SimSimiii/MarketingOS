"""A brand takes the logo and colour its own site declares - once, and only
its own.

Without this every branded email starts as a name in bold and a stock blue
until somebody finds the appearance page, and nobody does before the first
run. The two ways it could go wrong are the tests: replacing what the owner
chose, and adopting the look of some other site filed under the brand.
"""

from datetime import UTC, datetime

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.ingestion.documents import RawDocument, SourceType
from app.models.brand import Brand
from app.models.campaign import Campaign
from app.services import knowledge_service
from app.services.knowledge_service import KnowledgeService

LOOK = {"logo_url": "https://shop.example/logo.png", "theme_color": "#c2410c"}


@pytest.fixture(autouse=True)
def available_logo(monkeypatch):
    async def usable(_):
        return True
    monkeypatch.setattr(knowledge_service, "usable_logo", usable)


@pytest.mark.asyncio
async def test_a_dead_declared_logo_does_not_displace_the_text_wordmark(session, crawled, monkeypatch):
    async def unavailable(_):
        return False
    monkeypatch.setattr(knowledge_service, "usable_logo", unavailable)
    brand = brand_in(session)
    crawled("https://shop.example/")
    await KnowledgeService(session).ingest_source("https://shop.example/", brand_id=brand.id)
    session.refresh(brand)
    assert brand.logo_url is None
    assert brand.primary_color == LOOK["theme_color"]


@pytest.mark.asyncio
async def test_refresh_clears_only_the_dead_imported_logo(session, crawled, monkeypatch):
    brand = brand_in(session)
    crawled("https://shop.example/")
    service = KnowledgeService(session)
    await service.ingest_source("https://shop.example/", brand_id=brand.id)

    async def unavailable(_):
        return False
    monkeypatch.setattr(knowledge_service, "usable_logo", unavailable)
    assert await service.refresh_imported_logo(brand)
    assert brand.logo_url is None
    brand.logo_url = "https://owner.example/chosen.png"
    session.add(brand)
    session.commit()
    assert not await service.refresh_imported_logo(brand)
    assert brand.logo_url == "https://owner.example/chosen.png"


@pytest.mark.asyncio
async def test_recrawl_uses_only_existing_audiences_of_its_own_brand(session, monkeypatch):
    brand = brand_in(session)
    other = brand_in(session)
    session.add(Campaign(name="Auth emails", request="Write one email for this audience.",
                         brand_id=brand.id, audience_segment="A Supabase or Clerk app team"))
    session.add(Campaign(name="Other brand", request="Write one email for another audience.",
                         brand_id=other.id, audience_segment="A HubSpot sales team"))
    session.commit()
    seen = []

    class Crawler:
        def __init__(self, **_):
            pass

        async def crawl(self, url, *, focus=""):
            seen.append((url, focus))
            return []

    monkeypatch.setattr(knowledge_service, "SiteCrawler", Crawler)
    await KnowledgeService(session).ingest_source("https://shop.example/", brand_id=brand.id)
    assert seen == [("https://shop.example/", "Supabase Clerk")]


@pytest.fixture
def session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def brand_in(session: Session, **fields) -> Brand:
    brand = Brand(name="Cabaia", website_url="https://www.shop.example/", **fields)
    session.add(brand)
    session.commit()
    session.refresh(brand)
    return brand


@pytest.fixture
def crawled(monkeypatch):
    """Make the next crawl return one page, from `url`, declaring `LOOK`."""
    pages: list[RawDocument] = []

    class Crawler:
        def __init__(self, **_):
            pass

        async def crawl(self, url: str):
            return pages

    monkeypatch.setattr(knowledge_service, "SiteCrawler", Crawler)

    def serve(url: str, identity: dict = LOOK) -> None:
        pages[:] = [RawDocument(
            content="Cabaia makes backpacks and travel bags. " * 20,
            source=url, source_type=SourceType.WEBSITE, fetched_at=datetime.now(UTC),
            metadata={"title": "Cabaia", "identity": identity},
        )]

    return serve


@pytest.mark.asyncio
async def test_an_empty_brand_takes_the_look_its_site_declares(session, crawled):
    brand = brand_in(session)
    crawled("https://shop.example/")

    await KnowledgeService(session).ingest_source("https://shop.example/", brand_id=brand.id)

    session.refresh(brand)
    assert (brand.logo_url, brand.primary_color) == (LOOK["logo_url"], LOOK["theme_color"])


@pytest.mark.asyncio
async def test_what_the_owner_chose_is_never_replaced(session, crawled):
    brand = brand_in(session, logo_url="https://cdn.example/mine.png", primary_color="#123456")
    crawled("https://shop.example/")

    await KnowledgeService(session).ingest_source("https://shop.example/", brand_id=brand.id)

    session.refresh(brand)
    assert (brand.logo_url, brand.primary_color) == ("https://cdn.example/mine.png", "#123456")


@pytest.mark.asyncio
async def test_another_site_filed_under_the_brand_lends_it_nothing(session, crawled):
    """A press article about the brand declares the newspaper's logo."""
    brand = brand_in(session)
    crawled("https://press.example/articles/cabaia")

    await KnowledgeService(session).ingest_source(
        "https://press.example/articles/cabaia", brand_id=brand.id
    )

    session.refresh(brand)
    assert (brand.logo_url, brand.primary_color) == (None, None)


@pytest.mark.asyncio
async def test_a_site_that_declares_nothing_usable_changes_nothing(session, crawled):
    brand = brand_in(session)
    crawled("https://shop.example/", identity={})

    await KnowledgeService(session).ingest_source("https://shop.example/", brand_id=brand.id)

    session.refresh(brand)
    assert (brand.logo_url, brand.primary_color) == (None, None)
