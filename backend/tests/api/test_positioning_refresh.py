"""Saved market profiles can be reinterpreted without another paid scan."""

from uuid import UUID

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.market.claims import Claim, ClaimAxis, ClaimSet
from app.market.positioning import AxisReading, PositioningMap, Territory
from app.market.radar import MarketSnapshot
from app.market.rivals import RivalProfile
from app.market.store import MarketStore


def test_latest_scan_updates_arithmetic_without_rewriting_history(client: TestClient, engine):
    brand = client.post("/api/brands", json={"name": "Drafts"}).json()
    quote = "Export emails as HTML"
    ours = Claim(text=quote, verbatim=quote, axis=ClaimAxis.CONTROL, specific=False)
    theirs = ours.model_copy(update={"axis": ClaimAxis.EFFORT})
    snapshot = MarketSnapshot(
        rivals=[RivalProfile(name="Alternative", verified=True, claims=ClaimSet(claims=[theirs]))],
        positioning=PositioningMap(rivals_profiled=1, readings=[
            AxisReading(axis=ClaimAxis.CONTROL, territory=Territory.OPEN, ours=[ours]),
        ]),
    )
    payload = snapshot.model_dump(mode="json")
    with Session(engine) as session:
        store = MarketStore(session)
        row = store.save_scan(UUID(brand["id"]), snapshot)

        result = store.latest_scan(UUID(brand["id"]))

        assert result is not None
        control = next(r for r in result.positioning.readings if r.axis is ClaimAxis.CONTROL)
        assert control.territory is not Territory.OPEN
        assert control.theirs["Alternative"][0].verbatim == quote
        session.refresh(row)
        assert row.payload == payload
        assert row.version == 1
        assert len(store.scan_history(UUID(brand["id"]))) == 1
