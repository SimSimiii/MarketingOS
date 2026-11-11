"""Optional steering before a run: statuses, collisions, and that it lasts.

Scripted provider throughout - what is asserted is where the user's choices
go (the plan, every writer and critic prompt, the gate), never what a model
does with them.
"""

import json

import pytest

from app.knowledge.ledger import Evidence, EvidenceContext, EvidenceKind, EvidenceStrength
from app.marketing.briefs import CampaignBrief, EmailBrief, EmailSteering
from app.marketing.email_copy import parse_email
from app.marketing.pipeline import EmailCampaignPipeline
from app.marketing.policy import PRESETS
from app.marketing.request import CampaignRequest
from app.marketing.steering import (
    CampaignSteering,
    SteeringInstruction,
    SteeringItem,
    apply_steering,
    check_steering,
    claim_boundary,
    render_for_strategy,
    steering_gate,
    steering_options,
)
from tests.marketing.conftest import (
    FakeKnowledgeGateway,
    RoleScriptedProvider,
    artifacts_fixture,
    campaign_brief,
    default_answers,
    email_draft,
    make_session,
    varied_draft,
)


def _steering(*items: tuple[str, str], instructions=()) -> CampaignSteering:
    return CampaignSteering(
        items=[SteeringItem(id=item_id, choice=choice) for item_id, choice in items],
        instructions=[SteeringInstruction(**item) for item in instructions],
    )


def _brief(count: int = 2) -> CampaignBrief:
    return CampaignBrief(emails=[
        EmailBrief(position=position, single_idea=f"idea {position}",
                   evidence_ids=["E2"] if position == 1 else [])
        for position in range(1, count + 1)
    ])


def _request(steering: CampaignSteering | None) -> CampaignRequest:
    return CampaignRequest(
        name="Launch", request="Write me 2 emails that make developers try Notewright",
        steering=steering,
    )


def _body(lead: str) -> str:
    """A body the format checks accept, opening on `lead`."""
    return (
        f"{lead}\n\n"
        "Every release note started as a changelog nobody read, and ended as a paragraph you\n"
        "rewrote twice before shipping it.\n\n"
        "Notewright turns commits you already pushed into that paragraph, before you sit down.\n"
        "You edit it or you send it.\n\n"
        "Most people ask whether it sounds like them. It reads your older notes first, so it does."
    )


def _pipeline(provider: RoleScriptedProvider) -> EmailCampaignPipeline:
    return EmailCampaignPipeline(
        session=make_session(provider),
        knowledge=FakeKnowledgeGateway(compiled=artifacts_fixture()),
        policy=PRESETS["fast"],
    )


# ------------------------------------------------------------------ options


def test_options_separate_usable_facts_strategy_and_what_needs_confirming():
    artifacts = artifacts_fixture()
    artifacts.evidence.entries.append(Evidence(
        id="E3", kind=EvidenceKind.TESTIMONIAL, claim="teams love it",
        verbatim="People seem to like it.", strength=EvidenceStrength.WEAK,
    ))
    options = {option.id: option for option in steering_options(artifacts)}

    assert options["evidence:E1"].status == "usable"
    assert options["evidence:E1"].group == "proof"
    assert options["evidence:E2"].group == "price"
    # Vague in the source: selectable, never promoted to a claim.
    assert options["evidence:E3"].status == "to_confirm"
    plan = next(option for option in options.values() if option.id.startswith("plan:"))
    assert plan.status == "to_confirm", "a plan with no ledger fact behind it is not verified"
    assert any(o.group == "audience" and o.status == "strategic" for o in options.values())
    assert any(o.id.startswith("cta:") and o.status == "strategic" for o in options.values())


def test_no_compiled_knowledge_offers_nothing_and_requires_nothing():
    assert steering_options(None) == []
    assert check_steering(CampaignSteering(), []) == []


def test_including_a_price_with_unknown_billing_does_not_verify_it():
    artifacts = artifacts_fixture()
    artifacts.evidence.entries.append(Evidence(
        id="E-billing", kind=EvidenceKind.PRICE, claim="Pro costs €20 per month",
        verbatim="Pro €20 per month", strength=EvidenceStrength.STRONG,
        context=EvidenceContext(claim_scope="offer", limitations="Billing terms unknown."),
    ))
    options = steering_options(artifacts)
    option = next(item for item in options if item.id == "evidence:E-billing")
    assert option.status == "to_confirm"
    brief = _brief()
    apply_steering(brief, _steering((option.id, "include")), artifacts, options=options)
    assert all("E-billing" not in email.evidence_ids for email in brief.emails)


# ---------------------------------------------------------------- conflicts


