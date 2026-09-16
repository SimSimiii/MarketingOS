import pytest

from app.knowledge.artifacts import AudienceModel, Grounding, Provenance, Segment
from app.marketing.briefs import EmailBrief
from app.marketing.craft import CraftLoop, EmailVersion, better_of
from app.marketing.email_copy import Email
from app.marketing.gates import GateReport
from app.marketing.pipeline import _reader_recommendation
from app.marketing.reader import BlindRead, PanelRead, personas_for
from app.marketing.report import EmailReportLine, ReaderVerdict


def version(matches, pull, attempt):
    return EmailVersion(
        attempt=attempt,
        email=Email(position=1, subject=str(attempt), preview_text="", greeting="Hi",
                    body="A concrete offer", call_to_action="Try", sign_off="Team"),
        gates=GateReport(),
        read=PanelRead(reads=[BlindRead(
            pull=pull, situation_matches=matches,
            relevance_feedback="Assumes an established reporting workflow",
            assumed_experiences=["past reporting incidents"], problem_now="anticipated",
        )]),
    )


def test_mismatch_is_not_hidden_by_fluency_or_majority():
    bad, good = version(False, 10, 1), version(True, 7, 2)
    assert not bad.ships
    assert good.measured > bad.measured
    assert better_of(bad, good) is good
    assert "reporting workflow" in bad.read.render()
    assert "past reporting incidents" in bad.read.render()
    bad.read.reads.extend([BlindRead(pull=10), BlindRead(pull=10)])
    assert not bad.read.landed


@pytest.mark.asyncio
async def test_relevance_remains_the_fallback_without_a_comparison():
    loop = object.__new__(CraftLoop)
    loop._judge = None
    bad, good = version(False, 10, 1), version(True, 7, 2)
    assert await loop._prefers(good, bad, EmailBrief())
    assert not await loop._prefers(bad, good, EmailBrief())
    assert await loop._run_off(good, [bad], EmailBrief()) is good


@pytest.mark.asyncio
async def test_bakeoff_compares_candidates_with_disputed_relevance():
    from app.marketing.observer import RunObserver
    from app.marketing.tournament import PreferenceJudge
    from tests.marketing.conftest import (
        RoleScriptedProvider,
        make_session,
        votes_for_the_challenger,
    )

    provider = RoleScriptedProvider()
    provider.push("preference_judge", *votes_for_the_challenger(2))
    loop = object.__new__(CraftLoop)
    loop._judge = PreferenceJudge(make_session(provider))
    loop._observer = RunObserver()
    loop._personas = ["An ops generalist considering an internal assistant"]
    questioned, incumbent = version(False, 6, 1), version(True, 6, 1)
    questioned.email = questioned.email.model_copy(update={"body": "A different concrete offer"})
    assert await loop._run_off(incumbent, [questioned], EmailBrief()) is questioned
    assert provider.calls_by_role["preference_judge"] == 2
    assert not questioned.read.relevant  # Preserve the unresolved finding.


def test_profiles_preserve_source_and_uncertainty_without_sales_context():
    segment = Segment(name="Two engineers preparing a first feature", situation="Inspecting calls",
                      situation_grounding=Grounding.GROUNDED,
                      situation_provenance=[Provenance(source="https://example.test", quote="Inspecting calls")])
    profiles = personas_for(AudienceModel(segments=[segment]), segment, True)
    assert all(segment.name in p for p in profiles)
    assert all("https://example.test" in p for p in profiles)
    assert "Reading emphasis" in profiles[1]
    assert "Reading emphasis" in profiles[2]
    assert not any("they already use" in p or "they have been promised" in p for p in profiles)
    assert not any("orientation" in p or "objection answer" in p for p in profiles)


def test_recommendation_uses_cta_obstacle_and_preserves_unknown():
    line = EmailReportLine(position=1, reader_verdicts=[ReaderVerdict(
        biggest_doubt="Compatible providers unknown", to_click_it_would_have_to="Name supported providers")])
    recommendation = _reader_recommendation([line])
    assert "supported providers" in recommendation
    assert "If absent" in recommendation
    assert "testimonials" not in recommendation


