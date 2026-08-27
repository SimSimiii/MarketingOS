"""What the loop decides, and what it refuses to pay for.

These are the behaviours a measured run showed were missing. In that run three
candidates were written and two were the same email, one absolute score was
compared against another absolute score to decide whether a rewrite had helped,
a critique was bought for a rewrite that never happened, and an email whose
argument was not landing was rewritten twice into the same argument. Each of
those has a test here.
"""

import pytest

from app.knowledge.ledger import Evidence, EvidenceKind, EvidenceLedger
from app.marketing.request import CampaignRequest
from tests.marketing.conftest import (
    READ_FAIL,
    READ_PASS,
    RoleScriptedProvider,
    artifacts_fixture,
    campaign_brief,
    email_draft,
    inbox_verdict,
    subject_options,
    votes_for_the_challenger,
)
from tests.marketing.test_pipeline import bake_off_only, build, refine_only

ALTERNATIVE = "the second month is what you would be signing up to own"


def one_email(request: CampaignRequest) -> CampaignRequest:
    from dataclasses import replace

    return replace(request, request="Write me 1 email that sells my app")


def writer_briefs(provider: RoleScriptedProvider) -> list[str]:
    return [request.system_prompt or "" for request in provider.requests_for("email_writer")]


# ------------------------------------------------- one bet is not a bake-off


