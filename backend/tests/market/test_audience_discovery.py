"""Offline discovery checks: no live search, provider calls or campaign runs."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.ai.base import ResearchTool
from app.knowledge.artifacts import Grounding
from app.market.audience_discovery import (
    current_map,
    merge_research_evidence,
    validate_map,
)
from app.market.audience_research import (
    AudienceProblem,
    AudienceResearch,
    BuyerPhrase,
    EvidenceReference,
    FetchedSource,
    FetchResult,
    SourcedObservation,
    SourceReference,
    SourceTier,
)
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
    audience_fingerprint,
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


def reference(identifier, url):
    return SourceReference(
        id=identifier, requested_url=url, final_url=url, tier=SourceTier.BUYER_VOICE,
        fetched_at=datetime.now(UTC), content_hash="fixture",
    )


def research(**changes):
    values = {
        "audience_name": "Ateliers avec un stock reconditionné",
        "audience_fingerprint": audience_fingerprint(candidate()),
        "candidate_kind": "core",
        "sources": [
            reference("S1", "https://forum.example/thread"),
            reference("S2", "https://community.example/post"),
        ],
        "problems": [
            AudienceProblem(
                id="P1", statement="Les mêmes questions de garantie reviennent chaque matin.",
                grounding=Grounding.GROUNDED,
                evidence=[EvidenceReference(
                    source_id="S1", quote="On répond douze fois par semaine à la même question.")],
            ),
            AudienceProblem(
                id="P2", statement="Personne ne retrouve les réponses déjà écrites.",
                grounding=Grounding.GROUNDED,
                evidence=[EvidenceReference(
                    source_id="S2", quote="Nos réponses sont éparpillées dans quatre boîtes.")],
            ),
        ],
        "where": [SourcedObservation(
            text="L'annuaire des réparateurs indépendants",
            grounding=Grounding.GROUNDED,
            evidence=[EvidenceReference(
                source_id="S2", quote="Tous les ateliers du secteur y sont listés.")],
        )],
    }
    values.update(changes)
    return AudienceResearch(**values)


def researched(segment, found=None, product=None):
    demand = DemandMap(segments=[segment])
    return merge_research_evidence(
        demand,
        {"ateliers avec un stock reconditionné": found or research()},
        product if product is not None else profile(),
    ).segments[0]


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


async def run_map(provider, session, *, verdict=None, product=None, pages=None,
                  previous=None, options=None, answer=None):
    provider.push("audience_map_validate", {"candidates": [
        {"candidate_id": 0, "assessment": verdict or assessment()},
    ]})
    return await validate_map(
        session,
        answer or _MapAnswer(
            segments=[candidate()], source_urls=[p.final_url for p in PAGES]
        ),
        product or profile(), options or MapOptions(), previous, 7, lambda _: None,
        fetcher=Fetcher(pages),
    )


def unreported(**changes):
    """A discovery pass that searched and read, and listed no URLs."""
    values = {
        "segments": [candidate()],
        "source_urls": [],
        "searched": ["ateliers reconditionnés garantie questions répétées"],
        "reading": "The strongest voice found was a workshop describing the same "
                   "warranty question arriving a dozen times a week.",
    }
    values.update(changes)
    return _MapAnswer(**values)


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
@pytest.mark.parametrize("state,compatibility,priority", [
    # An unestablished product fit is a reason to go and look at this audience,
    # not a reason to rank it below one nobody has evidence for either way.
    (CapabilityState.UNKNOWN, "unknown", "explore_first"),
    (CapabilityState.UNSUPPORTED, "incompatible", "incompatible"),
    (CapabilityState.VERIFIED, "supported", "explore_first"),
])
async def test_model_cannot_override_product_truth(
    provider, session, state, compatibility, priority
):
    # The scripted verdict claims "supported" in every one of these.
    result = await run_map(provider, session, product=profile(state))
    assert result.segments[0].assessment.compatibility == compatibility
    assert result.segments[0].assessment.priority == priority


@pytest.mark.asyncio
async def test_compatibility_is_settled_by_the_profile_not_by_the_validation_call(
    provider, session
):
    """Positive support is a fact about the product, which Python holds. Left
    to the model it was never reachable: the check only ever downgraded, so an
    audience whose every requirement was verified still read `unknown`."""
    verdict = assessment(compatibility="unknown")

    result = await run_map(provider, session, verdict=verdict, product=profile())

    assert result.segments[0].assessment.compatibility == "supported"


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
async def test_counterevidence_is_counted_and_said_out_loud_rather_than_vetoing(
    provider, session
):
    """The discovery prompt asks for reasons the product would NOT work. Paying
    for that with a worse rank taught it not to look: a segment that came back
    with a contrary source is better understood than one that came back with
    none, so the sources are counted and named instead of suppressing the rank."""
    verdict = assessment()
    verdict["evidence"].append({**verdict["evidence"][0], "kind": "counterevidence"})

    result = await run_map(provider, session, verdict=verdict)

    segment = result.segments[0]
    assert segment.assessment.priority == "review_first"
    assert segment.assessment.counterevidence == 1
    assert any(e.kind == "counterevidence" for e in segment.assessment.evidence)
    assert any("counterevidence" in note for note in segment.assessment.unknowns)


@pytest.mark.asyncio
async def test_findability_is_its_own_axis(provider, session):
    """An audience nobody can reach and an audience nobody wants fail for
    unrelated reasons, and `priority` alone said the same word about both."""
    verdict = assessment()
    verdict["evidence"] = [item for item in verdict["evidence"] if item["kind"] != "access"]

    result = await run_map(provider, session, verdict=verdict)

    segment = result.segments[0]
    assert segment.assessment.findability == "unknown"
    assert segment.assessment.evidence_strength == "supported"
    assert segment.assessment.priority == "hypothesis"


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


def test_researched_sources_are_read_back_into_the_map_that_ranks_them() -> None:
    """The map ranked an audience `absent` while its research row held ten
    verified sources: the artifact existed, nothing read it."""
    segment = candidate(assessment=MapAssessment(compatibility="supported"))

    result = researched(segment)

    assert result.assessment.evidence_strength == "supported"
    assert result.assessment.priority == "explore_first"
    assert {item.kind for item in result.assessment.evidence} == {"need", "access"}
    assert all(item.fetched_at is not None for item in result.assessment.evidence)
    assert not any(
        "findability" in unknown for unknown in result.assessment.unknowns
    )


def test_research_lifts_evidence_without_inventing_product_compatibility() -> None:
    """Research answers whether the demand is real. What the product can serve
    is read off the capability profile and nowhere else."""
    result = researched(candidate(), product=profile(CapabilityState.UNKNOWN))

    assert result.assessment.evidence_strength == "supported"
    assert result.assessment.findability == "verified"
    assert result.assessment.compatibility == "unknown"


def test_inferred_research_findings_are_not_counted_as_sources() -> None:
    """An inferred finding is the researcher reasoning over the corpus. Useful
    to read, and not a second page that says the same thing."""
    inferred = research(problems=[
        AudienceProblem(
            id="P1", statement="Ils paieraient sans doute pour une réponse automatique.",
            grounding=Grounding.INFERRED,
            evidence=[EvidenceReference(source_id="S1", quote="On répond douze fois par semaine.")],
        )
    ])

    result = researched(candidate(assessment=MapAssessment(compatibility="supported")), inferred)

    assert result.assessment.evidence_strength == "absent"
    assert result.assessment.priority == "hypothesis"
    assert [item.kind for item in result.assessment.evidence] == ["access"]


def test_a_buyer_phrase_counts_and_is_not_merged_twice() -> None:
    quoted = research(buyer_phrases=[BuyerPhrase(
        text="J'ai renoncé à chercher dans les anciens mails",
        evidence=EvidenceReference(
            source_id="S1", quote="On répond douze fois par semaine à la même question."),
    )])
    segment = candidate(assessment=MapAssessment(compatibility="supported"))

    once = researched(segment, quoted)
    twice = merge_research_evidence(
        DemandMap(segments=[once]),
        {"ateliers avec un stock reconditionné": quoted},
        profile(),
    ).segments[0]

    assert len(twice.assessment.evidence) == len(once.assessment.evidence)
    assert twice.assessment.reasons == once.assessment.reasons


def test_a_map_with_no_research_is_returned_untouched() -> None:
    demand = DemandMap(segments=[candidate()])

    assert merge_research_evidence(demand, {}, profile()) is demand


@pytest.mark.asyncio
async def test_a_pass_that_reported_no_source_urls_is_asked_for_them(provider, session):
    """Validation hangs off `source_urls`, and the field is optional. A pass
    that searched twelve times and wrote a page about what it read, then
    returned an empty list, skipped stage two in silence with a deep tier web
    call already paid for."""
    provider.push("audience_map_sources", {"source_urls": [p.final_url for p in PAGES]})

    result = await run_map(provider, session, answer=unreported())

    segment = result.segments[0]
    assert provider.calls["audience_map_sources"] == 1
    assert provider.tools_used_by("audience_map_sources") == [ResearchTool.WEB_SEARCH]
    assert provider.calls["audience_map_validate"] == 1
    assert len(segment.assessment.evidence) == 3
    assert segment.assessment.priority == "explore_first"
    assert "Checked 3 pages" in result.validation_note


@pytest.mark.asyncio
async def test_a_pass_with_nothing_to_recall_from_is_not_asked(provider, session):
    result = await run_map(
        provider, session, answer=unreported(searched=[], reading="")
    )

    assert provider.calls["audience_map_sources"] == 0
    assert provider.calls["audience_map_validate"] == 0
    assert "No usable source URLs" in result.validation_note
    assert result.segments[0].assessment.priority == "hypothesis"


@pytest.mark.asyncio
async def test_a_recall_that_finds_nothing_says_so_rather_than_going_quiet(
    provider, session
):
    provider.push("audience_map_sources", {"source_urls": []})

    result = await run_map(provider, session, answer=unreported())

    assert provider.calls["audience_map_sources"] == 1
    assert provider.calls["audience_map_validate"] == 0
    assert "No usable source URLs" in result.validation_note