def test_historical_reports_keep_frequency_fields_without_forecast_rendering():
    read = BlindRead(opens_in_100=27, clicks_in_100=6)
    verdict = ReaderVerdict.from_panel(PanelRead(reads=[read]))[0]
    assert verdict.clicks_in_100 == 6
    assert verdict.situation_matches is None
    assert "uncalibrated" in read.render()
    assert "27 open" not in read.render()

@pytest.mark.asyncio
async def test_rewrite_receives_mismatch_details():
    from unittest.mock import AsyncMock

    from app.marketing.briefs import CampaignBrief
    from app.marketing.request import CampaignRequest
    from app.marketing.writer import EmailWriter
    from tests.marketing.conftest import artifacts_fixture

    bad = version(False, 10, 1)
    writer = EmailWriter(None)
    writer._write = AsyncMock(return_value=bad.email)
    await writer.revise(
        draft=bad.email, brief=EmailBrief(), campaign=CampaignBrief(),
        request=CampaignRequest(name="Test", request="Write one email"),
        artifacts=artifacts_fixture(), previous=[], gates=bad.gates, read=bad.read,
    )
    task = writer._write.call_args.kwargs["task"]
    assert "reporting workflow" in task
    assert "past reporting incidents" in task


def test_research_does_not_rename_selected_audience_or_lose_provenance():
    from app.marketing.intelligence import adapt_researched_audience
    from tests.marketing.test_campaign_intelligence import artifacts, context, research

    intelligence, _ = context()
    selected = "Small repair shops answering warranty requests"
    intelligence.trace.selected_audience = selected
    adapted = adapt_researched_audience(artifacts(), research(), intelligence)
    primary = adapted.audience.primary()
    assert primary.name == selected
    assert primary.situation_grounding == Grounding.GROUNDED
    assert primary.situation_provenance[0].quote == research().situation.evidence[0].quote

@pytest.mark.asyncio
async def test_strategy_cannot_replace_explicit_selection():
    from app.knowledge.corpus import SourceCorpus
    from app.marketing.contract import parse_contract
    from app.marketing.request import CampaignRequest
    from app.marketing.strategist import Strategist
    from tests.marketing.conftest import (
        RoleScriptedProvider,
        artifacts_fixture,
        default_answers,
        make_session,
    )

    provider = RoleScriptedProvider(default_answers())
    chosen = "Two engineers shipping their first AI feature"
    brief = await Strategist(make_session(provider)).build(
        request=CampaignRequest(name="Test", request="Write three emails"),
        artifacts=artifacts_fixture(), corpus=SourceCorpus(),
        contract=parse_contract("Write three emails"), chosen_segment=chosen,
    )
    assert brief.reader_segment == chosen
    assert chosen in brief.reader

@pytest.mark.asyncio
async def test_pipeline_keeps_selected_identity_for_writer_and_reader():
    from app.market.demand import AudienceSegment, DemandMap
    from app.marketing.pipeline import EmailCampaignPipeline
    from app.marketing.policy import PRESETS
    from app.marketing.request import CampaignRequest
    from tests.marketing.conftest import (
        FakeKnowledgeGateway,
        RoleScriptedProvider,
        artifacts_fixture,
        default_answers,
        make_session,
    )

    selected = "Two engineers shipping their first AI feature"
    provider = RoleScriptedProvider(default_answers())
    pipeline = EmailCampaignPipeline(
        session=make_session(provider),
        knowledge=FakeKnowledgeGateway(
            compiled=artifacts_fixture(), audience_choice=selected,
            demand=DemandMap(segments=[AudienceSegment(name=selected, who="Preparing a launch")]),
        ),
        policy=PRESETS["fast"],
    )
    result = await pipeline.run(CampaignRequest(name="Test", request="Write one email"))
    assert result.brief.reader_segment == selected
    for role in ("email_writer", "blind_reader"):
        assert selected in provider.requests_for(role)[0].system_prompt


def test_semantic_probe_renders_complete_emails_without_empty_cta():
    from app.evaluation.relevance_probe import cases
    from app.marketing.email_copy import render_email

    samples = cases()
    assert len(samples) == 3
    for _, _, email in samples:
        assert email.call_to_action.strip()
        assert email.greeting.strip()
        assert email.sign_off.strip()
        assert 'orqAgent' in email.body
        assert '\n\u2192\n' not in render_email(email)
    assert samples[0][2] == samples[2][2]
    assert samples[0][2].preview_text
