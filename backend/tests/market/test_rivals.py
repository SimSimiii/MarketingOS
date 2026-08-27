"""Finding competitors, and believing only what their pages actually say.

The load-bearing test here is `test_a_claim_not_on_the_page_is_discarded`.
Everything the positioning map decides rests on claims being real, and the
only thing standing between a model's memory of a competitor and a strategist
being planned against it is that check.
"""

import pytest

from app.ai.base import ResearchTool
from app.knowledge.artifacts import BusinessProfile
from app.market.claims import ClaimAxis
from app.market.rivals import RivalLead, RivalScout
from app.runtime.exceptions import CapabilityUnavailableError
from tests.market.conftest import ScriptedCrawler, ScriptedProvider

PRICING_PAGE = (
    "# Pricing\n\n"
    "Get your first API call away in under 4 minutes. "
    "Free tier includes 1,000 requests a month, no card required. "
    "Trusted by Ramp, who cut their review time from two days to twenty minutes.\n"
)

HOME_PAGE = (
    "# Alpha\n\n"
    "The fastest way to ship an agent. Supports 12 models across 4 providers.\n"
)


def profile_payload(**overrides: object) -> dict:
    payload: dict = {
        "one_liner": "The fastest way to ship an agent",
        "promise": "ship an agent this afternoon",
        "pricing": "free tier, then usage-based",
        "free_entry": "1,000 requests a month, no card",
        "icp": "product engineers",
        "vocabulary": ["agent", "ship", "orchestration"],
        "claims": [
            {
                "text": "first API call in under 4 minutes",
                "verbatim": "Get your first API call away in under 4 minutes.",
                "source": "https://alpha.example/pricing",
                "axis": "speed",
                "specific": True,
            },
            {
                "text": "12 models across 4 providers",
                "verbatim": "Supports 12 models across 4 providers.",
                "source": "https://alpha.example",
                "axis": "breadth",
                "specific": True,
            },
        ],
        "proof_shown": [
            {
                "text": "Ramp cut review time from two days to twenty minutes",
                "verbatim": (
                    "Trusted by Ramp, who cut their review time from two days to "
                    "twenty minutes."
                ),
                "source": "https://alpha.example/pricing",
                "axis": "proof",
                "specific": True,
            }
        ],
    }
    payload.update(overrides)
    return payload


def scout_with(provider: ScriptedProvider, session, pages: dict) -> RivalScout:
    return RivalScout(session, crawler=ScriptedCrawler(pages))  # type: ignore[arg-type]


# ------------------------------------------------------------------ profiling


@pytest.mark.asyncio
async def test_a_profile_is_read_from_the_competitors_own_pages(
    provider: ScriptedProvider, session
) -> None:
    provider.push("rival_profile", profile_payload())
    scout = scout_with(
        provider,
        session,
        {
            "https://alpha.example": [
                ("https://alpha.example", HOME_PAGE),
                ("https://alpha.example/pricing", PRICING_PAGE),
            ]
        },
    )

    profile = await scout.profile(RivalLead(name="Alpha", url="https://alpha.example"))

    assert profile.verified
    assert profile.pages_read == 2
    assert profile.promise == "ship an agent this afternoon"
    assert {claim.axis for claim in profile.claims.claims} == {
        ClaimAxis.SPEED,
        ClaimAxis.BREADTH,
    }
    assert len(profile.proof_shown) == 1
    assert profile.unverified_claims == 0


@pytest.mark.asyncio
async def test_profiling_never_reaches_for_the_web(
    provider: ScriptedProvider, session
) -> None:
    """The extraction reads text this process fetched. A profiling call that
    asked for search would be answering from somewhere nobody can check."""
    provider.push("rival_profile", profile_payload())
    scout = scout_with(
        provider, session, {"https://alpha.example": [("https://alpha.example", HOME_PAGE)]}
    )

    await scout.profile(RivalLead(name="Alpha", url="https://alpha.example"))

    assert provider.tools_used_by("rival_profile") == []


@pytest.mark.asyncio
async def test_a_claim_not_on_the_page_is_discarded(
    provider: ScriptedProvider, session
) -> None:
    """The check the whole design rests on. A model that remembers Alpha
    being SOC 2 certified must not be able to put that in front of a
    strategist unless Alpha's own page says so."""
    payload = profile_payload()
    payload["claims"].append(
        {
            "text": "SOC 2 Type II certified",
            "verbatim": "We are SOC 2 Type II certified and audited annually.",
            "source": "https://alpha.example",
            "axis": "security",
            "specific": True,
        }
    )
    provider.push("rival_profile", payload)
    scout = scout_with(
        provider,
        session,
        {
            "https://alpha.example": [
                ("https://alpha.example", HOME_PAGE),
                ("https://alpha.example/pricing", PRICING_PAGE),
            ]
        },
    )

    profile = await scout.profile(RivalLead(name="Alpha", url="https://alpha.example"))

    assert ClaimAxis.SECURITY not in profile.claims.axes
    assert profile.unverified_claims == 1
    assert "discarded" in profile.note


