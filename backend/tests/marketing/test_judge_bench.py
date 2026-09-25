"""The judge bench's own validity, checked for free.

The bench exists to say whether the instruments can be trusted, so a bench that
is quietly wrong is worse than none: it would report a reliability nobody has
and everything downstream would be read as calibrated. Two properties carry the
whole design and both are pinned here.

**A mutant must be plausibly worse, not broken.** The judgment-only mutations
claim that nothing mechanical can catch them. If one of them trips a gate, the
claim is false - the pair is measuring structural damage, not judgment, and the
detection rate it feeds is inflated.

**A mutation that changed nothing must not be scored.** A duel between two
identical emails is a coin toss, and counting the coin as a missed detection
would slander the judge.
"""

import pytest

from app.ai.model_router import ModelRouter, ModelTier
from app.ai.models import ClaudeModel
from app.evaluation.controls import CONTROL_DRAFTS, BenchSource, bench_only_sources
from app.evaluation.golden import GOLDEN_CASES
from app.evaluation.judge_bench import (
    DEFAULT_JUDGE_MODEL,
    BenchReport,
    PairResult,
    _free_gates,
    _subject_only,
    bench_sources,
    run_bench,
    wilson,
)
from app.evaluation.mutations import (
    _PROOF_RE,
    HARD_MUTATION_NAMES,
    HARD_MUTATIONS,
    MUTATIONS,
    Mutation,
    mutation_named,
)
from app.marketing.email_copy import Email, render_email
from app.runtime.model_session import _PROVIDER_ATTEMPTS as PROVIDER_ATTEMPTS
from tests.marketing.conftest import (
    FAIL,
    VOTE_A,
    RoleScriptedProvider,
    inbox_verdict,
    make_session,
    votes_for_the_champion,
)

PERSONA = "a developer who ships weekly"

DEGRADATIONS = [item for item in MUTATIONS if not item.invariant]
JUDGMENT_ONLY = [item for item in DEGRADATIONS if not item.gate_visible]
GATE_VISIBLE = [item for item in DEGRADATIONS if item.gate_visible]


def controls() -> list[Email]:
    return [source.email for source in bench_sources()]


def one_source(name: str, email: Email, *, anchor: bool = False) -> list[BenchSource]:
    return [BenchSource(name=name, email=email, persona=PERSONA, anchor=anchor)]


def plain_email() -> Email:
    """An email with no figure in it - nothing for the vagueness rules to eat."""
    return Email(
        position=1,
        subject="Your notes are still unwritten",
        preview_text="the part nobody schedules",
        greeting="Hi there,",
        body=(
            "You shipped it and nobody has heard about it yet.\n\n"
            "The person who has to describe the work is the person who just "
            "spent the week doing it, and by now they would rather not.\n\n"
            "Point it at the branch you merged and read what comes back."
        ),
        call_to_action="Point it at a branch",
        sign_off="- the team",
    )


# ------------------------------------------------------------ the mutations


def test_the_golden_set_still_offers_the_bench_its_human_controls():
    """The anchors are the only items whose difficulty is independent of the
    thing being measured. If a control stops parsing, the bench silently
    shrinks instead of failing, and this is where that gets noticed."""
    anchors = bench_sources(anchors_only=True)

    assert anchors, "no golden case has a control email the bench can use"
    assert all(source.anchor for source in anchors)


def test_one_control_email_is_benched_once_however_many_cases_carry_it():
    """The confound the widening exists to remove, and it was already here.

    `rich-sequence` and `rich-single` are two requests against one business
    carrying the same control email and the same persona. Keyed by case name
    the set yielded both, so every pair on that email was bought twice and the
    report counted them as two independent items - manufacturing the illusion
    of a sample while charging for it.
    """
    carrying = [case for case in GOLDEN_CASES if case.control_email.strip()]
    anchors = bench_sources(anchors_only=True)

    assert len(carrying) > len(anchors), "the duplicate control this pins is gone from golden.py"
    rendered = [render_email(source.email) for source in anchors]
    assert len(set(rendered)) == len(rendered)


