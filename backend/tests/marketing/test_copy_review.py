"""Data-flow and lexical regression checks; these do not measure copy quality."""

from html.parser import HTMLParser

import pytest

from app.knowledge.artifacts import KnowledgeArtifacts, Segment, Sophistication
from app.knowledge.ledger import Evidence, EvidenceIndex, EvidenceKind
from app.marketing.briefs import ArgumentOption, CampaignBrief, EmailBrief
from app.marketing.craft import CraftLoop, EmailVersion, _unchanged
from app.marketing.critic import ConversionCritic, Critique, Edit
from app.marketing.email_copy import parse_email, render_review
from app.marketing.gates import GateReport, copy_review_gate, run_all
from app.marketing.reader import BlindReader, PanelRead
from app.marketing.render_html import BrandStyle, EmailTier, render_html
from app.marketing.request import CampaignRequest
from app.marketing.writer import EmailWriter
from tests.marketing.conftest import (
    RoleScriptedProvider,
    blind_read,
    email_draft,
    make_session,
)


def evidence(text):
    return Evidence(id="S1", kind=EvidenceKind.FEATURE, claim=text, verbatim=text)


def email(**changes):
    return parse_email(email_draft(), 1).model_copy(update=changes)


@pytest.mark.parametrize("claim,support,flagged", [
    ("See what each answer cost.", "Analytics displays daily spend trends.", True),
    ("See cost per answer in USD.", "Each run consumes credits.", True),
    ("See cost per answer in USD.", "The dashboard shows cost per answer in credits.", True),
    ("See cost per answer.", "The dashboard does not show cost per answer.", True),
    ("See cost per answer.", "The dashboard shows cost per answer.", False),
    ("See cost per answer.", "The dashboard shows estimated cost per answer.", True),
    ("See estimated cost per answer.", "The dashboard shows estimated cost per answer.", False),
    ("See estimated cost per run in chat.", "The API shows estimated cost per run.", True),
    ("Start your bot with no extra configuration.",
     "Analytics tracks daily spend with no extra configuration.", True),
    ("Analytics tracks daily spend with no extra configuration.",
     "Analytics tracks daily spend with no extra configuration.", False),
    ("An in-house script cannot report spend.", "Analytics reports spend.", True),
    ("An in-house script can add its own reporting. Analytics includes spend reports.",
     "Analytics includes spend reports.", False),
])
def test_scope_cues_check_evidence_without_becoming_truth_vetoes(claim, support, flagged):
    report = copy_review_gate(email(body=claim, postscript=""), [evidence(support)])
    assert bool(report.advisory) is flagged
    assert not report.blocking
    if flagged:
        assert claim.split(".")[0] in report.advisory[0].detail


def test_absolute_diy_limit_can_refer_to_the_previous_sentence():
    draft = email(body="A responder wired from events and a model will answer. "
                 "What it will not tell you is what a week of questions cost.")
    report = copy_review_gate(draft, [])
    assert any("DIY" in issue.detail for issue in report.advisory)


def test_eyebrow_reaches_checks_and_changes_are_not_mistaken_for_identical_copy(artifacts):
    original = email(headline="A new way to write", eyebrow="WHAT'S NEW")
    changed = original.model_copy(update={"eyebrow": "SAVE $9876"})
    assert not _unchanged(original, changed)
    gates, _ = run_all(
        changed, evidence=EvidenceIndex(artifacts.evidence), offer=artifacts.offer,
        ledger=artifacts.evidence.entries,
    )
    assert any(issue.gate == "evidence" and "9876" in issue.detail for issue in gates.blocking)
    assert "WHAT'S NEW" in render_review(original)
    assert "WHAT'S NEW" not in render_review(original.model_copy(update={"headline": ""}))


class Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def test_review_covers_repetition_created_by_assembly_and_ignores_identity():
    draft = email(
        eyebrow="WHAT'S NEW", headline="Read the launch details",
        body="Read the full launch details.\n\nTry the new view.\n\nKeep your existing workflow.",
        call_to_action="Read the full launch details", postscript="Read the full launch details.",
        sign_off="Read the full launch details",
    )
    parsed = Text()
    parsed.feed(render_html(draft, EmailTier.BRANDED, BrandStyle(
        name="Sender", footer_lines=["Read the full launch details", "Sender address"],
    )))
    html_text = " ".join(parsed.parts)
    assert html_text.count("Read the full launch details") == 5
    assert render_review(draft).count("Read the full launch details") == 4
    report = copy_review_gate(draft, [])
    repeats = [issue for issue in report.advisory if issue.gate == "assembly-review"]
    assert len(repeats) == 2  # CTA and PS, not sign-off or footer
    assert 'CTA: "Read the full launch details"' in repeats[0].detail
    assert 'P.S.: "Read the full launch details."' in repeats[1].detail
    assert not copy_review_gate(draft.model_copy(update={
        "call_to_action": "Open the release", "postscript": "",
    }), []).issues


def loop(provider, artifacts, max_revisions=1):
    session = make_session(provider)
    return CraftLoop(
        writer=EmailWriter(session), reader=BlindReader(session),
        critic=ConversionCritic(session), artifacts=artifacts,
        evidence=EvidenceIndex(artifacts.evidence), personas=["A release engineer"],
        merge_fields=[], max_revisions=max_revisions,
    )


