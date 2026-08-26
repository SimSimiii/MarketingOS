"""The pipeline end to end, with a scripted provider.

These are the tests that would have caught the failures the old architecture
was built to survive: a run that produces the wrong number of emails, a run
that ships an unsupported claim, a run that cannot stop.
"""

import json
from dataclasses import replace

import pytest

from app.knowledge.artifacts import KnowledgeArtifacts, Segment
from app.knowledge.ledger import Evidence, EvidenceKind
from app.marketing.cancellation import CancellationToken
from app.marketing.contract import parse_contract
from app.marketing.observer import RunObserver
from app.marketing.pipeline import EmailCampaignPipeline
from app.marketing.policy import PRESETS, ExecutionPolicy
from app.marketing.request import CampaignRequest
from app.runtime.model_session import _PROVIDER_ATTEMPTS as PROVIDER_ATTEMPTS
from tests.marketing.conftest import (
    CRITIQUE_REVISE,
    CRITIQUE_SHIP,
    FAIL,
    READ_FAIL,
    READ_PASS,
    FakeKnowledgeGateway,
    RoleScriptedProvider,
    artifacts_fixture,
    blind_read,
    campaign_brief,
    email_draft,
    make_session,
    varied_draft,
)


def build(
    provider: RoleScriptedProvider,
    policy: ExecutionPolicy | None = None,
    artifacts=None,
    **kwargs,
):
    gateway = FakeKnowledgeGateway(
        compiled=artifacts if artifacts is not None else artifacts_fixture()
    )
    pipeline = EmailCampaignPipeline(
        session=make_session(provider),
        knowledge=gateway,
        policy=policy or PRESETS["balanced"],
        **kwargs,
    )
    return pipeline, gateway


def refine_only(**overrides) -> ExecutionPolicy:
    """Balanced with everything that multiplies calls switched off.

    For the tests that are about what happens to a draft *after* it is judged.
    They script the writer and the reader turn by turn, and anything that buys
    more than one of a role's calls per attempt eats the responses queued for
    the rewrite loop - the test then fails for a reason that has nothing to do
    with what it asserts. Three candidate openings did that; so does a
    three-reader panel, and so does a subject bake-off with its own reader
    calls. Each of those has its own tests below.

    The tournament stays on where a test asks for it, but off by default here:
    with it on, "was this rewrite kept" is answered by a duel, and a test about
    the rewrite loop should not have to script one.
    """
    return PRESETS["balanced"].model_copy(
        update={
            "draft_candidates": 1,
            "reader_panel": False,
            "tournament": False,
            "subject_variants": 0,
            **overrides,
        }
    )


def bake_off_only(**overrides) -> ExecutionPolicy:
    """Balanced with the bake-off intact and every other judge switched off.

    The mirror of `refine_only`: for tests about which of several candidates
    ships. One cold reader per draft, so a test can script "this opening read
    at 9 and that one at 2" as three responses rather than nine; no run-off,
    so the score is what decides; no subject bake-off, so the reader calls a
    test counts are the ones it queued.
    """
    return PRESETS["balanced"].model_copy(
        update={
            "reader_panel": False,
            "tournament": False,
            "subject_variants": 0,
            **overrides,
        }
    )