def test_every_control_written_for_the_bench_is_sendable():
    """`bench_only_sources` skips a draft it cannot parse, so a typo would
    shrink the bench rather than fail it - and a smaller bench reports a
    narrower rate with no sign that anything went missing."""
    parsed = bench_only_sources()

    assert len(parsed) == len(CONTROL_DRAFTS), (
        "a control draft is not sendable: "
        f"{sorted({draft.name for draft in CONTROL_DRAFTS} - {s.name for s in parsed})}"
    )
    assert not any(source.anchor for source in parsed)


def test_the_bench_runs_on_more_than_one_item_by_default():
    """The whole point. With one item a miss is unattributable: it is equally
    a blind judge and an email that never carried the thing being removed."""
    assert len(bench_sources()) >= 4


@pytest.mark.parametrize("mutation", DEGRADATIONS, ids=lambda item: item.name)
def test_every_degradation_actually_damages_a_control(mutation: Mutation):
    """A mutation that fires on none of the controls contributes nothing but
    skipped rows, and would go unnoticed because a skip is not a failure."""
    assert any(
        render_email(mutation.apply(email)) != render_email(email) for email in controls()
    ), f"{mutation.name} is a no-op on every control email"


@pytest.mark.parametrize("mutation", JUDGMENT_ONLY, ids=lambda item: item.name)
def test_judgment_only_damage_is_invisible_to_the_free_checks(mutation: Mutation):
    """The claim the detection rate rests on.

    These pairs are supposed to isolate judgment. A mutant that also breaks a
    structural rule can be caught by a regular expression, so a judge scoring
    it proves nothing about whether it can read.
    """
    for email in controls():
        issues = _free_gates(mutation.apply(email)).issues
        assert not issues, (
            f"{mutation.name} is classified judgment-only but trips: "
            f"{[issue.detail for issue in issues]}"
        )


@pytest.mark.parametrize("mutation", GATE_VISIBLE, ids=lambda item: item.name)
def test_gate_visible_damage_is_caught_by_the_free_checks(mutation: Mutation):
    """The complement, and a live test of the gates themselves: these run on
    every draft in production, and this is the only place they are pointed at
    copy built specifically to break them."""
    for email in controls():
        assert _free_gates(mutation.apply(email)).issues, (
            f"{mutation.name} is classified gate-visible but no free check fired"
        )


def test_the_invariant_pair_leaves_the_email_alone():
    """The control arm has to be a genuine null. An "invariant" that changed
    the argument would make the noise floor unreadable."""
    identity = mutation_named("identity")
    assert identity is not None
    for email in controls():
        assert render_email(identity.apply(email)) == render_email(email)


def test_a_neutral_change_moves_nothing_but_the_greeting():
    neutral = mutation_named("neutral_greeting")
    assert neutral is not None
    for email in controls():
        mutated = neutral.apply(email)
        assert mutated.body == email.body
        assert mutated.subject == email.subject


# ----------------------------------------------------------------- the bench


@pytest.mark.asyncio
async def test_a_mutation_that_changes_nothing_is_skipped_rather_than_scored(
    provider: RoleScriptedProvider,
):
    """The guard that keeps the detection rate honest. Without it every email
    with no number in it would hand `specifics_to_adjectives` a free miss."""
    vagueness = mutation_named("specifics_to_adjectives")
    assert vagueness is not None

    report = await run_bench(
        judge_session=make_session(provider),
        sources=one_source("plain", plain_email()),
        mutations=(vagueness,),
        votes=2,
    )

    assert report.pairs[0].skipped
    assert report.pairs[0].decided is False
    # And nothing was bought to establish it.
    assert not provider.requests_for("preference_judge")


@pytest.mark.asyncio
async def test_a_judge_that_prefers_the_original_scores_a_catch(
    provider: RoleScriptedProvider,
):
    strip = mutation_named("strip_the_proof")
    assert strip is not None
    provider.push("preference_judge", *votes_for_the_champion(4))

    report = await run_bench(
        judge_session=make_session(provider),
        sources=one_source("rich", controls()[0], anchor=True),
        mutations=(strip,),
        votes=4,
    )

    pair = report.pairs[0]
    assert pair.caught is True
    assert (pair.original_votes, pair.mutant_votes) == (4, 0)
    assert report.detection_rate == 1.0


