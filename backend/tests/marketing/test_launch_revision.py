"""Regressions from the saved 2026-09-16 launch, without paid model calls.

Scripted preferences check selection and context boundaries, not writing quality.
"""

import json
from pathlib import Path

import pytest

from app.evaluation.campaign_quality import CampaignQualityCase
from app.knowledge.artifacts import (
    AudienceModel,
    BusinessProfile,
    KnowledgeArtifacts,
    Objection,
    Segment,
)
from app.knowledge.corpus import SourceCorpus
from app.knowledge.ledger import Evidence, EvidenceIndex, EvidenceKind, EvidenceLedger
from app.marketing.briefs import CampaignBrief, EmailBrief
from app.marketing.contract import parse_contract
from app.marketing.craft import CraftLoop
from app.marketing.critic import ConversionCritic, Critique
from app.marketing.email_copy import Email, render_review
from app.marketing.gates import GateReport
from app.marketing.reader import BlindRead, BlindReader, PanelRead, personas_for
from app.marketing.request import CampaignRequest
from app.marketing.strategist import Strategist
from app.marketing.tournament import PreferenceJudge
from app.marketing.writer import EmailWriter
from tests.marketing.conftest import (
    RoleScriptedProvider,
    campaign_brief,
    make_session,
    votes_for_the_challenger,
    votes_for_the_champion,
)


@pytest.fixture
def observed():
    path = Path(__file__).resolve().parents[2] / "eval/fixtures/campaign_quality/slack-launch-retest.json"
    return CampaignQualityCase.model_validate_json(path.read_text(encoding="utf-8"))


@pytest.fixture
def launch_material(observed):
    return KnowledgeArtifacts(
        business=BusinessProfile(company_name="orqAgent", what_it_does="Build AI agents without code"),
        evidence=EvidenceLedger(entries=[
            Evidence(id=item.id, kind=EvidenceKind.FEATURE, claim=item.text, verbatim=item.text)
            for item in observed.context.evidence
        ]),
        audience=AudienceModel(segments=[Segment(
            name="Ops or IT generalist considering an internal Slack answer-bot",
            situation="Considering an assistant over company documents in Slack.",
        )]),
    )


def envelope(email: Email) -> str:
    fields = {
        "SUBJECT": email.subject, "PREVIEW": email.preview_text,
        "EYEBROW": email.eyebrow, "HEADLINE": email.headline, "GREETING": email.greeting,
        "CTA": email.call_to_action, "SIGNOFF": email.sign_off, "PS": email.postscript,
        "BODY": email.body,
    }
    return "\n".join(f"{key}: {value}" for key, value in fields.items())


@pytest.mark.asyncio
@pytest.mark.parametrize("challenger_wins", [True, False])
async def test_disputed_relevance_gets_a_comparison_without_erasing_the_warning(
    observed, launch_material, challenger_wins,
):
    """A single mismatch used to end this run before its available duel."""
    provider = RoleScriptedProvider()
    provider.push("email_writer", *(envelope(draft.email) for draft in observed.drafts))
    provider.push("blind_reader", *[
        BlindRead(
            understood=True, pull=6, situation_matches=matches,
            relevance_feedback="The small test leaves full deployment questions unanswered.",
        ).model_dump_json()
        for matches in (True, True, True, False, True, True)
    ])
    provider.set_default("conversion_critic", Critique(
        verdict="revise", summary="Remove the unsupported team ownership assertion.",
    ).model_dump_json())
    votes = votes_for_the_challenger if challenger_wins else votes_for_the_champion
    provider.push("preference_judge", *votes(4))
    session = make_session(provider)
    segment = launch_material.audience.primary()
    people = personas_for(launch_material.audience, segment, panel=True)
    loop = CraftLoop(
        writer=EmailWriter(session), reader=BlindReader(session), critic=ConversionCritic(session),
        artifacts=launch_material, evidence=EvidenceIndex(launch_material.evidence),
        personas=people, merge_fields=[], max_revisions=1, judge=PreferenceJudge(session),
    )
    outcome = await loop.craft(
        brief=EmailBrief(single_idea="Try a document assistant in Slack", evidence_ids=["E11", "E90", "E22"]),
        campaign=CampaignBrief(reader_segment=segment.name, interpretation="A product launch"),
        request=CampaignRequest(name="Regression", request="Announce the launch in one email"),
        previous=[],
    )
    assert provider.calls_by_role["preference_judge"] == 4
    assert provider.calls_by_role["email_writer"] == 2
    assert provider.calls_by_role["blind_reader"] == 6
    assert provider.calls_by_role["conversion_critic"] == 1
    assert outcome.best.attempt == (2 if challenger_wins else 1)
    assert outcome.versions[1].duel is not None
    assert not outcome.versions[1].read.relevant
    assert not outcome.shipped_clean
    # The comparison stays blind to the brief and to previous verdicts.
    for request in provider.requests_for("preference_judge"):
        assert "Remove the unsupported team ownership assertion" not in request.system_prompt
        assert "full deployment questions unanswered" not in request.system_prompt
        assert all(render_review(draft.email) in request.system_prompt for draft in observed.drafts)