@pytest.mark.asyncio
async def test_three_emails_asked_for_is_three_emails_delivered(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    pipeline, _ = build(provider)
    result = await pipeline.run(request_fixture)

    assert result.status == "completed"
    assert len(result.outcomes) == 3
    assert [email.position for email in result.emails] == [1, 2, 3]
    assert result.report.delivered == 3
    assert result.report.contract_violations == []


@pytest.mark.asyncio
async def test_compiled_knowledge_is_reused_rather_than_recompiled(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    """The second campaign for a business starts from what the first learned -
    the compiler is never called when the material has not changed."""
    pipeline, gateway = build(provider)
    await pipeline.run(request_fixture)

    assert provider.calls_by_role["knowledge_compiler"] == 0
    assert gateway.saves == []


@pytest.mark.asyncio
async def test_a_draft_that_did_not_land_is_rewritten_against_the_reader(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    provider.push("blind_reader", READ_FAIL, READ_PASS)
    provider.set_default("strategist", campaign_brief(1))

    pipeline, _ = build(provider, refine_only())
    result = await pipeline.run(request_fixture)

    outcome = result.outcomes[0]
    assert len(outcome.versions) == 2, "a failed read must produce a rewrite"
    assert outcome.best.attempt == 2

    rewrite_prompt = provider.requests_for("email_writer")[1].messages[0].content
    assert "honestly, I could not tell" in rewrite_prompt
    assert "cut the second paragraph" in rewrite_prompt


@pytest.mark.asyncio
async def test_a_rewrite_that_came_back_worse_is_thrown_away(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    """Rewriting copy that already worked usually sands the edges off it, so
    the loop keeps whichever version actually read better."""
    provider.set_default("strategist", campaign_brief(1))
    provider.push("blind_reader", READ_FAIL, READ_FAIL)

    pipeline, _ = build(provider, refine_only(max_revisions=1))
    result = await pipeline.run(request_fixture)

    outcome = result.outcomes[0]
    assert len(outcome.versions) == 2
    # Both reads scored the same; the tie goes to the draft that was already
    # there rather than to the rewrite.
    assert outcome.best.attempt == 1


@pytest.mark.asyncio
async def test_a_rewrite_that_changed_nothing_ends_the_loop(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    """Rewrites are bought one at a time, not in a block.

    A rewrite that comes back no better is the signal that more rewriting is
    not what this draft needs. Spending the rest of the budget anyway is how a
    run pays for a third and fourth attempt that score exactly what the second
    one did - which is most of what a failing email used to cost.
    """
    provider.set_default("strategist", campaign_brief(1))
    provider.set_default("blind_reader", READ_FAIL)

    pipeline, _ = build(provider, refine_only(max_revisions=3))
    result = await pipeline.run(request_fixture)

    outcome = result.outcomes[0]
    assert len(outcome.versions) == 2, "one rewrite proved it was not working; that is enough"
    assert outcome.stopped_early is True
    assert provider.calls_by_role["email_writer"] == 2, "two of the four writer turns, unspent"

    line = result.report.emails[0]
    assert line.rewrites_stopped_helping is True
    assert "rewriting had stopped moving it" in result.report.render()


@pytest.mark.asyncio
async def test_a_rewrite_is_told_which_angles_have_already_been_read(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    """Without this the loop has no memory: every rewrite sees the current
    draft and the last reader, so the third attempt is free to walk back onto
    the angle the first one was thrown away for - and does."""
    provider.set_default("strategist", campaign_brief(1))
    provider.push(
        "email_writer",
        email_draft(subject="The angle that was tried first"),
        email_draft(subject="The angle that was tried second"),
    )
    # Improving scores, so the loop keeps going and there is a third turn.
    provider.push(
        "blind_reader",
        blind_read(pull=3, would_act=False, biggest_doubt="I could not tell what it was for"),
        blind_read(pull=5, would_act=False),
    )

    pipeline, _ = build(provider, refine_only(max_revisions=3))
    await pipeline.run(request_fixture)

    third_turn = provider.requests_for("email_writer")[2].messages[0].content
    assert "The angle that was tried first" in third_turn
    assert "The angle that was tried second" in third_turn
    assert "I could not tell what it was for" in third_turn
    assert "has already been read" in third_turn


@pytest.mark.asyncio
async def test_an_unsupported_claim_blocks_the_email_and_is_named_to_the_writer(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    """The gate is the anti-hallucination mechanism: no model is asked whether
    the number is real."""
    provider.set_default("strategist", campaign_brief(1))
    provider.push(
        "email_writer",
        email_draft(
            body=(
                "Your release notes take 47 minutes each.\n\n"
                "That is most of a Friday afternoon gone to describing work that was already\n"
                "finished on Tuesday morning, and nobody ever put that time on a plan.\n\n"
                "Point it at the branch and read what comes back, then change what is wrong.\n"
                "It takes the commits you already pushed and writes the paragraph for you.\n\n"
                "Teams tell us the draft is close enough that arguing with it beats starting\n"
                "from an empty editor on a Friday."
            )
        ),
        varied_draft(1),
    )

    pipeline, _ = build(provider, refine_only())
    result = await pipeline.run(request_fixture)

    first_attempt = result.outcomes[0].versions[0]
    assert not first_attempt.gates.passed
    assert '"47 minutes"' in first_attempt.gates.render()

    rewrite_prompt = provider.requests_for("email_writer")[1].messages[0].content
    assert "47 minutes" in rewrite_prompt


@pytest.mark.asyncio
async def test_the_critic_can_send_back_copy_a_cold_reader_liked(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    """Brief drift is invisible to the reader, who has no brief - this is the
    failure only the critic can catch."""
    provider.set_default("strategist", campaign_brief(1))
    provider.push("conversion_critic", CRITIQUE_REVISE, CRITIQUE_SHIP)

    pipeline, _ = build(provider, refine_only())
    result = await pipeline.run(request_fixture)

    assert len(result.outcomes[0].versions) == 2
    rewrite_prompt = provider.requests_for("email_writer")[1].messages[0].content
    assert "conversion critic" in rewrite_prompt
    assert "switching-cost objection" in rewrite_prompt


@pytest.mark.asyncio
async def test_disabling_the_critic_skips_it_entirely(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    pipeline, _ = build(provider, PRESETS["fast"])
    await pipeline.run(request_fixture)
    assert provider.calls_by_role["conversion_critic"] == 0


@pytest.mark.asyncio
async def test_the_strategist_is_corrected_when_it_plans_the_wrong_number(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    """The count came out of the user's own sentence; a brief that got it
    wrong is wrong about the one thing that was never open to interpretation."""
    provider.push("strategist", campaign_brief(2), campaign_brief(3))

    pipeline, _ = build(provider)
    result = await pipeline.run(request_fixture)

    assert provider.calls_by_role["strategist"] == 2
    assert len(result.outcomes) == 3
    correction = provider.requests_for("strategist")[1].messages[0].content
    assert "exactly 3" in correction


@pytest.mark.asyncio
async def test_evidence_ids_the_ledger_does_not_have_are_dropped(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    """An id pointing at nothing would send the writer looking for a proof it
    cannot find."""
    brief = json.loads(campaign_brief(1))
    brief["emails"][0]["evidence_ids"] = ["E1", "E99"]
    provider.set_default("strategist", json.dumps(brief))

    pipeline, _ = build(provider)
    result = await pipeline.run(request_fixture)

    assert result.brief is not None
    assert result.brief.emails[0].evidence_ids == ["E1"]


@pytest.mark.asyncio
async def test_an_email_is_never_assigned_more_proof_than_it_can_argue(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    """The brief is read by the writer as "this is what this email is built
    on", and the critic asks afterwards whether the assigned evidence was
    spent. So a brief that assigns six facts asks for six facts on the page,
    and what comes back is a product page with a greeting."""
    artifacts = artifacts_fixture()
    artifacts.evidence.entries.extend(
        Evidence(
            id=f"E{index}",
            kind=EvidenceKind.FEATURE,
            claim=f"claim number {index}",
            verbatim=f"The source says claim number {index}.",
            source="https://example.com",
        )
        for index in range(3, 7)
    )
    brief = json.loads(campaign_brief(1))
    brief["emails"][0]["evidence_ids"] = ["E1", "E2", "E3", "E4", "E5", "E6"]
    provider.set_default("strategist", json.dumps(brief))

    pipeline, _ = build(provider, artifacts=artifacts)
    result = await pipeline.run(request_fixture)

    assert result.brief is not None
    assert result.brief.emails[0].evidence_ids == ["E1", "E2", "E3"], (
        "kept in the strategist's own ranking - the first ones are what it built the idea on"
    )


@pytest.mark.asyncio
async def test_the_writer_is_told_what_this_email_leaves_out(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    """The one instruction in the system that subtracts. Everything else a
    brief carries is a reason to put something on the page."""
    provider.set_default(
        "strategist",
        campaign_brief(
            1,
            emails=[
                {
                    "position": 1,
                    "single_idea": "the one idea this email owns",
                    "must_not_say": ["the pricing - email 3 owns it", "the security posture"],
                }
            ],
        ),
    )

    pipeline, _ = build(provider, refine_only())
    await pipeline.run(request_fixture)

    written = provider.requests_for("email_writer")[0].system_prompt or ""
    assert "the pricing - email 3 owns it" in written
    assert "the security posture" in written


@pytest.mark.asyncio
async def test_each_brief_is_told_what_the_earlier_ones_already_spent(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    pipeline, _ = build(provider)
    result = await pipeline.run(request_fixture)

    assert result.brief is not None
    assert result.brief.emails[0].must_not_reuse == []
    assert len(result.brief.emails[2].must_not_reuse) == 2


@pytest.mark.asyncio
async def test_cancelling_stops_between_emails_and_keeps_what_is_finished(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    """Degrading to "here are two of the three" beats failing a run that has
    minutes of good work in it."""
    token = CancellationToken()

    class CancelAfterFirst(RunObserver):
        def on_email_accepted(self, position, version):
            if position == 1:
                token.cancel()

    pipeline, _ = build(provider, cancel_token=token, observer=CancelAfterFirst())
    result = await pipeline.run(request_fixture)

    assert result.status == "cancelled"
    assert len(result.outcomes) == 1
    assert result.report.contract_violations, "a short delivery must be reported, not hidden"


@pytest.mark.asyncio
async def test_cancelling_mid_email_skips_the_rest_of_its_own_revision_loop(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    """The pipeline's own guard only checks between whole emails - a single
    email failing its cold read every time would otherwise keep buying a
    critique and a rewrite for every attempt up to max_revisions, regardless
    of a stop requested partway through. CraftLoop must catch this itself."""
    token = CancellationToken()

    class CancelAfterFirstRead(RunObserver):
        def on_read(self, position, attempt, read):
            if attempt == 1:
                token.cancel()

    provider.set_default("strategist", campaign_brief(1))
    provider.set_default("blind_reader", READ_FAIL)

    pipeline, _ = build(
        provider,
        refine_only(max_revisions=3),
        cancel_token=token,
        observer=CancelAfterFirstRead(),
    )
    result = await pipeline.run(request_fixture)

    outcome = result.outcomes[0]
    assert len(outcome.versions) == 1, "no revise should follow the cancelled attempt"
    assert provider.calls_by_role["email_writer"] == 1, "the rewrite must not be bought"
    assert provider.calls_by_role.get("conversion_critic", 0) == 0, "nor the critique that fed it"


@pytest.mark.asyncio
async def test_the_provider_going_away_hands_over_the_emails_already_written(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    """The most expensive bug this suite ever had, and it was invisible.

    A provider failure is a `ProviderError`, which is a `ModelRuntimeError` and
    not a `CampaignError` - so it went straight past the pipeline's own
    handler, past the craft loop, and into the orchestrator's crash path,
    which persists no assets and no report. A run that had already written and
    paid for two of three emails reported as a bare failure with nothing to
    show for it.

    The rule the guards already follow applies here too: stop between emails,
    keep what is finished, say why.
    """
    def writer(call: int) -> str:
        # Email 1 is drafted; from there the provider has stopped answering.
        return varied_draft(call) if call == 1 else FAIL

    provider.set_default("email_writer", writer)
    pipeline, _ = build(provider, refine_only())
    result = await pipeline.run(request_fixture)

    assert result.status == "provider_unavailable"
    assert len(result.outcomes) == 1, "the email that was finished must survive"
    assert result.report.emails[0].subject
    assert "stopped answering" in (result.abort_reason or "")
    assert result.report.contract_violations, "a short delivery is still reported as short"


@pytest.mark.asyncio
async def test_one_cold_reader_dropping_out_does_not_take_the_panel_with_it(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    """A panel is read concurrently, so an exception in one persona escapes
    `gather` and ends the run. `reported=False` already models a reader who
    never came back - a transport failure is one."""
    provider.set_default("strategist", campaign_brief(1))
    # Two readers answer; the third refuses every attempt the session makes.
    provider.push("blind_reader", READ_PASS, READ_PASS, *([FAIL] * PROVIDER_ATTEMPTS))

    pipeline, _ = build(provider, PRESETS["balanced"].model_copy(
        update={"draft_candidates": 1, "subject_variants": 0}
    ))
    result = await pipeline.run(request_fixture)

    assert result.status in ("completed", "degraded")
    read = result.outcomes[0].versions[0].read
    assert len(read.reads) == 3, "the panel keeps its shape"
    assert len(read.reported) == 2, "the reader that dropped out reports nothing"
    assert read.has_verdict, "two readers is still a verdict"


@pytest.mark.asyncio
async def test_a_run_that_fails_late_is_degraded_rather_than_failed(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    """Two finished emails behind a red badge is what teaches a user to
    distrust the badge on the runs that really did fail."""
    def writer(call: int) -> str:
        # The third email never comes back in a sendable shape, however often
        # the writer is asked - which is a CraftError, not a provider failure.
        return varied_draft(call) if call <= 2 else "not an email at all"

    provider.set_default("email_writer", writer)
    provider.set_default("strategist", campaign_brief(3))
    pipeline, _ = build(provider, refine_only())
    result = await pipeline.run(request_fixture)

    assert result.status == "degraded"
    assert len(result.outcomes) == 2
    assert result.report.notes, "and it says what went wrong"


@pytest.mark.asyncio
async def test_a_token_budget_stops_the_run(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    provider.tokens_per_call = 600
    policy = PRESETS["balanced"].model_copy(update={"max_total_tokens": 1_000})
    pipeline, _ = build(provider, policy)
    result = await pipeline.run(request_fixture)

    assert result.status == "budget_exhausted"
    assert "token budget" in (result.abort_reason or "")


@pytest.mark.asyncio
async def test_the_sequence_pass_reworks_the_email_the_arc_read_faults(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    """Individually fine, collectively a problem - the failure no single-email
    judge can see, because none of them is shown the other emails."""
    provider.set_default("strategist", campaign_brief(2))
    provider.push(
        "sequence_reviewer",
        json.dumps(
            {
                "escalates": False,
                "promise_is_consistent": True,
                "each_stands_alone": False,
                "notes": [
                    {
                        "position": 2,
                        "problem": "it assumes the reader opened email 1",
                        "fix": "make it stand alone",
                    }
                ],
                "summary": "Email 2 leans on email 1.",
            }
        ),
    )

    pipeline, _ = build(provider, refine_only())
    result = await pipeline.run(request_fixture)

    assert result.sequence is not None
    assert 2 in result.sequence.rework
    assert provider.calls_by_role["email_writer"] == 3, "the faulted email is rewritten"

    rework_prompt = provider.requests_for("email_writer")[2].messages[0].content
    assert "assumes the reader opened email 1" in rework_prompt


@pytest.mark.asyncio
async def test_repetition_inside_the_sequence_is_caught_while_writing(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    """The overlap check runs on every draft against the emails already
    accepted, so a repeat never survives to the sequence pass."""
    provider.set_default("strategist", campaign_brief(2))
    same = email_draft()
    provider.push("email_writer", same, same, varied_draft(2))

    pipeline, _ = build(provider, refine_only())
    result = await pipeline.run(request_fixture)

    second = result.outcomes[1]
    assert not second.versions[0].gates.passed
    assert "already appears in email 1" in second.versions[0].gates.render()
    assert second.best.attempt == 2, "the repeat is rewritten before it ships"


@pytest.mark.asyncio
async def test_a_single_email_never_runs_the_sequence_pass(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    provider.set_default("strategist", campaign_brief(1))
    pipeline, _ = build(provider)
    await pipeline.run(request_fixture)
    assert provider.calls_by_role["sequence_reviewer"] == 0


@pytest.mark.asyncio
async def test_the_report_records_what_held_the_copy_back(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    """The receipt, and the next campaign's memory."""
    pipeline, _ = build(provider)
    result = await pipeline.run(request_fixture)

    assert result.report.average_pull == 8
    assert result.report.knowledge_version == 1
    assert "no customer names" in result.report.render().lower()
    assert "Previous campaign" in result.report.render_learnings()


@pytest.mark.asyncio
async def test_a_writer_that_never_produces_a_sendable_email_fails_the_run(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    provider.set_default("strategist", campaign_brief(1))
    provider.set_default("email_writer", "I would be happy to help you write an email!")

    pipeline, _ = build(provider)
    result = await pipeline.run(request_fixture)

    assert result.status == "failed"
    assert "sendable email" in (result.abort_reason or "")


@pytest.mark.asyncio
async def test_no_model_call_is_ever_spent_on_deciding_what_runs_next(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    """The central claim of the redesign, asserted directly."""
    pipeline, _ = build(provider)
    await pipeline.run(request_fixture)

    # Every role here either distils knowledge, decides strategy, writes copy
    # or judges copy. None of them routes, which is the claim - the list grows
    # when the system buys more judgment and would be violated by one entry
    # called anything like "director".
    assert set(provider.calls_by_role) <= {
        "strategist",
        "email_writer",
        "subject_writer",
        "blind_reader",
        "preference_judge",
        "inbox_scanner",
        "conversion_critic",
        "sequence_reviewer",
        "knowledge_compiler",
    }
    assert "director" not in provider.calls_by_role


def test_the_contract_is_read_before_anything_runs(request_fixture: CampaignRequest):
    assert parse_contract(request_fixture.request).count == 3


# ------------------------------------------------- who the copy is judged by


SUPPORT_LEAD = "a support lead answering the same changelog question all week"

#: Three bodies that share no six-word run, so the overlap gate stays quiet
#: and a test about which opening won is not decided by a different gate.
_BODY_A = (
    "You wrote the same release note three times last month.\n\n"
    "Each one started as a changelog nobody read, and ended as a paragraph you rewrote twice\n"
    "before shipping it, on an afternoon that was supposed to belong to something else.\n\n"
    "Point it at the branch and read what comes back. You edit that, or you send it.\n\n"
    "Most people ask first whether it sounds like them. It reads your older notes, so it does."
)
_BODY_B = (
    "Friday afternoon is where your shipping week goes to die.\n\n"
    "The work was done on Tuesday. What is left is describing it, and describing it is the\n"
    "part nobody ever scheduled time for, so it lands on whoever is still online.\n\n"
    "Give it the entries you already published and it writes like those did.\n\n"
    "Teams tell us the draft is close enough that arguing with it beats an empty editor."
)
_BODY_C = (
    "Your changelog has a tone, and it is not the one you would use out loud.\n\n"
    "That happens when writing gets squeezed into whatever minutes are left before a deploy\n"
    "window closes, which is every week, which is why it reads the way it reads.\n\n"
    "Nothing to configure. Paste a branch name, then decide whether to keep the paragraph.\n\n"
    "Nobody has to change how they work for this, and that is most of why it survives."
)


def two_segments() -> KnowledgeArtifacts:
    """A business with more than one kind of buyer, which is every business.

    The single-segment fixture cannot express the failure below: with one
    segment, picking the wrong one and picking the right one look identical.
    """
    artifacts = artifacts_fixture()
    artifacts.audience.segments.append(
        Segment(name=SUPPORT_LEAD, situation="fields the same question after every deploy")
    )
    return artifacts


@pytest.mark.asyncio
async def test_the_draft_is_read_by_the_segment_the_brief_chose(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    """The copy is graded by the person it was written for, or the score is
    measuring the mismatch instead of the copy.

    A campaign aimed at someone who has no engineer, read by someone with a
    platform team, comes back rated on a premise the reader does not have -
    and then every rewrite in the run answers that reader's doubts, which
    makes the email worse for the person it is actually going to.
    """
    provider.set_default("strategist", campaign_brief(1, reader_segment=SUPPORT_LEAD))

    pipeline, _ = build(provider, refine_only(), artifacts=two_segments())
    result = await pipeline.run(request_fixture)

    assert result.brief is not None
    assert result.brief.reader_segment == SUPPORT_LEAD
    reader_prompt = provider.requests_for("blind_reader")[0].system_prompt
    assert SUPPORT_LEAD in reader_prompt
    assert "writes release notes by hand" not in reader_prompt


@pytest.mark.asyncio
async def test_a_mistyped_segment_is_recovered_from_the_reader_sentence(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    """The brief describes its reader twice - once as a name and once as a
    sentence - and the sentence is the one written with care. A name that
    matches nothing is not enough to give up on."""
    provider.set_default(
        "strategist",
        campaign_brief(
            1,
            reader_segment="Devs (weekly release cadence)",
            reader="a developer who ships weekly and writes release notes by hand",
        ),
    )

    pipeline, _ = build(provider, refine_only(), artifacts=two_segments())
    result = await pipeline.run(request_fixture)

    assert result.brief is not None
    assert result.brief.reader_segment == (
        "a developer who ships weekly and writes release notes by hand"
    )


@pytest.mark.asyncio
async def test_a_brief_that_names_nobody_we_know_falls_back_and_says_so(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    """Falling back is fine. Falling back silently is what let a whole run be
    graded by the wrong person without anything in the log saying so."""
    provider.set_default(
        "strategist",
        campaign_brief(
            1,
            reader_segment="chief revenue officers in logistics",
            reader="a chief revenue officer at a freight brokerage",
        ),
    )
    seen: list[str] = []

    class Watch(RunObserver):
        def on_phase(self, phase, message, data=None):
            if phase == "strategy":
                seen.append(message)

    pipeline, _ = build(provider, refine_only(), artifacts=two_segments(), observer=Watch())
    result = await pipeline.run(request_fixture)

    assert result.brief is not None
    assert result.brief.reader_segment == ""
    assert seen and "the brief named no segment we know" in seen[0]


# ------------------------------------------------------ several openings


@pytest.mark.asyncio
async def test_the_opening_a_stranger_responded_to_is_the_one_that_ships(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    """The point of writing more than one: which argument lands is not
    derivable from the brief, so it is decided by asking rather than by
    refining whichever one came out first."""
    provider.set_default("strategist", campaign_brief(1))
    provider.push(
        "email_writer",
        email_draft(subject="Opening one", body=_BODY_A),
        email_draft(subject="Opening two", body=_BODY_B),
        email_draft(subject="Opening three", body=_BODY_C),
    )
    provider.push("blind_reader", blind_read(pull=2), blind_read(pull=9), blind_read(pull=4))

    pipeline, _ = build(provider, bake_off_only(max_revisions=0))
    result = await pipeline.run(request_fixture)

    assert provider.calls_by_role["email_writer"] == 3, "three openings, one email"
    assert result.outcomes[0].email.subject == "Opening two"
    assert result.report.emails[0].pull == 9


@pytest.mark.asyncio
async def test_the_winning_opening_is_not_read_a_second_time(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    """The bake-off already paid for the winner's cold read. Buying it again
    is the whole saving of screening on the cheap judges, spent."""
    provider.set_default("strategist", campaign_brief(1))

    pipeline, _ = build(provider, bake_off_only(max_revisions=0))
    await pipeline.run(request_fixture)

    assert provider.calls_by_role["blind_reader"] == 3
    assert provider.calls_by_role["conversion_critic"] == 1, "the critic judges the survivor only"


@pytest.mark.asyncio
async def test_every_opening_is_written_to_a_different_constraint(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    """Candidates that share an opening move are the same email three times,
    and a cold reader has nothing to choose between them."""
    provider.set_default("strategist", campaign_brief(1))

    pipeline, _ = build(provider, bake_off_only(max_revisions=0))
    await pipeline.run(request_fixture)

    asks = [request.messages[0].content for request in provider.requests_for("email_writer")]
    constraints = [ask for ask in asks if "where it starts" in ask]
    assert len(constraints) == 3
    assert len(set(constraints)) == 3, "three openings must be three different instructions"


@pytest.mark.asyncio
async def test_an_opening_that_will_not_parse_does_not_sink_the_email(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    """One candidate failing is a candidate fewer, not a failed email."""
    provider.set_default("strategist", campaign_brief(1))
    # Three repair attempts per draft, so the first candidate is exhausted
    # before the second one starts.
    provider.push("email_writer", "not an email", "still not", "nope at all")

    pipeline, _ = build(provider, bake_off_only(max_revisions=0))
    result = await pipeline.run(request_fixture)

    assert result.status in {"completed", "degraded"}
    assert len(result.outcomes) == 1


# --------------------------------------------- what the run admits to


@pytest.mark.asyncio
async def test_copy_a_stranger_would_not_click_is_not_reported_as_completed(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    """A run that ends because it is out of rewrites has not succeeded.

    Reporting it as completed is worse than the bad copy: it teaches the user
    that the headline number means nothing, which costs them the one signal
    the system exists to give.
    """
    provider.set_default("strategist", campaign_brief(1))
    provider.set_default("blind_reader", READ_FAIL)

    pipeline, _ = build(provider, refine_only())
    result = await pipeline.run(request_fixture)

    assert result.status == "degraded"
    assert result.report.below_floor
    assert not result.report.healthy
    rendered = result.report.render()
    assert "never reached the 7/10 floor" in rendered
    assert "did not decide these were ready" in rendered


@pytest.mark.asyncio
async def test_a_draft_most_of_the_panel_would_click_ships_without_a_rewrite(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    """The floor has to be reachable, or every run ends out of rewrites.

    Landing used to need every reader on the panel to say they would click,
    and the panel was built to contain one who never would. Nothing could
    satisfy that, so the loop always spent every rewrite it had, always
    reported degraded, and always charged for four attempts at an email that
    two out of three strangers already wanted.
    """
    provider.set_default("strategist", campaign_brief(1))
    provider.push(
        "blind_reader",
        blind_read(pull=8),
        blind_read(pull=8),
        blind_read(pull=3, would_act=False),
    )

    pipeline, _ = build(provider, refine_only(reader_panel=True))
    # One email asked for and one delivered: this test is about the read, and
    # a contract violation would degrade the run for an unrelated reason.
    result = await pipeline.run(
        replace(request_fixture, request="Write me 1 email that sells my app")
    )

    assert provider.calls_by_role["blind_reader"] == 3, "one draft, three readers"
    assert len(result.outcomes[0].versions) == 1, "it landed - there was nothing to rewrite"
    assert result.status == "completed"
    assert not result.report.below_floor


@pytest.mark.asyncio
async def test_a_rewrite_answers_every_reader_on_the_panel(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    """A panel is bought for the variance. Rewriting against the first
    reader's report alone spends three reads and uses one."""
    provider.set_default("strategist", campaign_brief(1))
    provider.push(
        "blind_reader",
        blind_read(pull=3, would_act=False, stopped_at="the first line went nowhere"),
        blind_read(pull=3, would_act=False, biggest_doubt="we already pay for one of these"),
        blind_read(pull=8),
    )

    pipeline, _ = build(provider, refine_only(reader_panel=True))
    await pipeline.run(request_fixture)

    rewrite_prompt = provider.requests_for("email_writer")[1].messages[0].content
    assert "the first line went nowhere" in rewrite_prompt
    assert "we already pay for one of these" in rewrite_prompt


@pytest.mark.asyncio
async def test_a_read_that_never_came_back_is_not_a_passing_score(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    """A malformed reader response used to be recorded as exactly the score
    that ships an email, so a draft nobody had read averaged into the
    campaign's headline number as a pass."""
    provider.set_default("strategist", campaign_brief(1))
    provider.set_default("blind_reader", "the reader replied with prose, not a verdict")

    pipeline, _ = build(provider, refine_only())
    result = await pipeline.run(request_fixture)

    line = result.report.emails[0]
    assert line.read_reported is False
    assert result.report.average_pull == 0.0, "a score nobody gave is not an average"
    assert result.status == "degraded"
    assert "no cold reader reported back" in result.report.render()


# ------------------------------------------------ what the copy can prove


@pytest.mark.asyncio
async def test_the_strategist_is_told_which_angles_the_evidence_cannot_carry(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    """The fixture has a metric and a price and no testimonial - so an
    outcome-led campaign is not available, and saying so before the arc is
    designed is the only point at which that is still cheap to act on."""
    pipeline, _ = build(provider, refine_only())
    await pipeline.run(request_fixture)

    prompt = provider.requests_for("strategist")[0].system_prompt
    assert "Do not plan an email around proof that does not exist" in prompt
    assert "The mechanism, stated plainly enough to be judged" in prompt
    # The checkable specifics it does have are named, so "no proof" does not
    # read as "nothing to say".
    assert "writes a release note in about nine seconds" in prompt


@pytest.mark.asyncio
async def test_proof_that_exists_is_handed_over_to_be_spent(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    artifacts = artifacts_fixture()
    artifacts.evidence.entries.append(
        Evidence(
            id="E3",
            kind=EvidenceKind.TESTIMONIAL,
            claim="Basecamp's release manager stopped writing notes by hand",
            verbatim="We stopped writing them by hand entirely. - Dana, release manager",
            source="https://example.com/customers",
        )
    )
    pipeline, _ = build(provider, refine_only(), artifacts=artifacts)
    await pipeline.run(request_fixture)

    prompt = provider.requests_for("strategist")[0].system_prompt
    assert "Spend these deliberately" in prompt
    assert "Do not plan an email around proof that does not exist" not in prompt


@pytest.mark.asyncio
async def test_the_receipt_names_the_one_thing_that_would_change_the_next_run(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    """A gap the user can close is worth more than a rewrite, and the report
    is where they find that out."""
    pipeline, _ = build(provider, refine_only())
    result = await pipeline.run(request_fixture)

    assert result.report.what_would_help_most
    assert "What would help most next time:" in result.report.render()


def test_a_segment_is_matched_by_description_when_the_name_is_paraphrased():
    """Strategists paraphrase. Being strict here lands on the fallback that
    this matching exists to avoid."""
    audience = two_segments().audience

    assert audience.match(SUPPORT_LEAD) is not None
    assert audience.match("Support Lead Answering The Same Changelog Question All Week").name == (
        SUPPORT_LEAD
    )
    assert audience.match("the support lead").name == SUPPORT_LEAD
    assert audience.match("", "a support lead buried in changelog questions").name == SUPPORT_LEAD
    assert audience.match("someone else entirely") is None
