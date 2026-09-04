"""Deterministic admission before another audience research pass is bought."""

import inspect

import pytest

from app.market.demand import AudienceSegment, DemandMap, Researchability, SegmentKind


def concrete(**overrides: object) -> AudienceSegment:
    payload: dict = {
        "name": "Small SaaS engineering teams shipping their first AI feature",
        "who": "five-person engineering teams shipping a customer-facing AI feature for the first time",
        "trigger": "their first AI feature has just entered a customer beta",
        "signals": [
            "job postings for AI platform engineers",
            "GitHub issues discussing production evaluation failures",
        ],
        "where": [
            "r/devops",
            "GitHub issues in LangChain repositories",
        ],
        "population": "roughly 3,000 seed-stage SaaS companies in Europe",
        "fit": 0.31,
        "basis": "they discuss the workflow publicly",
    }
    payload.update(overrides)
    return AudienceSegment(**payload)


def test_a_concrete_audience_with_signals_and_named_venues_passes():
    admission = concrete().admission()

    assert admission.researchable
    assert admission.researchability is Researchability.HIGH
    assert any("observable signal" in reason for reason in admission.reasons)


@pytest.mark.parametrize(
    "name",
    ["business owners", "people interested in AI", "developers", "marketers"],
)
def test_a_generic_category_fails_even_when_reachable(name: str):
    admission = concrete(name=name, who="").admission()

    assert not admission.researchable
    assert admission.researchability is Researchability.UNRESEARCHABLE
    assert any("broad category" in reason for reason in admission.reasons)


def test_empty_signals_fail_admission():
    admission = concrete(signals=[]).admission()

    assert not admission.researchable
    assert any("observable signal" in reason for reason in admission.reasons)


@pytest.mark.parametrize("venue", ["online", "LinkedIn", "social media", "web"])
def test_a_generic_channel_without_a_qualifier_is_not_a_venue(venue: str):
    admission = concrete(where=[venue]).admission()

    assert not admission.researchable
    assert any("specific venue" in reason for reason in admission.reasons)


def test_a_named_channel_venue_is_specific_enough():
    admission = concrete(where=["LinkedIn SaaS CTO Network"]).admission()

    assert admission.researchable


def test_a_later_near_duplicate_remains_visible_but_fails_admission():
    original = concrete()
    reworded = concrete(
        name="SaaS engineers shipping a first customer-facing AI product",
        who="small SaaS engineers shipping their first AI capability to customers",
        fit=0.8,
    )
    demand = DemandMap(segments=[original, reworded])

    assert demand.admission_for(original).researchable
    duplicate = demand.admission_for(reworded)
    assert not duplicate.researchable
    assert any(original.name in reason for reason in duplicate.reasons)
    assert reworded in demand.researchability_ranked


def test_a_niche_but_observable_segment_passes():
    segment = concrete(
        name="COBOL maintainers reconciling failed nightly mainframe batches",
        who="bank platform maintainers manually reconciling failed overnight batch jobs",
        signals=["job posts naming COBOL and JCL"],
        where=["SHARE mainframe user group member directory"],
        population="",
        trigger="",
    )

    assert segment.admission().researchable


def test_a_triggered_audience_passes_and_the_trigger_improves_its_ranking():
    segment = concrete(
        name="Clinics replacing scheduling software after an acquisition",
        kind=SegmentKind.TRIGGERED,
        who="independent clinics consolidating several scheduling tools after being acquired",
        trigger="recently acquired by a regional clinic group",
        population="",
    )

    admission = segment.admission()
    assert admission.researchable
    assert any("clear trigger" in reason for reason in admission.reasons)


def test_a_manually_constructed_segment_uses_the_same_derived_admission():
    manual = concrete(name="Repair shops answering warranty requests through a shared inbox")

    assert manual.admission().researchable
    assert "researchable" not in manual.model_dump()
    assert "researchability" not in manual.model_dump()


def test_an_old_demand_map_loads_without_new_persisted_fields():
    demand = DemandMap.model_validate(
        {
            "segments": [
                {
                    "name": "Independent repair shops",
                    "who": "small repair shops answering warranty questions by hand",
                    "fit": 0.3,
                    "signals": ["a warranty page with a published support email"],
                }
            ]
        }
    )

    admission = demand.admission_for(demand.segments[0])
    assert not admission.researchable
    assert any("specific venue" in reason for reason in admission.reasons)
    assert "researchability" not in demand.model_dump()["segments"][0]


def test_researchability_ranking_is_separate_from_fit():
    high = concrete(name="SaaS teams shipping AI features", fit=0.1)
    low = concrete(
        name="Repair shops answering warranty requests through a shared inbox",
        who="repair shops answering warranty requests through one shared inbox",
        signals=["a warranty page with a published support email"],
        where=["UK repair association member directory"],
        trigger="",
        population="",
        fit=0.9,
    )
    failed = concrete(name="developers", who="", fit=1.0)
    demand = DemandMap(segments=[failed, low, high])

    assert [item.name for item in demand.researchability_ranked] == [
        high.name,
        low.name,
        failed.name,
    ]


def test_admission_has_no_product_evidence_or_campaign_inputs():
    baseline = concrete(fit=0.01, basis="unlikely to buy")
    changed_buying_case = baseline.model_copy(
        update={
            "fit": 0.99,
            "basis": "very likely to buy",
            "why_them": "the product is a perfect fit",
            "angle": "a campaign-specific sales angle",
        }
    )

    assert baseline.admission() == changed_buying_case.admission()
    assert set(inspect.signature(AudienceSegment.admission).parameters) == {"self", "existing"}