@pytest.mark.asyncio
async def test_candidates_argue_different_claims_when_the_brief_names_them(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    """The bake-off used to vary only where a draft opened, on a claim the
    strategist had already fixed - so three drafts were three ways into one
    bet, and the one thing about a campaign that has to be found out was the
    one thing it could not test."""
    provider.set_default(
        "strategist", campaign_brief(1, alternatives=[ALTERNATIVE, "a third claim entirely"])
    )

    pipeline, _ = build(provider, bake_off_only(max_revisions=0))
    await pipeline.run(one_email(request_fixture))

    claims = writer_briefs(provider)
    assert len(claims) == 3
    assert any(ALTERNATIVE in claim for claim in claims)
    assert any("a third claim entirely" in claim for claim in claims)


@pytest.mark.asyncio
async def test_a_writer_is_never_shown_the_claims_it_is_standing_in_for(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    """A draft told about the claims it could have argued hedges between them.
    Each candidate is told about exactly one idea - its own."""
    provider.set_default("strategist", campaign_brief(1, alternatives=[ALTERNATIVE]))

    pipeline, _ = build(provider, refine_only(max_revisions=0))
    await pipeline.run(one_email(request_fixture))

    assert ALTERNATIVE not in writer_briefs(provider)[0]


@pytest.mark.asyncio
async def test_two_candidates_that_came_back_the_same_are_not_read_twice(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    """A bake-off exists to buy alternatives, and two drafts with the same
    subject are one alternative bought twice. Screened before the cold reads,
    because the reads are what the duplicate would have cost."""
    provider.set_default("strategist", campaign_brief(1))
    provider.push(
        "email_writer",
        email_draft(subject="The same line", body=_BODY_ONE),
        email_draft(subject="The same line", body=_BODY_TWO),
        email_draft(subject="A different line", body=_BODY_THREE),
    )

    pipeline, _ = build(provider, bake_off_only(max_revisions=0))
    await pipeline.run(one_email(request_fixture))

    assert provider.calls_by_role["email_writer"] == 3, "all three were still written"
    assert provider.calls_by_role["blind_reader"] == 2, "only two of them were worth reading"


@pytest.mark.asyncio
async def test_a_candidate_a_gate_already_vetoed_is_not_read_cold(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    """The free checks outrank the score, so the reading decides nothing.

    `EmailVersion.measured` puts the gate first: a candidate with a blocking
    issue loses to any clean one whatever a stranger says about it. Reading it
    anyway bought a whole panel per blocked draft - three calls each on a
    preset that writes four candidates - for a number nothing consumes.
    """
    provider.set_default("strategist", campaign_brief(1))
    provider.push(
        "email_writer",
        email_draft(subject="The one that reads clean", body=_BODY_ONE),
        email_draft(subject="Act now, and the spam gate says no", body=_BODY_BLOCKED),
        email_draft(subject="The other one that reads clean", body=_BODY_THREE),
    )

    pipeline, _ = build(provider, bake_off_only(max_revisions=0))
    result = await pipeline.run(one_email(request_fixture))

    assert provider.calls_by_role["email_writer"] == 3, "all three were still written"
    assert provider.calls_by_role["blind_reader"] == 2, "the vetoed one was not worth reading"

    vetoed = next(
        item for item in result.outcomes[0].discarded if item.gates.blocking
    )
    assert vetoed.read.has_verdict is False
    assert not result.outcomes[0].best.gates.blocking


@pytest.mark.asyncio
async def test_candidates_that_all_broke_a_check_are_still_read(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    """The mirror of the rule above, and the reason it is stated as "unless".

    When every candidate is vetoed the gates have ranked nothing, so the cold
    read is the only instrument left that can say which of them to carry into
    the rewrites. Skipping it there would pick the winner by draft order.
    """
    provider.set_default("strategist", campaign_brief(1))
    provider.push(
        "email_writer",
        email_draft(subject="Act now, the first one", body=_BODY_BLOCKED),
        email_draft(subject="Act now, the second one", body=_BODY_BLOCKED_TWO),
        email_draft(subject="Act now, the third one", body=_BODY_BLOCKED_THREE),
    )

    pipeline, _ = build(provider, bake_off_only(max_revisions=0))
    result = await pipeline.run(one_email(request_fixture))

    assert provider.calls_by_role["blind_reader"] == 3
    assert result.outcomes[0].best.gates.blocking


@pytest.mark.asyncio
async def test_the_two_best_candidates_are_read_side_by_side(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    """The scores rank the field and routinely cannot separate the top two -
    three candidates coming back 5, 5 and 4 have said which one to throw away
    and nothing about the other two. That is the comparison worth one more
    reaction, and only that one."""
    provider.set_default("strategist", campaign_brief(1))
    provider.push(
        "email_writer",
        email_draft(subject="The one that scored first", body=_BODY_ONE),
        email_draft(subject="The one the readers preferred", body=_BODY_THREE),
    )
    provider.set_default("blind_reader", READ_FAIL)
    provider.push("preference_judge", *votes_for_the_challenger(2))

    pipeline, _ = build(
        provider,
        bake_off_only(max_revisions=0, draft_candidates=2, tournament=True),
    )
    result = await pipeline.run(one_email(request_fixture))

    assert provider.calls_by_role["preference_judge"] == 2, "one duel, both label orders"
    assert result.emails[0].subject == "The one the readers preferred"


# ------------------------------------------------- better is a comparison


@pytest.mark.asyncio
async def test_a_rewrite_the_reader_preferred_is_kept_even_on_a_level_score(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    """Two saturated scores cannot be compared. Put the drafts side by side and
    the reader can still say which one they would act on, which is the question
    the loop was asking all along."""
    provider.set_default("strategist", campaign_brief(1))
    provider.set_default("blind_reader", READ_FAIL)
    provider.push("preference_judge", *votes_for_the_challenger(2))

    pipeline, _ = build(provider, refine_only(max_revisions=1, tournament=True))
    result = await pipeline.run(one_email(request_fixture))

    outcome = result.outcomes[0]
    assert len(outcome.versions) == 2
    assert outcome.best.attempt == 2, "the readers picked the rewrite"
    assert outcome.stopped_early is False


@pytest.mark.asyncio
async def test_a_rewrite_that_drops_the_proof_does_not_take_the_title(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    """The measured hole in the judge, closed deterministically.

    On the bench, an email with its whole proof paragraph deleted took half the
    votes against the original - nothing invented, no gate tripped, and the
    instrument that decides what ships could not see the one thing the
    architecture exists to put on the page. So here the readers are scripted to
    prefer the rewrite, unanimously, and the rewrite is the same email with the
    figure it was built on taken out. The incumbent stands anyway.

    Deliberately narrow. This is a regression check between two drafts of one
    email, not a standard: a first draft with no proof in it is not blocked,
    and a rewrite that swaps one support for another is not weakened. See
    `Substantiation.weaker_than`.
    """
    provider.set_default("strategist", campaign_brief(1))
    provider.set_default("blind_reader", READ_FAIL)
    provider.push("preference_judge", *votes_for_the_challenger(2))
    provider.push(
        "email_writer",
        email_draft(subject="The draft that argues from the material"),
        email_draft(
            subject="The rewrite that argues from nothing",
            body=(
                "Friday afternoon is where your shipping week goes to die.\n\n"
                "The work was done on Tuesday. What is left is describing it, and describing\n"
                "it is the part nobody scheduled time for.\n\n"
                "Point it at the branch you merged and read whatever comes back to you.\n"
                "Keep the half that is right and rewrite the half that is not.\n\n"
                "Teams say the draft is close enough that arguing with it beats starting from\n"
                "an empty page on the last afternoon of the week."
            ),
        ),
    )

    pipeline, _ = build(provider, refine_only(max_revisions=1, tournament=True))
    result = await pipeline.run(one_email(request_fixture))

    outcome = result.outcomes[0]
    assert len(outcome.versions) == 2, "the rewrite was still written and read"
    assert outcome.versions[1].duel is None, "and was not even put to a vote"
    assert outcome.best.attempt == 1
    assert result.emails[0].subject == "The draft that argues from the material"


@pytest.mark.asyncio
async def test_an_email_that_spends_none_of_its_evidence_says_so_on_the_receipt(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    """Advisory, never blocking - and therefore worth naming out loud.

    A business with no proof is written from mechanism on purpose, so this
    cannot stop a run. What it can do is stop being invisible: the copy
    invented nothing, which is all the gates ever checked, and a stranger
    still has no reason to believe a word of it.
    """
    provider.set_default("strategist", campaign_brief(1))
    provider.set_default(
        "email_writer",
        email_draft(
            subject="Release notes, written before you sit down",
            body=(
                "You shipped it on Tuesday and nobody has heard about it yet.\n\n"
                "The person who has to describe the work is the person who just spent the\n"
                "week doing it, and by now they would rather not.\n\n"
                "Point it at the branch you merged and read whatever comes back to you.\n"
                "Keep the half that is right and rewrite the half that is not.\n\n"
                "Most people keep the first paragraph and change the second one before they\n"
                "send it on to anybody else."
            ),
        ),
    )

    pipeline, _ = build(provider, refine_only(max_revisions=0))
    result = await pipeline.run(one_email(request_fixture))

    line = result.report.emails[0]
    assert line.evidence_assigned == ["E1"]
    assert line.evidence_spent == []
    assert line.argues_from_nothing
    assert result.report.unsubstantiated == [line]
    assert "none of the evidence" in line.render()
    # Advisory: the run still finished and the email still shipped.
    assert result.status in ("completed", "degraded")
    assert not result.outcomes[0].best.gates.blocking


@pytest.mark.asyncio
async def test_a_rewrite_nobody_preferred_leaves_the_earlier_draft_standing(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    provider.set_default("strategist", campaign_brief(1))
    provider.set_default("blind_reader", READ_FAIL)

    pipeline, _ = build(provider, refine_only(max_revisions=1, tournament=True))
    result = await pipeline.run(one_email(request_fixture))

    outcome = result.outcomes[0]
    assert outcome.best.attempt == 1
    assert outcome.stopped_early is True


# ------------------------------------------------- a stalled email pivots


@pytest.mark.asyncio
async def test_an_argument_that_is_not_landing_is_replaced_rather_than_reworded(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    """When the copy stops moving, what is usually not working is the claim -
    and no rewrite is allowed to change the claim. So the loop takes an untried
    one from the brief instead of buying a third phrasing of a bet it has
    already measured twice."""
    provider.set_default("strategist", campaign_brief(1, alternatives=[ALTERNATIVE]))
    provider.set_default("blind_reader", READ_FAIL)

    pipeline, _ = build(provider, refine_only(max_revisions=2))
    result = await pipeline.run(one_email(request_fixture))

    outcome = result.outcomes[0]
    assert outcome.pivoted_to == ALTERNATIVE
    assert ALTERNATIVE in writer_briefs(provider)[-1], "the last draft argued the new claim"
    # Three writer turns: the draft, one rewrite, and then a different bet -
    # not three phrasings of the bet the reader had already turned down twice.
    assert provider.calls_by_role["email_writer"] == 3


@pytest.mark.asyncio
async def test_a_pivot_that_lands_is_the_email_that_ships(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    """The point of pivoting rather than stopping: the run still has attempts
    left, and the claim was the thing that was wrong."""
    provider.set_default("strategist", campaign_brief(1, alternatives=[ALTERNATIVE]))
    provider.push("blind_reader", READ_FAIL, READ_FAIL, READ_PASS)

    pipeline, _ = build(provider, refine_only(max_revisions=2))
    result = await pipeline.run(one_email(request_fixture))

    outcome = result.outcomes[0]
    assert outcome.pivoted_to == ALTERNATIVE
    assert outcome.best.attempt == 3
    assert outcome.best.idea == ALTERNATIVE
    assert outcome.best.read.landed is True


@pytest.mark.asyncio
async def test_a_pivot_is_a_fresh_draft_and_not_a_rewrite(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    """A rewrite is handed the draft it replaces and told to keep what worked -
    the one instruction that would drag the argument that has just failed into
    the one that has not been tried."""
    provider.set_default("strategist", campaign_brief(1, alternatives=[ALTERNATIVE]))
    provider.set_default("blind_reader", READ_FAIL)

    pipeline, _ = build(provider, refine_only(max_revisions=2))
    await pipeline.run(one_email(request_fixture))

    last_task = provider.requests_for("email_writer")[-1].messages[0].content
    assert "--- what you sent ---" not in last_task
    assert "What has already been tried on this email" in last_task


@pytest.mark.asyncio
async def test_only_one_pivot_per_email(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    """A second pivot is a brief that is wrong about who it is writing to, and
    no amount of re-arguing fixes that. It goes on the receipt instead."""
    provider.set_default(
        "strategist", campaign_brief(1, alternatives=[ALTERNATIVE, "a third claim entirely"])
    )
    provider.set_default("blind_reader", READ_FAIL)

    pipeline, _ = build(provider, refine_only(max_revisions=3))
    result = await pipeline.run(one_email(request_fixture))

    assert "a third claim entirely" not in "".join(writer_briefs(provider))
    assert result.outcomes[0].stopped_early is True


@pytest.mark.asyncio
async def test_an_email_with_nowhere_to_pivot_stops_rather_than_rewriting(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    provider.set_default("strategist", campaign_brief(1))
    provider.set_default("blind_reader", READ_FAIL)

    pipeline, _ = build(provider, refine_only(max_revisions=3))
    result = await pipeline.run(one_email(request_fixture))

    assert result.outcomes[0].pivoted_to == ""
    assert result.outcomes[0].stopped_early is True
    assert provider.calls_by_role["email_writer"] == 2


# ------------------------------------------------- the critic is bought late


@pytest.mark.asyncio
async def test_no_critique_is_bought_for_a_rewrite_that_will_not_happen(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    """The measured waste: the loop critiqued first and discovered afterwards
    that the rewrite had stalled, so a deep-tier call, 49 seconds and 13% of
    the run bought edits nothing could consume."""
    provider.set_default("strategist", campaign_brief(1))
    provider.set_default("blind_reader", READ_FAIL)

    pipeline, _ = build(provider, refine_only(max_revisions=3))
    await pipeline.run(one_email(request_fixture))

    # Two attempts, and only the first one had a rewrite in front of it.
    assert provider.calls_by_role["email_writer"] == 2
    assert provider.calls_by_role["conversion_critic"] == 1


@pytest.mark.asyncio
async def test_an_email_always_has_one_judgment_on_the_record(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    """The critique is not only an instruction to the writer: its brief drift
    and unspent evidence are what the user is shown about why an email is the
    way it is. A run configured for no rewrites would otherwise have none."""
    provider.set_default("strategist", campaign_brief(1))
    provider.set_default("blind_reader", READ_FAIL)

    pipeline, _ = build(provider, refine_only(max_revisions=0))
    result = await pipeline.run(one_email(request_fixture))

    assert provider.calls_by_role["conversion_critic"] == 1
    assert result.outcomes[0].best.critique is not None


# ------------------------------------------------- the subject is chosen too


@pytest.mark.asyncio
async def test_the_subject_that_more_people_would_open_is_the_one_delivered(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    provider.set_default("strategist", campaign_brief(1))
    provider.set_default("subject_lines", subject_options(2))
    provider.set_default("inbox_scanner", inbox_verdict(8, 41, 7))

    pipeline, _ = build(provider, refine_only(max_revisions=0, subject_variants=2))
    result = await pipeline.run(one_email(request_fixture))

    assert result.emails[0].subject == "Release notes, option 1"


@pytest.mark.asyncio
async def test_a_better_scanning_subject_that_breaks_a_check_is_not_shipped(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    """The free checks outrank the improvement. A subject can repeat an earlier
    email's word for word, and a swap that breaks a gate is a swap that made
    the deliverable worse."""
    import json

    provider.set_default("strategist", campaign_brief(1))
    provider.set_default(
        "subject_lines",
        json.dumps(
            {
                "options": [
                    {
                        "subject": "Act now before this offer ends",
                        "preview": "the spam gate will refuse this one",
                        "approach": "urgency",
                    }
                ]
            }
        ),
    )
    provider.set_default("inbox_scanner", inbox_verdict(5, 60))

    pipeline, _ = build(provider, refine_only(max_revisions=0, subject_variants=1))
    result = await pipeline.run(one_email(request_fixture))

    assert result.emails[0].subject != "Act now before this offer ends"
    assert not result.outcomes[0].best.gates.blocking


# ------------------------------------------------- nothing to argue from


@pytest.mark.asyncio
async def test_a_run_with_nothing_checkable_asks_before_it_spends(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    """No rewrite has ever added a proof the material did not contain. A
    campaign written from assertions alone gets written, disbelieved, rewritten
    and disbelieved again - all of it discoverable for nothing, before the
    first model call."""
    artifacts = artifacts_fixture()
    artifacts.evidence = EvidenceLedger(
        entries=[
            Evidence(
                id="E1",
                kind=EvidenceKind.FEATURE,
                claim="it has a dashboard",
                verbatim="It has a dashboard.",
            )
        ]
    )

    pipeline, _ = build(provider, artifacts=artifacts)
    result = await pipeline.run(request_fixture)

    assert result.status == "needs_input"
    assert result.report.questions
    assert provider.calls_by_role["strategist"] == 0
    assert provider.calls_by_role["email_writer"] == 0


@pytest.mark.asyncio
async def test_a_business_with_no_testimonials_but_real_specifics_is_not_blocked(
    provider: RoleScriptedProvider, request_fixture: CampaignRequest
):
    """Specific beats persuasive. A price, a limit and a mechanism are enough
    to write from, and stopping there would refuse most of the businesses this
    is for - the fixture has no testimonial in it at all."""
    pipeline, _ = build(provider)
    result = await pipeline.run(request_fixture)

    assert result.status == "completed"


#: Long enough to clear the structural floor, so a draft is rejected by the
#: check a test is about rather than by the word count it was not.
_BODY_ONE = (
    "You wrote the same release note three times last month.\n\n"
    "Every one of them started as a changelog nobody read, and ended as a paragraph\n"
    "you rewrote twice before shipping it to anyone at all.\n\n"
    "Point it at the branch and read what comes back. Change the bits that are wrong\n"
    "and leave the rest of it alone.\n\n"
    "Most people ask whether it sounds like them. It reads your older notes first,\n"
    "so it does, and that is the whole trick."
)
_BODY_TWO = (
    "You wrote the same release note three times last month.\n\n"
    "Each one began life as a changelog nobody opened, then became a paragraph you\n"
    "rewrote twice before it shipped to anybody at all.\n\n"
    "Aim it at a merged branch and read the draft. Edit whatever is wrong and let\n"
    "the rest of it stand.\n\n"
    "People ask first whether it sounds like them. It reads your earlier notes, so\n"
    "it does, and that is most of the trick."
)
_BODY_THREE = (
    "Your changelog has a tone, and it is not the one you would use out loud.\n\n"
    "That happens when writing gets squeezed into whatever minutes are left before\n"
    "a deploy window closes on you for the week.\n\n"
    "Give it the twenty entries you already published and it will write like those\n"
    "did, in the register you actually use.\n\n"
    "Nothing to configure. Paste a branch name, read a paragraph, decide whether to\n"
    "keep what it handed you."
)

#: Drafts that break a blocking gate on purpose - "act now" is spam-filter
#: vocabulary, and `spam_gate` reads the rendered email. Each opens differently
#: from the others so `_distinct` keeps all three: what these tests are about
#: is what happens after the checks run, not the duplicate screen before them.
_BODY_BLOCKED = (
    "Act now, because the deploy window shuts on you again this Friday.\n\n"
    "The note is the part that gets squeezed into whatever minutes are left once\n"
    "the work everybody cares about is already finished and merged.\n\n"
    "Hand it a branch and read the paragraph that comes back to you.\n\n"
    "Keep the half that is right, rewrite the half that is not, and send it."
)
_BODY_BLOCKED_TWO = (
    "Every sprint ends with a paragraph nobody volunteered to write.\n\n"
    "Act now and it is written before the retro starts, from the commits that are\n"
    "already sitting on the branch you merged this morning.\n\n"
    "You read it, you change what is wrong, and then it goes out.\n\n"
    "That is the whole loop, and it takes about as long as reading this did."
)
_BODY_BLOCKED_THREE = (
    "Nobody on your team wants to own the changelog, and it shows.\n\n"
    "It reads like a list because it is one, and the people it was written for\n"
    "gave up on opening it some time around the spring.\n\n"
    "Act now on the twenty entries you already published and it writes like those.\n\n"
    "Paste a branch name. Read what it gives you. Decide whether to keep it."
)
