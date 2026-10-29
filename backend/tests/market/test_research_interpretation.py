"""Exact quotation presence does not certify the direction of a paraphrase."""

from datetime import UTC, datetime

import pytest
from sqlmodel import Session

from app.knowledge.artifacts import Grounding
from app.market.audience_research import (
    AudienceProblem,
    AudienceResearch,
    EvidenceReference,
    SourcedObservation,
    SourceReference,
    SourceTier,
    _ResearchDraft,
    review_research_interpretations,
    verify_research,
)
from app.market.store import MarketStore
from app.models.market import AudienceResearchRow
from app.schemas.market import AudienceResearchRead
from tests.market.test_audience_research import database, fetched, segment

ACTUAL_QUOTE = "Using the app, you’ll receive the data in a simplified version which is easier to handle within Make."
ACTUAL_INTERPRETATION = (
    "Builders are advised to use the generic Webhook trigger module instead of the native "
    "Tally app module, because the native module simplifies the payload in a way that "
    "complicates handling it downstream."
)


def test_exact_saved_native_module_interpretation_is_reviewed_without_losing_the_quote():
    original = AudienceResearch(
        audience_name="Builders", candidate_kind="adjacent",
        incumbent_behaviour=[SourcedObservation(
            text=ACTUAL_INTERPRETATION, grounding=Grounding.GROUNDED,
            evidence=[EvidenceReference(source_id="S3", quote=ACTUAL_QUOTE)],
        )],
    )
    reviewed = review_research_interpretations(original)
    assert original.incumbent_behaviour[0].grounding is Grounding.GROUNDED
    assert reviewed.incumbent_behaviour[0].grounding is Grounding.INFERRED
    assert reviewed.incumbent_behaviour[0].evidence[0].quote == ACTUAL_QUOTE
    assert "Review required" in reviewed.incumbent_behaviour[0].inference_basis
    assert reviewed.interpretation_warnings
    twice = review_research_interpretations(reviewed)
    assert twice.interpretation_warnings == reviewed.interpretation_warnings


@pytest.mark.parametrize("quote,interpretation", [
    ("The native modules make routine projects easier.", "Native modules complicate routine projects."),
    ("The jig makes frame assembly simpler.", "The jig makes frame assembly more complex."),
    ("The caching layer reduces peak memory usage.", "The caching layer increases peak memory usage."),
])
def test_fresh_research_downgrades_opposing_interpretations_across_products(quote, interpretation):
    source = fetched("https://synthetic.example/buyer", SourceTier.BUYER_VOICE, quote)
    reference = EvidenceReference(source_id="S1", quote=quote)
    draft = _ResearchDraft(
        incumbent_behaviour=[SourcedObservation(text=interpretation, evidence=[reference])],
        problems=[AudienceProblem(statement=interpretation, evidence=[reference])],
    )
    reviewed = verify_research(segment(), draft, [source])
    assert reviewed.incumbent_behaviour[0].grounding is Grounding.INFERRED
    assert reviewed.problems[0].grounding is Grounding.INFERRED
    assert reviewed.problems[0].corroboration == 0
    assert reviewed.problems[0].evidence[0].quote == quote


@pytest.mark.parametrize("text,quote", [
    ("Native modules simplify routine projects.", "The native modules make routine projects easier."),
    ("Native modules do not complicate routine projects.", "The native modules make routine projects easier."),
    ("Payload handling is difficult.", "The assembly jig makes frame alignment easier."),
])
def test_agreement_negation_and_unrelated_topics_are_not_treated_as_proven_reversals(text, quote):
    observation = SourcedObservation(text=text, grounding=Grounding.GROUNDED,
                                    evidence=[EvidenceReference(source_id="S1", quote=quote)])
    reviewed = review_research_interpretations(AudienceResearch(
        audience_name="Synthetic audience", candidate_kind="adjacent", incumbent_behaviour=[observation],
    ))
    assert reviewed.incumbent_behaviour[0].grounding is Grounding.GROUNDED
    assert not reviewed.interpretation_warnings


def test_stored_research_and_api_are_reviewed_without_overwriting_history():
    engine, brand_id = database()
    research = AudienceResearch(
        audience_name="Builders", candidate_kind="adjacent",
        incumbent_behaviour=[SourcedObservation(
            text=ACTUAL_INTERPRETATION, grounding=Grounding.GROUNDED,
            evidence=[EvidenceReference(source_id="S3", quote=ACTUAL_QUOTE)],
        )],
    )
    with Session(engine) as session:
        row = AudienceResearchRow(brand_id=brand_id, audience_key="builders", audience_name="Builders",
                                  payload=research.model_dump(mode="json"))
        session.add(row)
        session.commit()
        loaded = MarketStore(session).latest_research(brand_id, "Builders")
        assert loaded is not None
        assert loaded[1].incumbent_behaviour[0].grounding is Grounding.INFERRED
        visible = AudienceResearchRead.of(row)
        assert visible.interpretation_warnings
        assert visible.incumbent_behaviour[0].grounding is Grounding.INFERRED
        session.expire(row)
        assert row.payload["incumbent_behaviour"][0]["grounding"] == "grounded"
        assert row.payload.get("interpretation_warnings") == []


def test_obsolete_computed_reversal_warning_is_removed_without_promoting_the_problem():
    statement = "Google Analytics reports are too complex, pushing owners toward simpler alternatives."
    old_warning = "Review required: this problem may reverse the cited source's meaning. " + statement
    original = AudienceResearch(
        audience_name="Founders", candidate_kind="core",
        interpretation_warnings=[old_warning, "A fetched source was unavailable."],
        problems=[AudienceProblem(
            id="P1", statement=statement, grounding=Grounding.INFERRED,
            evidence=[EvidenceReference(source_id="S1", quote="Google Analytics reports are harder to navigate.")],
        )],
    )
    reviewed = review_research_interpretations(original)
    assert old_warning not in reviewed.interpretation_warnings
    assert "A fetched source was unavailable." in reviewed.interpretation_warnings
    assert old_warning in original.interpretation_warnings
    assert reviewed.problems[0].grounding is Grounding.INFERRED


@pytest.mark.parametrize("title,historical", [
    ("My 2022 Retro: the year I launched a course", True),
    ("My 2026 in review", False),
    ("A 2022 camera used today", False),
])
def test_explicit_retrospective_timeframe_is_not_confused_with_a_publication_date(title, historical):
    source = SourceReference(id="S1", requested_url="https://creator.example/story",
                             final_url="https://creator.example/story", title=title,
                             tier=SourceTier.BUYER_VOICE, fetched_at=datetime(2026, 10, 20, tzinfo=UTC),
                             content_hash="source-hash")
    research = AudienceResearch(
        audience_name="Creators", candidate_kind="core", sources=[source],
        researched_at=datetime(2026, 10, 20, tzinfo=UTC),
        incumbent_behaviour=[SourcedObservation(
            text="The creator collects feedback after chapters.", grounding=Grounding.GROUNDED,
            evidence=[EvidenceReference(source_id="S1", quote="I collect feedback after each chapter.")],
        )],
    )
    reviewed = review_research_interpretations(research)
    assert reviewed.sources[0].published_date is None
    assert reviewed.sources[0].publication_date_basis == "unknown"
    assert any("Historical" in warning for warning in reviewed.interpretation_warnings) is historical
    assert (reviewed.incumbent_behaviour[0].grounding is Grounding.INFERRED) is historical
    assert research.incumbent_behaviour[0].grounding is Grounding.GROUNDED