@pytest.mark.asyncio
async def test_strategy_biography_is_not_passed_to_the_writer(launch_material, observed):
    segment = launch_material.audience.primary()
    invented = "Her team has eleven unowned pipelines and postponed its build in June."
    planned = json.loads(campaign_brief(1))
    planned.update(reader=invented, reader_segment=segment.name)
    provider = RoleScriptedProvider({"strategist": json.dumps(planned)})
    provider.push("email_writer", envelope(observed.drafts[0].email))
    session = make_session(provider)
    request = CampaignRequest(
        name="Launch", request="Announce the launch in one email",
        target_market="Recipients who asked for a launch notification",
    )
    brief = await Strategist(session).build(
        request=request, artifacts=launch_material, corpus=SourceCorpus(),
        contract=parse_contract(request.request), chosen_segment=segment.name,
    )
    assert invented not in brief.reader
    assert segment.name in brief.reader
    assert segment.situation in brief.reader
    assert "inferred" in brief.reader
    assert request.target_market in brief.reader
    await EmailWriter(session).draft(
        brief=brief.emails[0], campaign=brief, request=request, artifacts=launch_material, previous=[],
    )
    prompt = provider.requests_for("email_writer")[0].system_prompt
    assert invented not in prompt
    assert request.target_market in prompt


@pytest.mark.asyncio
async def test_critic_gets_the_scaling_source_despite_reader_skepticism(observed, launch_material):
    provider = RoleScriptedProvider(
        {
            "conversion_critic": Critique(
                verdict="ship", failure_mode="none"
            ).model_dump_json()
        }
    )
    await ConversionCritic(make_session(provider)).critique(
        email=observed.drafts[0].email, brief=EmailBrief(evidence_ids=["E22"]),
        campaign=CampaignBrief(), artifacts=launch_material, gates=GateReport(),
        read=PanelRead(reads=[BlindRead(biggest_doubt="I do not believe it scales automatically.")]),
    )
    prompt = provider.requests_for("conversion_critic")[0].system_prompt
    assert '[E22]' in prompt
    assert launch_material.evidence.get("E22").verbatim in prompt
    assert "I do not believe it scales automatically." in prompt


@pytest.mark.asyncio
async def test_related_objection_does_not_restore_a_removed_recipient_history(
    observed, launch_material,
):
    launch_material.audience.objections = [Objection(
        objection="Internal tooling maintenance after the original builder leaves",
        answer="Hosted document retrieval", evidence_ids=["E11"],
    )]
    provider = RoleScriptedProvider({"email_writer": envelope(observed.drafts[0].email)})
    await EmailWriter(make_session(provider)).draft(
        brief=EmailBrief(objection="Internal tooling maintenance"),
        campaign=CampaignBrief(reader_segment=launch_material.audience.primary().name),
        request=CampaignRequest(name="Launch", request="Announce the launch in one email"),
        artifacts=launch_material, previous=[],
    )
    prompt = provider.requests_for("email_writer")[0].system_prompt
    assert "original builder leaves" not in prompt
    assert "Internal tooling maintenance" in prompt
    assert "Hosted document retrieval" in prompt
    assert "[E11]" in prompt
    assert "inferred" in prompt
