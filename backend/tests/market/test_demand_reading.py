"""Discovery prose cannot override the later, source-checked assessments."""

from app.market.demand import AudienceSegment, DemandMap, MapAssessment, MapEvidence
from app.schemas.market import DemandMapRead


def test_public_and_strategy_summaries_use_assessments_without_changing_the_archive():
    raw = "Everyone buys this product; a discovery-only story proves it."
    evidence = MapEvidence(claim="Manual work", quote="I copy each quote manually.",
                           url="https://community.example/thread")
    demand = DemandMap(reading=raw, segments=[AudienceSegment(
        name="A course creator collecting student testimonials before launch",
        assessment=MapAssessment(
            compatibility="supported", evidence_strength="supported", priority="explore_first",
            reachability="venue_identified", evidence=[evidence, evidence],
        ),
    )])
    public = DemandMapRead.of(demand).reading
    strategy = demand.render_for_strategy()
    assert raw not in public
    assert raw not in strategy
    assert "1 quoted source(s)" in public
    assert "use or purchase unknown" in public
    assert "product compatibility supported" in public
    assert demand.reading == raw, "Keep the original discovery as historical data"


def test_legacy_discovery_without_sources_stays_unknown():
    demand = DemandMap(reading="We found a proven market", segments=[AudienceSegment(name="Creators")])
    public = DemandMapRead.of(demand).reading
    assert "proven market" not in public
    assert "audience evidence absent (0 quoted source(s))" in public
    assert "product compatibility unknown" in public
    assert "use or purchase unknown" in public
