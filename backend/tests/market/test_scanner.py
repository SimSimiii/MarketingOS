"""One pass over a market, end to end.

Deliberately no database: the scanner computes, the service persists, and a
test that needed a session to check the arithmetic would be testing both.
"""

import pytest

from app.knowledge.artifacts import BusinessProfile, KnowledgeArtifacts
from app.knowledge.ledger import Evidence, EvidenceKind, EvidenceLedger
from app.market.positioning import Territory
from app.market.radar import MarketSnapshot, RadarSeverity
from app.market.rivals import RivalLead, RivalScout
from app.market.scanner import MarketScanner
from tests.market.conftest import ScriptedCrawler, ScriptedProvider

ALPHA_PAGE = (
    "# Alpha\n\nThe fastest way to ship an agent. Live in under 10 minutes.\n"
    "Trusted by Ramp and Linear.\n"
)
BETA_PAGE = "# Beta\n\nAgent orchestration you can self-host. Runs in your own VPC.\n"


def artifacts() -> KnowledgeArtifacts:
    return KnowledgeArtifacts(
        business=BusinessProfile(
            company_name="orqAgent",
            what_it_does="agent orchestration",
            category="AI infrastructure",
            vocabulary=["agents", "orchestration"],
        ),
        evidence=EvidenceLedger(
            entries=[
                Evidence(
                    id="E1",
                    kind=EvidenceKind.FEATURE,
                    claim="first API call in under 5 minutes",
                    verbatim="From sign-up to your first API call takes under 5 minutes.",
                ),
                Evidence(
                    id="E2",
                    kind=EvidenceKind.INTEGRATION,
                    claim="25 models across 9 providers",
                    verbatim="25 models across 9 providers.",
                ),
            ]
        ),
    )


def scanner_for(provider: ScriptedProvider, session, pages: dict) -> MarketScanner:
    return MarketScanner(session, scout=RivalScout(session, crawler=ScriptedCrawler(pages)))  # type: ignore[arg-type]


PAGES = {
    "https://alpha.example": [("https://alpha.example", ALPHA_PAGE)],
    "https://beta.example": [("https://beta.example", BETA_PAGE)],
}

ALPHA_PROFILE = {
    "one_liner": "The fastest way to ship an agent",
    "promise": "ship an agent today",
    "pricing": "free tier then usage",
    "free_entry": "free tier",
    "icp": "product engineers",
    "vocabulary": ["agent", "orchestration"],
    "claims": [
        {
            "text": "live in under 10 minutes",
            "verbatim": "Live in under 10 minutes.",
            "source": "https://alpha.example",
            "axis": "speed",
            "specific": True,
        }
    ],
    "proof_shown": [
        {
            "text": "Ramp and Linear use it",
            "verbatim": "Trusted by Ramp and Linear.",
            "source": "https://alpha.example",
            "axis": "proof",
            "specific": True,
        }
    ],
}

BETA_PROFILE = {
    "one_liner": "Agent orchestration you can self-host",
    "promise": "keep it in your own VPC",
    "pricing": "",
    "free_entry": "",
    "icp": "platform teams",
    "vocabulary": ["orchestration", "self-host"],
    "claims": [
        {
            "text": "runs in your own VPC",
            "verbatim": "Runs in your own VPC.",
            "source": "https://beta.example",
            "axis": "control",
            "specific": False,
        }
    ],
    "proof_shown": [],
}


@pytest.mark.asyncio
async def test_a_first_scan_discovers_profiles_and_positions(
    provider: ScriptedProvider, session
) -> None:
    provider.push(
        "rival_scan",
        {
            "leads": [
                {"name": "Alpha", "url": "https://alpha.example", "kind": "alternative"},
                {"name": "Beta", "url": "https://beta.example", "kind": "alternative"},
            ],
            "searched": ["alternatives to orqAgent"],
        },
    )
    provider.push("rival_profile", ALPHA_PROFILE, BETA_PROFILE)
    progress: list[str] = []

    result = await scanner_for(provider, session, PAGES).scan(
        artifacts=artifacts(),
        known=[],
        on_progress=lambda _stage, message: progress.append(message),
    )

    assert result.searched_web
    assert [lead.name for lead in result.discovered] == ["Alpha", "Beta"]
    assert result.snapshot.positioning.rivals_profiled == 2

    # Alpha claims speed with a figure, so speed is contested rather than ours.
    speed = next(
        r for r in result.snapshot.positioning.readings if str(r.axis) == "speed"
    )
    assert speed.territory is not Territory.OPEN
    # Nobody contests breadth, so that is where an email should lead.
    breadth = next(
        r for r in result.snapshot.positioning.readings if str(r.axis) == "breadth"
    )
    assert breadth.territory is Territory.OPEN

    # Alpha shows named customers and we show none.
    assert result.snapshot.positioning.proof_deficit
    # And the run said what it was doing at each step.
    assert len(progress) >= 3