@pytest.mark.asyncio
async def test_verification_is_blind_to_typography(
    provider: ScriptedProvider, session
) -> None:
    """Every published page has been through a CMS that curled its
    apostrophes, and a model quoting one back answers in ASCII about half the
    time. An exact test would throw away correctly quoted claims."""
    curly = "# Alpha\n\nWe don’t charge for the first 1,000 requests — ever.\n"
    payload = profile_payload(
        claims=[
            {
                "text": "first 1,000 requests free",
                "verbatim": "We don't charge for the first 1,000 requests - ever.",
                "source": "https://alpha.example",
                "axis": "price",
                "specific": True,
            }
        ],
        proof_shown=[],
    )
    provider.push("rival_profile", payload)
    scout = scout_with(
        provider, session, {"https://alpha.example": [("https://alpha.example", curly)]}
    )

    profile = await scout.profile(RivalLead(name="Alpha", url="https://alpha.example"))

    assert profile.unverified_claims == 0
    assert profile.claims.claims[0].axis is ClaimAxis.PRICE


@pytest.mark.asyncio
async def test_a_site_that_will_not_load_is_kept_and_marked(
    provider: ScriptedProvider, session
) -> None:
    """"We found this competitor and could not read their site" is a true and
    useful thing to say. Losing the lead silently is not."""
    scout = scout_with(provider, session, {})

    profile = await scout.profile(RivalLead(name="Ghost", url="https://ghost.example"))

    assert not profile.verified
    assert profile.name == "Ghost"
    assert "could not be read" in profile.note
    assert not profile.claims.claims


@pytest.mark.asyncio
async def test_a_lead_with_no_url_is_not_crawled(
    provider: ScriptedProvider, session
) -> None:
    crawler = ScriptedCrawler({})
    scout = RivalScout(session, crawler=crawler)  # type: ignore[arg-type]

    profile = await scout.profile(RivalLead(name="A spreadsheet", kind="status_quo"))

    assert not profile.verified
    assert crawler.crawled == []


# ------------------------------------------------------------------ discovery


@pytest.mark.asyncio
async def test_discovery_asks_for_the_web(provider: ScriptedProvider, session) -> None:
    provider.push(
        "rival_scan",
        {
            "leads": [
                {
                    "name": "Alpha",
                    "url": "alpha.example",
                    "why": "where a team outgrowing the raw API looks first",
                    "kind": "alternative",
                },
                {"name": "A python script", "url": "", "kind": "status_quo"},
            ],
            "searched": ["alternatives to orqAgent"],
        },
    )
    scout = RivalScout(session, crawler=ScriptedCrawler({}))  # type: ignore[arg-type]

    found = await scout.discover(BusinessProfile(company_name="orqAgent"))

    assert [lead.name for lead in found.leads] == ["Alpha", "A python script"]
    # A bare hostname is still a URL the crawler can use.
    assert found.leads[0].url == "https://alpha.example"
    assert set(provider.tools_used_by("rival_scan")) == {
        ResearchTool.WEB_SEARCH,
        ResearchTool.WEB_FETCH,
    }


@pytest.mark.asyncio
async def test_discovery_refuses_a_provider_that_cannot_search(session) -> None:
    """Failing loudly is what keeps "we looked this up" true: a scan run
    without the web returns remembered competitors, and nothing downstream
    could tell."""
    blind = ScriptedProvider(tools=frozenset())
    from app.ai.model_router import ModelRouter
    from app.core.config import PROMPTS_DIR
    from app.runtime.events import EventBus
    from app.runtime.model_session import ModelSession
    from app.runtime.prompt_engine import PromptEngine

    blind_session = ModelSession(
        provider=blind,
        prompt_engine=PromptEngine(PROMPTS_DIR),
        events=EventBus(),
        model_router=ModelRouter(),
        execution_id="test-blind",
    )
    scout = RivalScout(blind_session, crawler=ScriptedCrawler({}))  # type: ignore[arg-type]

    with pytest.raises(CapabilityUnavailableError) as caught:
        await scout.discover(BusinessProfile(company_name="orqAgent"))

    assert "web_search" in str(caught.value)
    # And nothing was spent finding that out.
    assert not blind.requests


@pytest.mark.asyncio
async def test_several_competitors_are_profiled_at_once(
    provider: ScriptedProvider, session
) -> None:
    for _ in range(3):
        provider.push("rival_profile", profile_payload())
    pages = {
        f"https://{name}.example": [(f"https://{name}.example", HOME_PAGE)]
        for name in ("alpha", "beta", "gamma")
    }
    scout = scout_with(provider, session, pages)

    profiles = await scout.profile_all(
        [
            RivalLead(name=name.title(), url=f"https://{name}.example")
            for name in ("alpha", "beta", "gamma")
        ]
    )

    assert [profile.name for profile in profiles] == ["Alpha", "Beta", "Gamma"]
    assert all(profile.verified for profile in profiles)