@pytest.mark.asyncio
async def test_critic_gets_selected_audience_stage_intent_and_actual_candidate(provider, artifacts):
    artifacts.audience.segments = [Segment(
        name="Existing operators", situation="Already operating production agents.",
        sophistication=Sophistication.PRODUCT_AWARE,
    )]
    campaign = CampaignBrief(
        reader_segment="Existing operators", reader="An operator",
        interpretation="Announce the newly available reporting view to current users.",
        orientation="An agent operations console",
    )
    draft = email(eyebrow="NEW REPORT", headline="Find the daily totals")
    version = EmailVersion(1, draft, GateReport(), PanelRead(), idea="The selected alternative")
    await loop(provider, artifacts)._critique(
        version, EmailBrief(single_idea="The original idea"), campaign, 1,
    )
    prompt = provider.requests_for("conversion_critic")[0].system_prompt
    assert "Already operating production agents." in prompt
    assert "They already know roughly what this product is" in prompt
    assert campaign.interpretation in prompt
    assert campaign.orientation in prompt
    assert "The one idea it owns: The selected alternative" in prompt
    assert "The one idea it owns: The original idea" not in prompt
    assert "NEW REPORT" in prompt


@pytest.mark.asyncio
@pytest.mark.parametrize("unsupported", [False, True])
async def test_feedback_survives_format_repair_and_revised_claims_are_checked(
    provider: RoleScriptedProvider, artifacts: KnowledgeArtifacts, unsupported: bool,
):
    edit = Edit(
        line="See what each answer cost.", severity="major",
        problem="Only daily aggregate spend is documented.",
        fix="Name the daily aggregate and remove the per-answer promise.",
    )
    provider.set_default("conversion_critic", Critique(edits=[edit]).model_dump_json())
    initial = email_draft() + "\n\nSee what each answer cost."
    revised = email_draft(subject="Read the daily totals")
    if unsupported:
        revised += "\n\nThe price is $9876 per month."
    provider.push("email_writer", initial, "BODY: malformed revision", revised)
    provider.push("blind_reader", blind_read(pull=4), blind_read(pull=9))
    outcome = await loop(provider, artifacts).craft(
        brief=EmailBrief(single_idea="A supported report"),
        campaign=CampaignBrief(interpretation="A product announcement"),
        request=CampaignRequest(name="Scope regression", request="Write one email"), previous=[],
    )
    for request in provider.requests_for("email_writer")[1:]:
        task = "\n".join(message.content for message in request.messages)
        for value in (edit.line, edit.problem, edit.fix, "major"):
            assert value in task
    repaired_task = provider.requests_for("email_writer")[2].messages[-1].content
    assert "BODY: malformed revision" in repaired_task
    assert len(outcome.versions) == 2
    assert bool(outcome.versions[-1].gates.blocking) is unsupported
    assert outcome.best.attempt == (1 if unsupported else 2)
    assert provider.calls_by_role["conversion_critic"] == 1
    assert provider.calls_by_role["email_writer"] == 3


@pytest.mark.asyncio
async def test_missing_material_stops_before_a_futile_rewrite(provider, artifacts):
    provider.set_default(
        "conversion_critic",
        Critique(
            verdict="revise",
            failure_mode="missing_material",
            strategy_gap="A verified setup guide is absent from the campaign material.",
            summary="The writer cannot invent the destination.",
        ).model_dump_json(),
    )
    provider.set_default("blind_reader", blind_read(pull=4, would_act=False))

    outcome = await loop(provider, artifacts, max_revisions=2).craft(
        brief=EmailBrief(single_idea="Inspect the integration before signup"),
        campaign=CampaignBrief(interpretation="A product announcement"),
        request=CampaignRequest(name="Missing guide", request="Write one launch email"),
        previous=[],
    )

    assert outcome.unresolved_strategy == (
        "A verified setup guide is absent from the campaign material."
    )
    assert provider.calls_by_role["email_writer"] == 1
    assert provider.calls_by_role["blind_reader"] == 1
    assert provider.calls_by_role["conversion_critic"] == 1


@pytest.mark.asyncio
async def test_strategy_failure_pivots_with_the_complete_alternative(provider, artifacts):
    provider.set_default(
        "conversion_critic",
        Critique(
            verdict="revise",
            failure_mode="argument",
            strategy_gap="Account creation is too large a first step for this proposition.",
        ).model_dump_json(),
    )
    provider.push(
        "blind_reader",
        blind_read(pull=4, would_act=False),
        blind_read(pull=8, would_act=True),
    )
    alternative = ArgumentOption(
        single_idea="Inspect one supported setup path first",
        mechanism="A verified guide shows the configuration",
        evidence_ids=["E2"],
        call_to_action="Read the setup guide",
        next_step_decision="Whether this setup path fits the current auth flow",
        next_step_value="The guide shows the supported configuration",
        next_step_evidence_ids=["E2"],
        next_step_limit="It does not prove production deliverability",
        subject_strategy="Name the integration",
    )

    outcome = await loop(provider, artifacts, max_revisions=2).craft(
        brief=EmailBrief(
            single_idea="Create an account now",
            call_to_action="Start the trial",
            alternative_arguments=[alternative],
        ),
        campaign=CampaignBrief(interpretation="A product announcement"),
        request=CampaignRequest(name="Pivot CTA", request="Write one launch email"),
        previous=[],
    )

    assert outcome.pivoted_to == alternative.single_idea
    assert outcome.best.idea == alternative.single_idea
    assert outcome.selected_brief.call_to_action == "Read the setup guide"
    assert outcome.selected_brief.next_step_evidence_ids == ["E2"]
    final_prompt = provider.requests_for("email_writer")[-1].system_prompt
    assert "What it asks for: Read the setup guide" in final_prompt
    assert "Evidence it spends: E2" in final_prompt
    assert alternative.next_step_decision in final_prompt
    assert alternative.next_step_limit in final_prompt