@pytest.mark.asyncio
async def test_a_tie_is_a_miss(provider: RoleScriptedProvider):
    """A judge that cannot separate the pair has not detected the damage.

    Scored strictly because the loop's own tie rule keeps the incumbent - so a
    tie here is the instrument saying "these are the same email", about a pair
    that is not.
    """
    strip = mutation_named("strip_the_proof")
    assert strip is not None
    # One letter, every vote. The ballot alternates labels, so this is an even
    # split between the two emails - see conftest.
    provider.set_default("preference_judge", VOTE_A)

    report = await run_bench(
        judge_session=make_session(provider),
        sources=one_source("rich", controls()[0], anchor=True),
        mutations=(strip,),
        votes=4,
    )

    pair = report.pairs[0]
    assert pair.original_votes == pair.mutant_votes
    assert pair.caught is False
    assert report.detection_rate == 0.0


@pytest.mark.asyncio
async def test_an_undamaged_pair_reports_the_noise_floor(provider: RoleScriptedProvider):
    """The line that discounts everything else. A judge sweeping a pair of
    identical emails is answering from the label, not the copy."""
    identity = mutation_named("identity")
    assert identity is not None
    provider.set_default("preference_judge", VOTE_A)

    report = await run_bench(
        judge_session=make_session(provider),
        sources=one_source("rich", controls()[0], anchor=True),
        mutations=(identity,),
        votes=4,
    )

    assert report.invariants, "an identical pair must still be judged, not skipped"
    assert report.noise == 0.0


@pytest.mark.asyncio
async def test_a_provider_failure_costs_one_pair_and_not_the_run(
    provider: RoleScriptedProvider,
):
    """A bench is a hundred-odd billed calls. One dropped connection two thirds
    of the way through must not throw away everything bought before it - and
    the pair it killed must not be recorded as a judge that missed.

    The provider has to refuse every attempt, not one: `ModelSession` resends
    a call that failed in transport, so a single dropped connection is a blip
    the bench never sees. What is being tested here is the floor underneath
    that - a provider that has genuinely stopped answering."""
    strip, hedge = mutation_named("strip_the_proof"), mutation_named("hedge_the_claims")
    assert strip is not None and hedge is not None
    # Two votes are cast concurrently and each may be resent, so the queue has
    # to hold every attempt both of them will make - a shorter run of failures
    # is a blip the session absorbs, which is the behaviour the *other* tests
    # here are about.
    provider.push("preference_judge", *([FAIL] * (PROVIDER_ATTEMPTS * 2)))
    provider.set_default("preference_judge", VOTE_A)

    report = await run_bench(
        judge_session=make_session(provider),
        sources=one_source("rich", controls()[0], anchor=True),
        mutations=(strip, hedge),
        votes=2,
    )

    assert len(report.pairs) == 2
    assert report.pairs[0].skipped.startswith("the provider failed")
    assert "never came back" in report.pairs[0].skipped
    assert report.pairs[0].decided is False
    assert report.pairs[1].decided is True


# --------------------------------------------------------------- the routing


def test_the_bench_asks_for_a_model_the_cli_would_recognise():
    """The bug this pins, which cost a real run.

    `ModelRouter` overrides are model names and are handed to the CLI verbatim;
    tier names are a different vocabulary. An override of "balanced" reaches
    Claude Code as a model id, it rejects it, and every call fails - after the
    bench has already printed that it is spending money.
    """
    router = ModelRouter({"*": DEFAULT_JUDGE_MODEL} if DEFAULT_JUDGE_MODEL else None)

    resolved = router.resolve("preference_judge", ModelTier.BALANCED)

    assert resolved in {model.value for model in ClaudeModel}


def test_the_bench_judges_with_the_model_the_craft_loop_uses():
    """Benching a model the system never runs would measure a different
    instrument from the one that decides what ships."""
    bench = ModelRouter({"*": DEFAULT_JUDGE_MODEL} if DEFAULT_JUDGE_MODEL else None)
    loop = ModelRouter()

    for role, tier in (("preference_judge", ModelTier.BALANCED), ("blind_reader", ModelTier.BALANCED)):
        assert bench.resolve(role, tier) == loop.resolve(role, tier)