def test_a_price_direction_beside_an_excluded_price_is_a_conflict():
    options = steering_options(artifacts_fixture())
    conflicts = check_steering(
        _steering(("evidence:E2", "exclude"),
                  instructions=[{"text": "Put the price in the first line"}]),
        options,
    )
    assert any(item.severity == "conflict" and "price" in item.message for item in conflicts)


def test_opposite_directions_and_an_email_that_does_not_exist_are_flagged():
    conflicts = check_steering(
        _steering(instructions=[
            {"text": "Make it shorter"},
            {"text": "More detailed please", "scope": "email", "position": 5},
        ]),
        steering_options(artifacts_fixture()),
        email_count=3,
    )
    messages = " ".join(item.message for item in conflicts)
    assert "opposite" in messages
    assert "email 5" in messages


def test_including_an_unverified_item_says_it_stays_context():
    options = steering_options(artifacts_fixture())
    plan = next(option for option in options if option.id.startswith("plan:"))
    conflicts = check_steering(_steering((plan.id, "include")), options)
    assert any(item.severity == "notice" and "not verified" in item.message for item in conflicts)


# ------------------------------------------------------------- applying it


def test_exclusion_leaves_every_slot_and_its_figures_are_blocked():
    artifacts = artifacts_fixture()
    brief = _brief()
    notes = apply_steering(brief, _steering(("evidence:E2", "exclude")), artifacts)

    for email in brief.emails:
        assert "E2" not in email.evidence_ids
        assert "E2" in email.forbidden_evidence_ids
        assert email.steering.excluded_values, "the figures only E2 states are gated"
    assert notes


def test_inclusion_is_assigned_to_one_email_and_survives_a_pivot():
    artifacts = artifacts_fixture()
    brief = _brief()
    apply_steering(brief, _steering(("evidence:E1", "include")), artifacts)

    holders = [email for email in brief.emails if "E1" in email.steering.include_evidence_ids]
    assert len(holders) == 1 and "E1" in holders[0].evidence_ids
    # The loop may change the idea; it may not drop what the user asked for.
    pivoted = holders[0].with_argument(holders[0].primary_argument().model_copy(
        update={"single_idea": "another idea", "evidence_ids": []}))
    assert "E1" in pivoted.evidence_ids
    assert "E1" not in pivoted.forbidden_evidence_ids


def test_inclusion_never_crosses_an_existing_claim_boundary():
    artifacts = artifacts_fixture()
    brief = _brief()
    for email in brief.emails:
        email.forbidden_evidence_ids = ["E1"]
    notes = apply_steering(brief, _steering(("evidence:E1", "include")), artifacts)
    assert all("E1" not in email.evidence_ids for email in brief.emails)
    assert any("boundary" in note for note in notes)


def test_a_fact_outside_the_audience_boundary_is_flagged_and_never_named_to_the_planner():
    # Regression from a live Buttondown run: the inclusion was refused by the
    # brief's boundary, but the steering block had already told the planner
    # to use the fact, and the shipped email stated it.
    artifacts = artifacts_fixture()
    options = steering_options(artifacts, boundary=frozenset({"E1"}))
    by_id = {option.id: option for option in options}
    assert by_id["evidence:E1"].outside_boundary
    assert by_id["evidence:E1"].status == "to_confirm"

    steering = _steering(("evidence:E1", "include"))
    conflicts = check_steering(steering, options)
    assert any(c.severity == "conflict" and "outside the claims" in c.message for c in conflicts)
    block = render_for_strategy(steering, options)
    assert "nine seconds" not in block

    brief = _brief()
    notes = apply_steering(brief, steering, artifacts, options)
    assert any("Kept [E1] out" in note for note in notes)
    for email in brief.emails:
        assert "E1" not in email.evidence_ids
        assert "nine seconds" not in email.render()


def test_claim_boundary_mirrors_the_brief_normalization():
    artifacts = artifacts_fixture()
    from types import SimpleNamespace

    narrow = SimpleNamespace(forbidden_evidence_ids=["E2"], v2_claim_boundary=True,
                             allowed_evidence_ids=["E1"])
    assert claim_boundary(narrow, artifacts) == {"E2"}
    open_ = SimpleNamespace(forbidden_evidence_ids=[], v2_claim_boundary=False,
                            allowed_evidence_ids=[])
    assert claim_boundary(open_, artifacts) == frozenset()
    assert claim_boundary(None, artifacts) == frozenset()


def test_scoped_directions_reach_only_their_email():
    brief = _brief()
    apply_steering(brief, _steering(instructions=[
        {"text": "Keep it under 120 words"},
        {"text": "State the price first", "scope": "email", "position": 2},
    ]), artifacts_fixture())
    assert brief.emails[0].steering.directions == ["Keep it under 120 words"]
    assert brief.emails[1].steering.directions == ["Keep it under 120 words", "State the price first"]
    assert "Direction: State the price first" in brief.emails[1].render()
    assert "State the price first" not in brief.emails[0].render()


