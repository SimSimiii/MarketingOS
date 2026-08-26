"""The deterministic half of the question the judge bench asks.

The bench pairs a hand-written control email against a copy with one principle
deliberately broken and asks a model to choose. Its first real round found that
the judge **could not see that the entire proof paragraph had been deleted**:
2-2, an even split, on the one kind of damage the whole architecture exists to
prevent. Every other number in the system is read off that instrument.

Two of those mutations remove evidence rather than rearrange it, and "is the
evidence still on the page" has a correct answer. These tests pin that answer.
They cost no model call, they run in the free suite, and they are what stops
the same regression arriving twice.

The negative cases matter as much as the positive ones. A measure that fired on
`hedge_the_claims` or `bury_the_ask` would be claiming to detect damage it
cannot see, and would then be trusted to veto a rewrite on a judgment it never
made. Those pairs stay the judges' problem, and this file says so out loud.
"""

import pytest

from app.evaluation.judge_bench import bench_sources
from app.evaluation.mutations import Mutation, mutation_named
from app.knowledge.ledger import Evidence, EvidenceKind
from app.marketing.email_copy import Email
from app.marketing.substantiation import assess, names_in

#: The Notewright material as a compile of the golden site would leave it: the
#: mechanism figure, the price, and the one thing a third party said. Written
#: out here rather than compiled because compiling costs a model call, and the
#: entries a compile produces from this site are not in doubt - the site states
#: all three verbatim (see app.evaluation.golden).
LEDGER = [
    Evidence(
        id="E1",
        kind=EvidenceKind.METRIC,
        claim="drafts a release note in about nine seconds",
        verbatim="Point it at a branch and it drafts the note in about nine seconds.",
    ),
    Evidence(
        id="E2",
        kind=EvidenceKind.PRICE,
        claim="Team is $29 per month per workspace",
        verbatim=(
            "Team is $29 per month per workspace. Every account starts with 1,500 free "
            "credits and no card."
        ),
    ),
    Evidence(
        id="E3",
        kind=EvidenceKind.TESTIMONIAL,
        claim="an engineering lead at Halcyon says the team stopped arguing about the notes",
        verbatim=(
            '"We stopped arguing about who writes the notes. It just does it, and we edit." '
            "- Priya, engineering lead at Halcyon"
        ),
    ),
]


def named(name: str) -> Mutation:
    mutation = mutation_named(name)
    assert mutation is not None, name
    return mutation


def evidence_bearing_controls() -> list[Email]:
    """The bench's control emails that argue from the material at all.

    The onboarding control deliberately does not - it writes to somebody who
    has already signed up, from their own situation - so there is nothing in
    it for a mutation to remove and nothing here to assert.
    """
    return [
        email
        for _, email, _ in bench_sources()
        if assess(email, LEDGER, LEDGER).attributions or assess(email, LEDGER, LEDGER).carried
    ]


def test_the_controls_actually_carry_their_evidence():
    """The premise everything below rests on. A control that cited nothing
    would make every "detected" result here vacuous."""
    controls = evidence_bearing_controls()
    assert controls, "the bench has no control email that argues from the material"
    for email in controls:
        before = assess(email, LEDGER, LEDGER)
        assert before.carried, "the control spends none of the ledger"
        assert before.attributions, "and cites nobody"


@pytest.mark.parametrize("name", ["strip_the_proof", "specifics_to_adjectives"])
def test_damage_that_removes_evidence_is_visible_without_a_model(name: str):
    """The measured miss, closed.

    `strip_the_proof` deletes the paragraph carrying the testimonial and puts
    nothing back: nothing is invented, no gate fires, the ledger is untouched,
    and a preference judge split its votes evenly on it. What changed is that
    the copy stopped naming anybody. That is a string comparison.
    """
    mutation = named(name)
    for email in evidence_bearing_controls():
        before = assess(email, LEDGER, LEDGER)
        after = assess(mutation.apply(email), LEDGER, LEDGER)
        assert after.weaker_than(before), (
            f"{name} left the substantiation of "
            f'"{email.subject}" unchanged: {before.describe()} -> {after.describe()}'
        )