# --------------------------------------------------------------- the metrics


def _pair(
    mutation: str,
    original: int,
    mutant: int,
    source: str = "fixture",
    *,
    anchor: bool = False,
) -> PairResult:
    found = mutation_named(mutation)
    assert found is not None
    return PairResult(
        source=source,
        mutation=found,
        anchor=anchor,
        original_votes=original,
        mutant_votes=mutant,
    )


def test_the_headline_rate_ignores_damage_a_gate_would_have_caught():
    """Mixing the two would let three structural mutants any regular expression
    catches carry a judge that cannot read at all."""
    report = BenchReport(
        pairs=[
            _pair("strip_the_proof", 4, 0),
            _pair("hedge_the_claims", 0, 4),
            _pair("wall_of_text", 4, 0),
            _pair("shout_and_exclaim", 4, 0),
        ]
    )

    assert report.detection_rate == 0.5
    assert report.gate_detection_rate == 1.0


def test_a_pair_nobody_could_judge_is_left_out_of_the_rate():
    """An undecided duel is not a miss, for the same reason an unreported read
    is not a bad score - see BlindRead.reported."""
    report = BenchReport(pairs=[_pair("strip_the_proof", 4, 0), _pair("hedge_the_claims", 0, 0)])

    assert len(report.judgment_only) == 1
    assert report.detection_rate == 1.0


# ----------------------------------------------- the subject decision's judge


@pytest.mark.asyncio
async def test_damage_above_the_body_goes_to_the_inbox_and_not_to_a_duel(
    provider: RoleScriptedProvider,
):
    """A duel shows a reader two whole emails and asks which they would act on.
    Both are open by then, so a pair identical below the subject can only come
    back even however bad one line is - which is what the first bench round
    recorded as a missed detection. The system already owns the right
    instrument for that decision, and this is it.
    """
    clickbait = mutation_named("clickbait_subject")
    assert clickbait is not None
    # The original is listed first in one pass and second in the other, so the
    # two answers here are (original 60, mutant 20) and (mutant 20, original 60).
    provider.push("inbox_scanner", inbox_verdict(60, 20), inbox_verdict(20, 60))

    report = await run_bench(
        judge_session=make_session(provider),
        sources=one_source("rich", controls()[0], anchor=True),
        mutations=(clickbait,),
        votes=4,
    )

    pair = report.pairs[0]
    assert not provider.requests_for("preference_judge"), "no ballot is cast on this pair"
    assert provider.calls_by_role["inbox_scanner"] == 2, "one pass per listing order"
    assert pair.by_inbox and pair.caught
    assert (pair.original_opens, pair.mutant_opens) == (60, 20)
    assert report.by_inbox == [pair]
    assert report.judgment_only == [], "it does not inflate the rate it never measured"
    assert report.inbox_detection_rate == 1.0


@pytest.mark.asyncio
async def test_two_lines_the_scanner_cannot_separate_are_a_miss(
    provider: RoleScriptedProvider,
):
    """The same rule the duel is held to: an instrument that ranks the pair
    level has declined to detect the damage, not failed to see it."""
    clickbait = mutation_named("clickbait_subject")
    assert clickbait is not None
    provider.set_default("inbox_scanner", inbox_verdict(40, 40))

    report = await run_bench(
        judge_session=make_session(provider),
        sources=one_source("rich", controls()[0], anchor=True),
        mutations=(clickbait,),
        votes=4,
    )

    assert report.pairs[0].caught is False
    assert report.inbox_detection_rate == 0.0