@pytest.mark.asyncio
async def test_a_first_scan_reports_no_changes(
    provider: ScriptedProvider, session
) -> None:
    """There is nothing to have moved yet, and a feed that says otherwise on
    day one is a feed that starts by crying wolf."""
    provider.push("rival_profile", ALPHA_PROFILE)

    result = await scanner_for(provider, session, PAGES).scan(
        artifacts=artifacts(),
        known=[RivalLead(name="Alpha", url="https://alpha.example")],
        previous=MarketSnapshot(),
        discover=False,
    )

    assert result.events == []
    assert not result.searched_web


@pytest.mark.asyncio
async def test_a_rescan_reports_what_moved(provider: ScriptedProvider, session) -> None:
    provider.push("rival_profile", ALPHA_PROFILE)
    known = [RivalLead(name="Alpha", url="https://alpha.example")]
    first = await scanner_for(provider, session, PAGES).scan(
        artifacts=artifacts(), known=known, discover=False
    )

    # Alpha now claims model breadth too - the axis we were alone on.
    moved = dict(ALPHA_PROFILE)
    moved["claims"] = [
        *ALPHA_PROFILE["claims"],
        {
            "text": "30 models across 10 providers",
            "verbatim": "Live in under 10 minutes.",
            "source": "https://alpha.example",
            "axis": "breadth",
            "specific": True,
        },
    ]
    provider.push("rival_profile", moved)

    second = await scanner_for(provider, session, PAGES).scan(
        artifacts=artifacts(), known=known, previous=first.snapshot, discover=False
    )

    lost = [e for e in second.events if str(e.axis) == "breadth"]
    assert lost, "losing the axis we were alone on is the point of the feed"
    assert lost[0].severity is RadarSeverity.ACTS_ON_COPY


@pytest.mark.asyncio
async def test_a_rescan_does_not_search_the_web(
    provider: ScriptedProvider, session
) -> None:
    """Somebody who has curated their competitor list wants those companies
    re-read, not a sixth proposed every Monday."""
    provider.push("rival_profile", ALPHA_PROFILE)

    await scanner_for(provider, session, PAGES).scan(
        artifacts=artifacts(),
        known=[RivalLead(name="Alpha", url="https://alpha.example")],
        discover=False,
    )

    assert "rival_scan" not in provider.calls


@pytest.mark.asyncio
async def test_an_empty_market_says_so(provider: ScriptedProvider, session) -> None:
    provider.push("rival_scan", {"leads": [], "searched": ["alternatives to orqAgent"]})

    result = await scanner_for(provider, session, {}).scan(artifacts=artifacts(), known=[])

    assert result.snapshot.positioning.is_empty
    assert "no field to position against" in " ".join(result.notes)


@pytest.mark.asyncio
async def test_an_unreadable_competitor_is_reported_not_hidden(
    provider: ScriptedProvider, session
) -> None:
    provider.push("rival_profile", ALPHA_PROFILE)

    result = await scanner_for(provider, session, PAGES).scan(
        artifacts=artifacts(),
        known=[
            RivalLead(name="Alpha", url="https://alpha.example"),
            RivalLead(name="Ghost", url="https://ghost.example"),
        ],
        discover=False,
    )

    assert result.snapshot.positioning.rivals_profiled == 1
    assert "Ghost" in " ".join(result.notes)


@pytest.mark.asyncio
async def test_a_competitor_already_on_the_list_is_not_added_twice(
    provider: ScriptedProvider, session
) -> None:
    provider.push(
        "rival_scan",
        {
            "leads": [
                {"name": "alpha", "url": "https://alpha.example", "kind": "alternative"},
                {"name": "Beta", "url": "https://beta.example", "kind": "alternative"},
            ],
            "searched": [],
        },
    )
    provider.push("rival_profile", ALPHA_PROFILE, BETA_PROFILE)

    result = await scanner_for(provider, session, PAGES).scan(
        artifacts=artifacts(),
        known=[RivalLead(name="Alpha", url="https://alpha.example")],
    )

    assert [lead.name for lead in result.discovered] == ["Beta"]
    assert result.snapshot.positioning.rivals_profiled == 2
