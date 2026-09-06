"""Offline discovery checks: no live search, provider calls or campaign runs."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.market.audience_discovery import current_map, validate_map
from app.market.audience_research import FetchedSource, FetchResult, SourceTier
from app.market.capabilities import (
    CapabilityState,
    ProductCapability,
    ProductCapabilityProfile,
)
from app.market.demand import (
    AudienceCartographer,
    AudienceSegment,
    DemandMap,
    MapAssessment,
    MapOptions,
    _MapAnswer,
)
from app.market.qualification import AudienceDefinition
from app.runtime.exceptions import ProviderError
from app.schemas.market import DemandMapRead, MapAudienceRequest
from tests.market.test_demand import artifacts


def candidate(**changes):
    values = {
        "name": "Ateliers avec un stock reconditionné",
        "organization": "Ateliers indépendants",
        "workflow": "Gestion manuelle des garanties",
        "need": "Répondre aux questions répétées",
        "who": "Une petite équipe répond aux mêmes questions chaque semaine.",
        "signals": ["Page de garantie publiée", "Catalogue de produits reconditionnés"],
        "where": ["Annuaire des réparateurs"],
        "definition": AudienceDefinition(required_product_capabilities=["warranty_answers"]),
    }
    values.update(changes)
    return AudienceSegment(**values)


def profile(state=CapabilityState.VERIFIED):
    return ProductCapabilityProfile(
        knowledge_id=uuid4(), knowledge_version=1,
        capabilities=[ProductCapability(id="warranty_answers", label="Warranty answers", state=state)],
    )


def page(url, content):
    return FetchedSource(
        requested_url=url, final_url=url, tier=SourceTier.BUYER_VOICE,
        fetched_at=datetime.now(UTC), content_hash="fixture", content=content,
    )


PAGES = [
    page("https://workshop.example/problems", "We answer the same warranty questions manually every week."),
    page("https://repairs.example/about", "Our staff spends each morning replying to warranty questions."),
    page("https://directory.example/list", "Independent refurbishment workshops are listed in this directory."),
]


class Fetcher:
    def __init__(self, pages=None):
        self.pages = PAGES if pages is None else pages
        self.requested = []

    async def fetch(self, located):
        self.requested.extend(item.url for item in located)
        return FetchResult(sources=[p for p in self.pages if p.final_url in self.requested])


def assessment(**changes):
    data = {
        "compatibility": "supported",
        "priority": "explore_first", "evidence_strength": "supported",
        "evidence": [
            {"claim": "Observed workflow", "quote": p.content, "url": p.final_url,
                 "kind": "access" if i == 2 else "need"}
            for i, p in enumerate(PAGES)
        ],
    }
    data.update(changes)
    return data


async def run_map(provider, session, *, verdict=None, product=None, pages=None, previous=None, options=None):
    provider.push("audience_map_validate", {"candidates": [
        {"candidate_id": 0, "assessment": verdict or assessment()},
    ]})
    return await validate_map(
        session, _MapAnswer(segments=[candidate()], source_urls=[p.final_url for p in PAGES]),
        product or profile(), options or MapOptions(), previous, 7, lambda _: None,
        fetcher=Fetcher(pages),
    )


@pytest.mark.asyncio
async def test_source_bound_priority_and_closed_world_tools(provider, session):
    result = await run_map(provider, session)
    segment = result.segments[0]
    assert segment.assessment.priority == "explore_first"
    assert len(segment.assessment.evidence) == 3
    assert all(e.fetched_at for e in segment.assessment.evidence)
    assert provider.tools_used_by("audience_map_validate") == []
    assert provider.calls["audience_map_validate"] == 1
    assert segment.admission().researchable  # French needs no English verb suffix.
    assert "%" not in result.render_for_strategy()
    read = DemandMapRead.of(result).model_dump()
    assert read["segments"][0]["assessment"]["evidence"][0]["url"]
    assert "source_cache" not in read


@pytest.mark.asyncio
@pytest.mark.parametrize("state,expected", [
    (CapabilityState.UNKNOWN, "unknown"),
    (CapabilityState.UNSUPPORTED, "incompatible"),
])
async def test_model_cannot_override_product_truth(provider, session, state, expected):
    result = await run_map(provider, session, product=profile(state))
    assert result.segments[0].assessment.compatibility == expected
    assert result.segments[0].assessment.priority != "explore_first"


@pytest.mark.asyncio
async def test_quote_must_belong_to_its_exact_page(provider, session):
    verdict = assessment()
    verdict["evidence"][0]["url"] = PAGES[1].final_url
    verdict["evidence"][1]["quote"] = "An invented quotation with convincing details."
    result = await run_map(provider, session, verdict=verdict)
    segment = result.segments[0]
    assert len(segment.assessment.evidence) == 1
    assert segment.assessment.evidence_strength == "absent"
    assert segment.assessment.priority == "hypothesis"
    assert "2 unsupported" in " ".join(segment.assessment.unknowns)


@pytest.mark.asyncio
async def test_copied_pages_do_not_count_as_independent_need_evidence(provider, session):
    pages = [PAGES[0], PAGES[1].model_copy(update={"content": PAGES[0].content}), PAGES[2]]
    verdict = assessment()
    verdict["evidence"][1]["quote"] = PAGES[0].content
    result = await run_map(provider, session, pages=pages, verdict=verdict)
    assert result.segments[0].assessment.evidence_strength == "limited"
    assert result.segments[0].assessment.priority == "hypothesis"


@pytest.mark.asyncio
async def test_counterevidence_remains_visible_and_prevents_top_priority(provider, session):
    verdict = assessment()
    verdict["evidence"].append({**verdict["evidence"][0], "kind": "counterevidence"})
    result = await run_map(provider, session, verdict=verdict)
    assert result.segments[0].assessment.priority == "hypothesis"
    assert any(e.kind == "counterevidence" for e in result.segments[0].assessment.evidence)


@pytest.mark.asyncio
async def test_unreadable_sources_do_not_create_a_false_empty_market(provider, session):
    result = await run_map(provider, session, pages=[])
    assert len(result.segments) == 1
    assert result.segments[0].assessment.priority == "hypothesis"
    assert "absence of demand" in result.validation_note
    assert provider.calls["audience_map_validate"] == 0


@pytest.mark.asyncio
async def test_failed_assessment_keeps_discovered_work(session, monkeypatch):
    async def fail(**kwargs):
        raise ProviderError("offline")
    monkeypatch.setattr(session, "structured", fail)
    result = await validate_map(
        session, _MapAnswer(segments=[candidate()], source_urls=[p.final_url for p in PAGES]),
        profile(), MapOptions(), None, 7, lambda _: None, fetcher=Fetcher(),
    )
    assert result.segments[0].assessment.priority == "hypothesis"
    assert "failed" in result.validation_note


@pytest.mark.asyncio
async def test_discovery_cannot_self_certify_or_filter_low_rates(provider, session):
    provider.push("audience_map", {"segments": [candidate(
        fit=0.01, assessment=MapAssessment.model_validate(assessment())
    ).model_dump(mode="json")]})
    result = await AudienceCartographer(session).map(artifacts())
    assert result.segments[0].assessment.evidence == []
    assert result.segments[0].assessment.priority == "hypothesis"
    assert provider.calls["audience_map_validate"] == 0


@pytest.mark.asyncio
async def test_scope_reaches_prompt_and_dynamic_catalogue(provider, session):
    provider.push("audience_map", {"segments": []})
    await AudienceCartographer(session).map(
        artifacts(), options=MapOptions(geography="France", language="Français", exclusions="Clinics"),
        capability_profile=profile(),
    )
    request = provider.requests[0]
    text = str(request)
    assert "France" in text and "Clinics" in text and "warranty_answers" in text
    assert "hipaa_compliance" not in text


@pytest.mark.asyncio
async def test_exploration_preserves_names_and_scope_change_does_not(provider, session):
    previous = DemandMap(segments=[candidate(name="Existing", organization="Existing shops")])
    result = await run_map(provider, session, previous=previous, options=MapOptions(mode="explore"))
    assert next(s.name for s in result.segments) == "Existing"
    assert len(result.segments) == 2
    result = await run_map(provider, session, previous=previous, options=MapOptions(mode="explore", geography="France"))
    assert len(result.segments) == 1
    assert previous.segments[0].assessment.unknowns == []


@pytest.mark.asyncio
async def test_recent_cached_pages_are_reused_only_during_exploration(provider, session):
    product = profile()
    previous = await run_map(provider, session, product=product)
    provider.push("audience_map_validate", {"candidates": [{"candidate_id": 0, "assessment": assessment()}]})
    fetcher = Fetcher([])
    result = await validate_map(
        session, _MapAnswer(segments=[candidate()], source_urls=[p.final_url for p in PAGES]),
        product, MapOptions(mode="explore"), previous, 7, lambda _: None, fetcher=fetcher,
    )
    assert fetcher.requested == []
    assert len(result.segments) == 1
    assert len(result.source_cache) == 3


def test_legacy_maps_remain_readable_without_claiming_validation():
    old = DemandMap.model_validate({"segments": [{"name": "Legacy", "fit": 0.99}]})
    read = DemandMapRead.of(old)
    assert read.segments[0].assessment.priority == "hypothesis"
    assert "refresh" in read.validation_note
    assert MapAudienceRequest.model_validate({}).objective == "customers"


@pytest.mark.asyncio
async def test_refresh_replaces_previous_audiences(provider, session):
    previous = DemandMap(segments=[candidate(name="Existing", organization="Other shops")])
    result = await run_map(provider, session, previous=previous)
    assert len(result.segments) == 1
    assert result.segments[0].name == candidate().name
    assert previous.segments[0].name == "Existing"


@pytest.mark.asyncio
async def test_changed_product_invalidates_retained_exploration_priority(provider, session):
    previous = await run_map(provider, session)
    assert previous.segments[0].assessment.priority == "explore_first"
    result = await run_map(
        provider, session, previous=previous, product=profile(CapabilityState.UNSUPPORTED),
        options=MapOptions(mode="explore"),
    )
    assert result.segments[0].assessment.priority == "incompatible"
    assert previous.segments[0].assessment.priority == "explore_first"


@pytest.mark.asyncio
async def test_old_cache_is_fetched_again(provider, session):
    previous = await run_map(provider, session)
    for payload in previous.source_cache:
        payload["fetched_at"] = (datetime.now(UTC) - timedelta(days=8)).isoformat()
    fetcher = Fetcher()
    provider.push("audience_map_validate", {"candidates": []})
    await validate_map(
        session, _MapAnswer(segments=[candidate()], source_urls=[p.final_url for p in PAGES]),
        profile(), MapOptions(mode="explore"), previous, 7, lambda _: None, fetcher=fetcher,
    )
    assert len(fetcher.requested) == 3


def test_distinct_workflows_are_not_blocked_as_lexical_duplicates():
    first = candidate()
    second = candidate(workflow="Réparation des retours sous garantie", need="Organiser les réparations")
    assert second.admission([first]).researchable


@pytest.mark.asyncio
async def test_product_edits_invalidate_old_map_without_rewriting_history(provider, session):
    previous = await run_map(provider, session)
    current = current_map(previous, profile(CapabilityState.UNSUPPORTED))
    assert current.segments[0].assessment.priority == "incompatible"
    assert "Product profile changed" in current.validation_note
    assert previous.segments[0].assessment.priority == "explore_first"
    assert len(current.segments[0].assessment.evidence) == 3


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["refresh", "explore"])
async def test_rerun_does_not_repeat_names_when_workflow_changes(session, mode):
    first = candidate()
    changed = candidate(workflow="Reworded workflow")
    previous = DemandMap(segments=[first, changed])
    result = await validate_map(
        session, _MapAnswer(segments=[changed, first]), profile(),
        MapOptions(mode=mode), previous, 7, lambda _: None,
    )
    assert len(result.segments) == 1
    assert result.segments[0].name == first.name
    assert result.segments[0].workflow == (changed.workflow if mode == "refresh" else first.workflow)
    assert len(previous.segments) == 2


def test_saved_duplicate_names_are_collapsed_without_changing_history():
    first = candidate()
    previous = DemandMap(segments=[first, candidate(workflow="Reworded workflow")])
    result = current_map(previous, None)
    assert len(result.segments) == 1
    assert result.segments[0].name == first.name
    assert len(previous.segments) == 2