@pytest.mark.asyncio
async def test_the_listing_order_is_cancelled_rather_than_trusted(
    provider: RoleScriptedProvider,
):
    """A list is read top down. A scanner that simply favours the first line
    scores both passes the same way, and the two orders cancel to a tie - the
    same property the duel buys by alternating its labels.
    """
    clickbait = mutation_named("clickbait_subject")
    assert clickbait is not None
    provider.set_default("inbox_scanner", inbox_verdict(70, 10))

    report = await run_bench(
        judge_session=make_session(provider),
        sources=one_source("rich", controls()[0], anchor=True),
        mutations=(clickbait,),
        votes=4,
    )

    pair = report.pairs[0]
    assert pair.original_opens == pair.mutant_opens == 40
    assert pair.caught is False


def test_only_damage_that_leaves_the_body_alone_is_ranked_rather_than_duelled():
    """The routing rule itself, over every mutation the bench carries. It is
    derived from what a mutation did to this email rather than declared on the
    mutation, so it cannot drift out of step with the mutation it describes.
    """
    original = controls()[0]
    routed = {
        mutation.name
        for mutation in MUTATIONS
        if not mutation.invariant and _subject_only(original, mutation.apply(original))
    }

    assert routed == {"clickbait_subject"}


# ------------------------------------------- telling a blind judge from an easy email


def test_a_mutation_missed_everywhere_and_one_missed_on_one_item_are_different_rows():
    """The measurement the single-item bench could not make.

    Both mutations below score badly pooled. One is missed on every item,
    which is a blind spot in the judge and belongs in the duel prompt or in
    code. The other is missed on exactly one, which is an item that is not
    carrying what the mutation removes and belongs in `controls.py`. With one
    control email these are the same 2-2 and nothing can separate them.
    """
    report = BenchReport(
        pairs=[
            _pair("strip_the_proof", 2, 2, "one"),
            _pair("strip_the_proof", 2, 2, "two"),
            _pair("strip_the_proof", 2, 2, "three"),
            _pair("bury_the_ask", 2, 2, "one"),
            _pair("bury_the_ask", 4, 0, "two"),
            _pair("bury_the_ask", 4, 0, "three"),
        ]
    )

    blind, item = sorted(report.by_mutation(), key=lambda row: row.rate)
    assert blind.mutation.name == "strip_the_proof"
    assert blind.missed_on == ("one", "two", "three")
    assert item.mutation.name == "bury_the_ask"
    assert item.missed_on == ("one",)


def test_an_item_nothing_separated_shows_up_as_a_ballot_share_not_a_rate():
    """caught/judged cannot tell 4-0 from 3-1, and the difference is the whole
    evidence. An item sitting at half its ballots was separated by nothing."""
    report = BenchReport(
        pairs=[
            _pair("strip_the_proof", 2, 2, "opaque"),
            _pair("bury_the_ask", 2, 2, "opaque"),
            _pair("strip_the_proof", 4, 0, "clear"),
            _pair("bury_the_ask", 3, 1, "clear"),
        ]
    )

    opaque, clear = report.items()
    assert (opaque.rate, clear.rate) == (0.0, 1.0)
    assert opaque.ballot_share == 0.5
    assert clear.ballot_share == 0.875


def test_the_two_provenances_are_reported_apart_and_never_pooled_away():
    """A control written for the bench may be easier to defend than one a
    person wrote. If the two rates diverge the fixtures are the suspect, and
    a single pooled percentage is exactly what would hide it."""
    report = BenchReport(
        pairs=[
            _pair("strip_the_proof", 4, 0, "human", anchor=True),
            _pair("bury_the_ask", 4, 0, "human", anchor=True),
            _pair("strip_the_proof", 2, 2, "fixture"),
            _pair("bury_the_ask", 2, 2, "fixture"),
        ]
    )

    assert report.anchor_detection_rate == 1.0
    assert report.bench_detection_rate == 0.0
    assert report.detection_rate == 0.5


def test_the_matrix_and_its_legend_appear_only_once_there_is_something_to_compare():
    """One column is not a matrix, and printing one would suggest the bench
    had made a comparison it cannot make."""
    single = BenchReport(pairs=[_pair("strip_the_proof", 4, 0, "only")])
    several = BenchReport(
        pairs=[_pair("strip_the_proof", 4, 0, "one"), _pair("strip_the_proof", 2, 2, "two")]
    )

    assert "MATRIX" not in single.render()
    assert "MATRIX" in several.render()
    assert "PER MUTATION" in several.render()


