"""Reader value stays attached to its complete evidence through argument changes."""

import pytest

from app.marketing.briefs import ArgumentOption, CampaignBrief, EmailBrief, ValueCase
from app.marketing.contract import parse_contract
from app.marketing.gates import GateReport
from app.marketing.reader import PanelRead
from app.marketing.request import CampaignRequest
from app.marketing.strategist import Strategist
from app.marketing.writer import EmailWriter
from tests.marketing.conftest import (
    RoleScriptedProvider,
    artifacts_fixture,
    email_draft,
    make_session,
)
from tests.marketing.test_argument_integrity import tally_case


def value():
    return ValueCase(reader_benefit="Manage book orders and shipping together",
                     mechanism="Calculate shipping fees and receive payments",
                     evidence_ids=["E1", "E2"], decision_conditions=["Small product ranges"])


def test_legacy_brief_needs_no_value_configuration():
    brief = EmailBrief.model_validate({"single_idea": "Existing proposition"})
    assert brief.value_case == ValueCase()
    assert "Reader value to explain" not in brief.render()


def test_argument_pivot_carries_typed_value_without_aliasing():
    alternative = ArgumentOption(single_idea="Books", evidence_ids=["E1", "E2"], value_case=value())
    pivot = EmailBrief(evidence_ids=["E3"]).with_argument(alternative)
    restored = EmailBrief.model_validate_json(pivot.model_dump_json())
    assert restored.primary_argument().value_case == alternative.value_case
    assert "Manage book orders" in pivot.render()
    assert "Small product ranges" in pivot.render()
    pivot.value_case.decision_conditions.append("Changed")
    assert alternative.value_case.decision_conditions == ["Small product ranges"]


@pytest.mark.parametrize("allowed", [set(), {"E1"}, {"E2"}, {"E3"}])
def test_partial_support_does_not_keep_the_full_benefit(allowed):
    assert value().for_evidence(allowed) == ValueCase()
    assert value().render(allowed) == ""


def test_excluded_fact_cannot_support_visible_value():
    brief = EmailBrief(evidence_ids=["E1", "E2"], forbidden_evidence_ids=["E2"], value_case=value())
    assert "Manage book orders" not in brief.render()


def test_distinct_later_argument_keeps_its_shared_mechanism_dependency():
    campaign = CampaignBrief(emails=[
        EmailBrief(position=1, single_idea="Introduce the workflow", evidence_ids=["E1"]),
        EmailBrief(position=2, single_idea="Evaluate a plan for that workflow",
                   evidence_ids=["E1", "E2"], value_case=value()),
    ])
    result = Strategist(None)._normalize(
        campaign, parse_contract("Write 2 emails"), artifacts_fixture(),
    )
    assert result.emails[1].evidence_ids == ["E1", "E2"]
    assert result.emails[1].value_case == value()
    assert "Manage book orders" in result.emails[1].render()


def test_repaired_unsupported_argument_discards_dependent_value():
    artifacts, _, _, context, brief = tally_case()
    brief.emails[0].value_case = ValueCase(reader_benefit="No maintenance required",
                                         evidence_ids=["E21", "E33"])
    result = Strategist(None)._normalize(brief, parse_contract("Write 1 email"), artifacts, context)
    assert result.emails[0].value_case == ValueCase()
    assert "No maintenance required" not in result.render()


@pytest.mark.asyncio
async def test_draft_rewrite_and_user_adjustment_keep_value_and_conditions():
    provider = RoleScriptedProvider().set_default("email_writer", email_draft())
    brief = EmailBrief(evidence_ids=["E1", "E2"], value_case=value())
    writer = EmailWriter(make_session(provider))
    args = {"brief": brief, "campaign": CampaignBrief(emails=[brief]),
            "request": CampaignRequest(name="Value", request="Write one acquisition email"),
            "artifacts": artifacts_fixture(), "previous": []}
    draft = await writer.draft(**args)
    revised = await writer.revise(draft=draft, gates=GateReport(), read=PanelRead(), **args)
    await writer.adjust(draft=revised, instruction="Shorter", **args)
    requests = provider.requests_for("email_writer")
    assert len(requests) == 3
    for request in requests:
        assert "Manage book orders and shipping together" in request.system_prompt
        assert "Calculate shipping fees and receive payments" in request.system_prompt
        assert "Small product ranges" in request.system_prompt