@pytest.mark.parametrize("name", ["identity", "neutral_greeting"])
def test_the_control_arm_moves_nothing(name: str):
    """The bench's own control arm, applied to this measure.

    An instrument that reports damage on an email compared with itself is not
    reading the copy, and every detection it scores elsewhere is worth
    nothing.
    """
    mutation = named(name)
    for email in evidence_bearing_controls():
        before = assess(email, LEDGER, LEDGER)
        after = assess(mutation.apply(email), LEDGER, LEDGER)
        assert not after.weaker_than(before)
        assert not before.weaker_than(after)


@pytest.mark.parametrize(
    "name", ["hedge_the_claims", "bury_the_ask", "open_on_the_company", "clickbait_subject"]
)
def test_damage_that_only_a_reader_can_see_is_not_claimed(name: str):
    """What this measure is deliberately blind to.

    Every one of these leaves the evidence exactly where it was and makes the
    email worse anyway - a hedged claim, an ask nobody reaches, an opening
    about the sender. No string comparison can see any of it, and a measure
    that pretended to would be handed a veto over rewrites on a judgment it
    never made. These stay the judges' job, and the judge bench is where they
    are scored.
    """
    mutation = named(name)
    for email in evidence_bearing_controls():
        before = assess(email, LEDGER, LEDGER)
        after = assess(mutation.apply(email), LEDGER, LEDGER)
        assert not after.weaker_than(before), (
            f"{name} is being scored as evidence damage - it is not, and treating it as "
            "such would let this measure overrule a reader on a question it cannot answer"
        )


# ------------------------------------------------------------- the mechanics


def test_a_name_is_only_a_name_when_grammar_did_not_capitalise_it():
    """Without this, every sentence-initial "The" reads as a company the copy
    could be checked against, and a testimonial counts as cited by any email
    with two sentences in it."""
    assert names_in("The team shipped it. We told Halcyon on Tuesday.") == {"halcyon"}


def test_a_possessive_is_the_same_name():
    """And it is dropped as a suffix, never with `rstrip` - a character-set
    strip turns "Ross" into "Ro" and silently stops matching the customer the
    testimonial names."""
    assert names_in("It was Halcyon's call. We asked Ross and Ross agreed.") == {
        "halcyon",
        "ross",
    }


def test_an_acronym_counts_wherever_it_falls():
    """"SOC 2" at the start of a sentence is still SOC 2 - it is capitalised
    because it is an acronym, not because a full stop preceded it."""
    assert "soc" in names_in("SOC 2 is audited every year.")


def test_an_email_that_spends_nothing_is_told_which_fact_it_left_out():
    """The gate's output is handed straight to the writer, so it has to name
    the entry and quote the claim - "use your evidence" is not actionable."""
    email = Email(
        position=1,
        subject="Release notes, written before you sit down",
        preview_text="what changes on Monday",
        greeting="Hi there,",
        body=(
            "You wrote the same release note three times last month.\n\n"
            "Every one of them started as a changelog nobody read, and ended as a "
            "paragraph you rewrote twice before shipping it.\n\n"
            "Point it at the branch you merged and read what comes back."
        ),
        call_to_action="Point it at a branch",
        sign_off="- the team",
    )
    substantiation = assess(email, [LEDGER[0]], LEDGER)

    assert substantiation.spends_nothing
    assert substantiation.unspent[0].id == "E1"


def test_trading_one_support_for_another_is_not_a_regression():
    """The rule that keeps this from becoming a rule against editing. A
    rewrite that drops the price and names a customer instead has not weakened
    the email, and a measure that said so would freeze the first draft."""
    email = Email(
        position=1,
        subject="Nine seconds",
        preview_text="the part nobody schedules",
        greeting="Hi there,",
        body=(
            "You shipped it on Tuesday and nobody has heard about it yet.\n\n"
            "Point it at the branch and it drafts the note in about nine seconds, in the "
            "tone of the notes you already publish.\n\n"
            "Read what comes back and decide whether to keep it."
        ),
        call_to_action="Point it at a branch",
        sign_off="- the team",
    )
    traded = email.model_copy(
        update={
            "body": email.body.replace(
                "in about nine seconds",
                "while you read this - the way Priya's team at Halcyon now does it",
            )
        }
    )
    before = assess(email, LEDGER, LEDGER)
    after = assess(traded, LEDGER, LEDGER)

    assert before.carried and not before.attributions
    assert after.attributions, "the rewrite cites somebody the original did not"
    assert not after.weaker_than(before)