# ------------------------------------------------------------------- the interval


def test_four_votes_do_not_settle_a_rate():
    """The honesty device. A clean sweep of a four-vote ballot is consistent
    with a judge that is right half the time, and the old report printed it
    as 100%."""
    low, high = wilson(4, 4)

    assert low < 0.6 and high == 1.0


def test_the_interval_narrows_as_items_are_added():
    """What the widening actually buys, stated as a property rather than a
    hope: the same rate over more pairs is a smaller claim."""
    narrow_low, narrow_high = wilson(4, 6)
    wide_low, wide_high = wilson(32, 48)

    assert (wide_high - wide_low) < (narrow_high - narrow_low)


def test_an_empty_bench_claims_nothing():
    assert wilson(0, 0) == (0.0, 1.0)


# --------------------------------------------------------------- the subtle tier


def test_the_hard_tier_is_entirely_judgment_only():
    """What `--hard` rests on.

    The tier exists because the original six are passed 32/33, which leaves no
    room to measure anything. If one of these were catchable by a gate it would
    be benching the gate instead, and the flag would quietly restore the
    ceiling it was added to escape.
    """
    assert HARD_MUTATIONS, "the hard tier is empty"
    assert {item.name for item in HARD_MUTATIONS} == set(HARD_MUTATION_NAMES)
    for mutation in HARD_MUTATIONS:
        assert not mutation.gate_visible, f"{mutation.name} is caught by a free check"
        assert not mutation.invariant, f"{mutation.name} is in the control arm"


def test_the_hollowed_testimonial_still_looks_exactly_like_proof():
    """The whole mechanism of `generic_proof`.

    `strip_the_proof` deletes a name and a passage, which is a string
    comparison and is already answered in code. This one keeps the name, the
    quotation marks and the attribution clause, and removes only what the
    person said. If any of that shape went missing, the pair would be scoring
    the missing shape rather than the missing meaning.
    """
    mutation = mutation_named("generic_proof")
    assert mutation is not None
    for source in bench_sources():
        original, mutant = source.email, mutation.apply(source.email)
        if render_email(mutant) == render_email(original):
            continue  # no quoted span to hollow - the bench skips this pair
        assert mutant.body.count('"') == original.body.count('"')
        # Asserted against the bench's own definition of a proof block rather
        # than a list of reporting verbs: "told me", "wrote to us" and "said"
        # are all attributions, and a test that knew about only some of them
        # would fail on a control for being written differently.
        assert _PROOF_RE.search(mutant.body), "the attribution shape did not survive"
        assert "a real difference" in mutant.body


def test_moving_the_proof_past_the_ask_changes_no_words():
    """The pair isolates position. If a word moved, it would also be isolating
    whatever that word was doing."""
    mutation = mutation_named("proof_after_the_ask")
    assert mutation is not None
    for source in bench_sources():
        mutant = mutation.apply(source.email)
        assert sorted(mutant.body.split()) == sorted(source.email.body.split())


def test_a_second_ask_adds_and_removes_nothing():
    """Every original sentence survives, so the pair isolates the competition
    between two asks rather than the loss of anything."""
    mutation = mutation_named("second_ask")
    assert mutation is not None
    for source in bench_sources():
        mutant = mutation.apply(source.email)
        for block in source.email.body.split("\n\n"):
            assert block.strip() in mutant.body
        assert mutant.call_to_action == source.email.call_to_action


def test_trading_the_mechanism_for_a_benefit_keeps_the_proof_and_the_ask():
    """It removes the reason and nothing else. A mutant that also lost its
    testimonial would be a second `strip_the_proof` with extra steps."""
    mutation = mutation_named("mechanism_to_benefit")
    assert mutation is not None
    for source in bench_sources():
        original, mutant = source.email, mutation.apply(source.email)
        if render_email(mutant) == render_email(original):
            continue
        blocks = [b.strip() for b in original.body.split("\n\n") if b.strip()]
        assert blocks[-1] in mutant.body, "the ask went missing"
        assert mutant.body.count('"') == original.body.count('"'), "the proof went missing"
