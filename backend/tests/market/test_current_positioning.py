"""Read adapters use current product facts without rewriting market history."""

from sqlmodel import Session, SQLModel, create_engine

from app.knowledge.ledger import Evidence, EvidenceKind
from app.knowledge.store import ArtifactScope, ArtifactStore
from app.market.claims import ClaimAxis
from app.market.positioning import PositioningMap
from app.market.radar import MarketSnapshot
from app.market.rivals import RivalProfile
from app.models.brand import Brand
from app.models.campaign import Campaign
from app.models.market import MarketScan
from app.orchestration.campaign_orchestrator import _DbKnowledgeGateway
from app.services.market_service import MarketService
from tests.marketing.conftest import artifacts_fixture


def test_new_product_fact_reaches_market_and_campaign_without_overwriting_scan(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'positioning.db'}")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as db:
        brand = Brand(name="Form Builder")
        db.add(brand)
        db.commit()
        campaign = Campaign(name="Agency launch", request="Write one launch email", brand_id=brand.id)
        db.add(campaign)
        original = MarketSnapshot(
            rivals=[RivalProfile(name="Competitor", url="https://rival.example", verified=True)],
            positioning=PositioningMap(),
        ).model_dump(mode="json")
        scan = MarketScan(brand_id=brand.id, payload=original)
        db.add(scan)
        db.commit()
        artifacts = artifacts_fixture()
        artifacts.evidence.entries.append(Evidence(
            id="E_NEW_DOMAIN", kind=EvidenceKind.FEATURE,
            claim="Publish your form on a custom domain",
            verbatim="Publish your form on a custom domain", source="https://forms.example/help/domains",
        ))
        ArtifactStore(db).save(ArtifactScope(brand_id=brand.id), artifacts, "updated-documents")
        market = MarketService(db).snapshot(brand.id).positioning
        campaign_map = _DbKnowledgeGateway(db, campaign).positioning()
        for current in (market, campaign_map):
            assert any(reading.axis is ClaimAxis.CONTROL
                       and any(claim.text == "Publish your form on a custom domain" for claim in reading.ours)
                       for reading in current.readings)
        db.expire_all()
        assert db.get(MarketScan, scan.id).payload == original
    engine.dispose()