def test_without_steering_the_brief_is_untouched():
    brief = _brief()
    before = brief.model_dump()
    assert apply_steering(brief, None, artifacts_fixture()) == []
    assert apply_steering(brief, CampaignSteering(), artifacts_fixture()) == []
    assert brief.model_dump() == before
    assert "User steering" not in brief.emails[0].render()


# --------------------------------------------------------------------- gate


def test_gate_blocks_a_figure_from_excluded_material_and_advises_a_missing_inclusion():
    artifacts = artifacts_fixture()
    brief = _brief()
    apply_steering(brief, _steering(("evidence:E2", "exclude"), ("evidence:E1", "include")),
                   artifacts)
    holder = next(e for e in brief.emails if e.steering.include_evidence_ids)
    draft = parse_email(email_draft(body=_body("The Team plan costs $29/month and that is all.")), 1)

    report = steering_gate(draft, holder.steering, artifacts.evidence.entries)
    assert any(issue.gate == "user-steering" and "$29" in issue.detail for issue in report.blocking)
    assert any("E1" in issue.detail for issue in report.advisory)


def test_a_figure_also_stated_by_kept_material_is_not_blocked():
    artifacts = artifacts_fixture()
    artifacts.evidence.entries.append(Evidence(
        id="E9", kind=EvidenceKind.FEATURE, claim="1,500 credits",
        verbatim="Accounts include 1,500 credits.",
    ))
    brief = _brief()
    apply_steering(brief, _steering(("evidence:E2", "exclude")), artifacts)
    draft = parse_email(email_draft(body=_body("You start with 1,500 credits on day one.")), 1)
    report = steering_gate(draft, brief.emails[0].steering, artifacts.evidence.entries)
    assert not report.blocking


def test_empty_steering_gate_is_free():
    draft = parse_email(email_draft(), 1)
    assert steering_gate(draft, EmailSteering(), []).issues == []


# ---------------------------------------------------------------- whole run


@pytest.mark.asyncio
async def test_steering_reaches_the_plan_and_every_writer_call():
    provider = RoleScriptedProvider(default_answers())
    provider.set_default("strategist", campaign_brief(2))
    steering = _steering(("evidence:E2", "exclude"), instructions=[
        {"text": "Keep it under 120 words"},
        {"text": "Mention the trial first", "scope": "email", "position": 2},
    ])
    result = await _pipeline(provider).run(_request(steering))

    assert result.delivered
    strategist = provider.requests_for("strategist")[0].system_prompt or ""
    assert "User steering" in strategist and "Must not be used" in strategist
    writers = provider.requests_for("email_writer")
    assert writers and all("Direction: Keep it under 120 words" in (r.system_prompt or "")
                           for r in writers)
    second = [r for r in writers if "Position: 2" in (r.system_prompt or "")]
    first = [r for r in writers if "Position: 1" in (r.system_prompt or "")]
    assert second and all("Mention the trial first" in (r.system_prompt or "") for r in second)
    assert first and not any("Mention the trial first" in (r.system_prompt or "") for r in first)
    for email in result.brief.emails:
        assert "E2" in email.forbidden_evidence_ids


@pytest.mark.asyncio
async def test_a_draft_using_excluded_material_is_rewritten_not_shipped():
    provider = RoleScriptedProvider(default_answers())
    provider.review("The $29 claim uses material explicitly excluded by the user.")
    provider.set_default("strategist", campaign_brief(1))
    provider.push("email_writer", email_draft(
        body=_body("Team is $29/month, and that buys a lot of release notes.")))
    provider.set_default("email_writer", varied_draft)
    result = await _pipeline(provider).run(CampaignRequest(
        name="One", request="Write me one email for developers",
        steering=_steering(("evidence:E2", "exclude")),
    ))

    outcome = result.outcomes[0]
    assert any(issue.gate == "claim-review" for issue in outcome.versions[0].gates.blocking)
    assert not any(issue.gate == "user-steering" for issue in outcome.best.gates.blocking)
    assert "$29" not in outcome.email.body


@pytest.mark.asyncio
async def test_the_minimal_path_is_unchanged_without_steering():
    provider = RoleScriptedProvider(default_answers())
    result = await _pipeline(provider).run(_request(None))
    assert result.delivered
    assert "User steering" not in (provider.requests_for("strategist")[0].system_prompt or "")
    assert all(email.steering.is_empty for email in result.brief.emails)
    assert json.loads(result.brief.model_dump_json())["emails"][0]["steering"]["directions"] == []
