"""The diff between two readings of the same market.

Every row in the feed is a claim the user will act on, so the tests here are
mostly about *not* reporting things: a feed that fires on a reworded headline
is a feed nobody opens twice.
"""

from app.market.claims import Claim, ClaimAxis, ClaimSet
from app.market.positioning import build
from app.market.radar import MarketSnapshot, RadarSeverity, diff
from app.market.rivals import RivalProfile


def rival(name: str, *claims: Claim, promise: str = "", pricing: str = "",
          proof: list[Claim] | None = None) -> RivalProfile:
    return RivalProfile(
        name=name,
        url=f"https://{name}.example",
        verified=True,
        promise=promise,
        pricing=pricing,
        claims=ClaimSet(claims=list(claims)),
        proof_shown=proof or [],
    )


def claim(text: str, axis: ClaimAxis, specific: bool = False) -> Claim:
    return Claim(text=text, verbatim=text, axis=axis, specific=specific)


def snapshot(ours: ClaimSet, rivals: list[RivalProfile], proof: bool = False) -> MarketSnapshot:
    return MarketSnapshot(rivals=rivals, positioning=build(ours, rivals, we_have_proof=proof))


# ------------------------------------------------------------------- ground


def test_losing_open_ground_is_the_loudest_row() -> None:
    """The change that most reliably makes already-written copy worse, and the
    one nothing else in the system can see."""
    ours = ClaimSet(claims=[claim("self-hosted, your VPC", ClaimAxis.CONTROL)])
    field = [rival(name, claim("fast", ClaimAxis.SPEED)) for name in ("alpha", "gamma", "delta")]
    before = snapshot(ours, field)
    after = snapshot(
        ours, [*field, rival("beta", claim("run it in your own cloud", ClaimAxis.CONTROL))]
    )

    events = diff(before, after)
    lost = next(e for e in events if e.axis is ClaimAxis.CONTROL)

    assert lost.severity is RadarSeverity.ACTS_ON_COPY
    assert "no longer own" in lost.headline, "one rival in four leaves it contested"
    assert "beta" in lost.detail.lower()
    assert lost.what_to_do
    # And it sorts above the routine noise.
    assert events[0].severity is RadarSeverity.ACTS_ON_COPY


def test_half_the_field_taking_an_axis_makes_it_table_stakes() -> None:
    ours = ClaimSet(claims=[claim("self-hosted, your VPC", ClaimAxis.CONTROL)])
    before = snapshot(ours, [rival("alpha"), rival("beta")])
    after = snapshot(
        ours,
        [rival("alpha", claim("run it in your own cloud", ClaimAxis.CONTROL)), rival("beta")],
    )

    lost = next(e for e in diff(before, after) if e.axis is ClaimAxis.CONTROL)
    assert "table stakes" in lost.headline
    assert lost.severity is RadarSeverity.ACTS_ON_COPY


def test_gaining_ground_is_reported_but_quieter() -> None:
    ours = ClaimSet(claims=[claim("self-hosted", ClaimAxis.CONTROL)])
    before = snapshot(
        ours,
        [
            rival("alpha", claim("run it yourself", ClaimAxis.CONTROL)),
            rival("beta", claim("bring your own cloud", ClaimAxis.CONTROL)),
        ],
    )
    after = snapshot(ours, [rival("alpha", claim("fast", ClaimAxis.SPEED))])

    opened = next(e for e in diff(before, after) if e.axis is ClaimAxis.CONTROL)
    assert "opened up" in opened.headline
    assert opened.severity is RadarSeverity.NOTABLE


def test_a_still_market_produces_nothing() -> None:
    """Including for a claim made entirely of category words, which has no
    distinctive vocabulary to compare and used to be reported as new every
    single week."""
    ours = ClaimSet(claims=[claim("fast", ClaimAxis.SPEED)])
    rivals = [rival("alpha", claim("also fast", ClaimAxis.SPEED))]
    assert diff(snapshot(ours, rivals), snapshot(ours, rivals)) == []


# ------------------------------------------------------------------- rivals


def test_a_new_competitor_is_reported() -> None:
    before = snapshot(ClaimSet(), [rival("alpha")])
    after = snapshot(ClaimSet(), [rival("alpha"), rival("beta", promise="ship agents faster")])

    new = next(e for e in diff(before, after) if e.rival == "beta")
    assert "new in this market" in new.headline
    assert new.detail == "ship agents faster"


def test_a_reworded_promise_is_not_a_repositioning() -> None:
    """A company that tidied its home page has not repositioned, and a feed
    that says it has cries wolf."""
    before = snapshot(ClaimSet(), [rival("alpha", promise="the fastest way to ship an agent")])
    after = snapshot(ClaimSet(), [rival("alpha", promise="ship an agent, the fastest way")])

    assert not [e for e in diff(before, after) if "repositioned" in e.headline]


def test_a_real_repositioning_is_reported() -> None:
    before = snapshot(ClaimSet(), [rival("alpha", promise="the fastest way to ship an agent")])
    after = snapshot(
        ClaimSet(), [rival("alpha", promise="enterprise governance for regulated industries")]
    )

    moved = next(e for e in diff(before, after) if "repositioned" in e.headline)
    assert moved.severity is RadarSeverity.NOTABLE
    assert "was:" in moved.detail


def test_a_price_change_is_reported() -> None:
    before = snapshot(ClaimSet(), [rival("alpha", pricing="$20 per seat")])
    after = snapshot(ClaimSet(), [rival("alpha", pricing="$12 per seat")])

    priced = next(e for e in diff(before, after) if e.axis is ClaimAxis.PRICE)
    assert "changed their pricing" in priced.headline


def test_a_rival_that_starts_naming_customers_is_reported() -> None:
    before = snapshot(ClaimSet(), [rival("alpha")])
    after = snapshot(
        ClaimSet(),
        [rival("alpha", proof=[claim("Ramp cut review time", ClaimAxis.PROOF)])],
    )

    shown = next(e for e in diff(before, after) if "showing proof" in e.headline)
    assert "Ramp" in shown.detail


def test_the_proof_gap_widening_acts_on_copy() -> None:
    before = snapshot(
        ClaimSet(),
        [rival("alpha", proof=[claim("Ramp uses it", ClaimAxis.PROOF)]), rival("beta")],
    )
    after = snapshot(
        ClaimSet(),
        [
            rival("alpha", proof=[claim("Ramp uses it", ClaimAxis.PROOF)]),
            rival("beta", proof=[claim("Linear uses it", ClaimAxis.PROOF)]),
        ],
    )

    widened = next(e for e in diff(before, after) if "naming customers" in e.headline)
    assert widened.severity is RadarSeverity.ACTS_ON_COPY
    assert "afternoon" in widened.what_to_do


def test_a_rival_that_stopped_answering_is_only_routine() -> None:
    before = snapshot(ClaimSet(), [rival("alpha"), rival("beta")])
    after = snapshot(ClaimSet(), [rival("alpha")])

    gone = next(e for e in diff(before, after) if e.rival == "beta")
    assert gone.severity is RadarSeverity.ROUTINE


def test_everything_is_new_against_an_empty_snapshot() -> None:
    """`diff` compares what it is given; suppressing the first scan is the
    scanner's job, not this function's - see MarketScanner.scan, which only
    diffs when a previous snapshot has rivals in it."""
    events = diff(MarketSnapshot(), snapshot(ClaimSet(), [rival("alpha")]))
    assert [e.headline for e in events] == ["alpha is new in this market"]
