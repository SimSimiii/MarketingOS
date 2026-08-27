"""The differentiation check.

The first test is the one this whole module exists for: it is the exact email
from the run that scored 4/10, which passed every other check in the system.
"""

from app.knowledge.artifacts import OfferSheet
from app.knowledge.corpus import SourceCorpus
from app.knowledge.ledger import Evidence, EvidenceIndex, EvidenceKind, EvidenceLedger
from app.market.claims import Claim, ClaimAxis, ClaimSet
from app.market.positioning import build
from app.market.rivals import RivalProfile
from app.market.sameness import check
from app.marketing.email_copy import Email
from app.marketing.gates import GateSeverity, run_all, sameness_gate

# The draft as it shipped. Every word of it was licensed by the evidence
# ledger and every existing gate passed it first time.
SHIPPED = Email(
    position=1,
    subject="Your competitor isn't waiting on you",
    preview_text="Three months of building is three months of losing ground.",
    greeting="Hi there,",
    body=(
        "Build it yourself and you're three months out, DevOps included. Hire for it and "
        "you're still searching six months from now. Neither one ships this quarter.\n\n"
        "That's three months your competitor doesn't have to spend catching up - because "
        "you're spending it deciding.\n\n"
        "orqAgent skips the build. From sign-up to your first API call takes under 5 "
        "minutes, with 25 models across 9 providers already wired in.\n\n"
        "Start with 1,500 free credits, no card required. Make your first call today."
    ),
    call_to_action="Start for free",
    sign_off="- the orqAgent team",
)


def test_the_email_that_scored_four_is_blocked() -> None:
    report = check(
        subject=SHIPPED.subject, preview=SHIPPED.preview_text, body=SHIPPED.body
    )

    assert not report.passed
    finding = report.blocking[0]
    assert finding.where == "subject"
    assert finding.quote == "Your competitor isn't waiting on you"
    assert "competitor" in finding.frame
    # The point of the check is the replacement, not the verdict.
    assert "own week" in finding.instead


def test_it_reaches_the_writer_through_the_normal_gate_run() -> None:
    """A finding nobody acts on is not a check. It has to arrive in the same
    report as every other blocking issue, so the writer's correction turn
    sees it."""
    report, _ = run_all(
        SHIPPED,
        evidence=EvidenceIndex(EvidenceLedger(), SourceCorpus().text),
        offer=OfferSheet(),
    )
    sameness = [issue for issue in report.blocking if issue.gate == "sameness"]
    assert len(sameness) == 1
    assert "subject" in sameness[0].detail


def test_ordinary_specific_copy_passes() -> None:
    """The list has to stay quiet on copy that is doing its job, or everyone
    learns to ignore it - the same reason the spam list is short."""
    report = check(
        subject="Nine seconds per release note",
        preview="what your changelog script cannot write for you",
        body=(
            "The work shipped Tuesday. The note about it is what is keeping you here on "
            "Friday.\n\n"
            "Your script assembles the commits. It cannot say why any of them matter, "
            "which is the part support hears about later.\n\n"
            "Point it at the branch you merged and read what comes back."
        ),
    )
    assert report.passed
    assert not report.findings


def test_a_competitor_mentioned_as_a_fact_is_not_the_threat_frame() -> None:
    """The pattern is about the *frame*, not about the word. Copy that names
    what competitors do factually is not the same move as telling a stranger
    theirs is beating them."""
    report = check(
        subject="Twenty-five models, one endpoint",
        preview="what nine providers cost you to wire up yourself",
        body=(
            "Most competitors in this category support one provider. We support nine, "
            "behind one endpoint.\n\n"
            "Point it at a model you already use and read what comes back."
        ),
    )
    assert report.passed


def test_the_swap_test_flags_a_paragraph_made_of_category_words() -> None:
    """A paragraph whose every distinctive word is one competitors also spend
    could have been sent by any of them."""
    rivals = [
        RivalProfile(
            name=name,
            url=f"https://{name}.com",
            verified=True,
            claims=ClaimSet(
                claims=[
                    Claim(
                        text="enterprise-grade orchestration for agents",
                        axis=ClaimAxis.QUALITY,
                    ),
                    Claim(
                        text=(
                            "observability, evaluation, monitoring, tracing, prompt "
                            "versioning and deployment pipelines"
                        ),
                        axis=ClaimAxis.QUALITY,
                    ),
                ]
            ),
        )
        for name in ("alpha", "beta", "gamma")
    ]
    positioning = build(ClaimSet(), rivals)
    assert positioning.crowd_words

    report = check(
        subject="Orchestration for agents",
        preview="observability and evaluation",
        body=(
            "Enterprise-grade orchestration for agents, with observability, evaluation, "
            "monitoring, tracing, prompt versioning and deployment pipelines.\n\n"
            "Point it at a branch and read what comes back."
        ),
        positioning=positioning,
    )
    assert report.advisory, "a paragraph of pure category vocabulary should be flagged"
    assert report.passed, "the swap test must never block - its corpus is too thin"
    assert report.distinctiveness < 1.0
    assert not report.blind


def test_our_own_open_ground_is_not_counted_against_us() -> None:
    """A company whose open ground is model coverage should say "models". A
    check that punished the word would push copy off the axis it wins on."""
    ours = ClaimSet(
        claims=[
            Claim(
                text="25 models across 9 providers",
                verbatim="25 models across 9 providers",
                axis=ClaimAxis.BREADTH,
                specific=True,
            )
        ]
    )
    rivals = [
        RivalProfile(
            name=name,
            verified=True,
            claims=ClaimSet(
                claims=[Claim(text="broad model coverage", axis=ClaimAxis.BREADTH)]
            ),
        )
        for name in ("alpha", "beta")
    ]
    positioning = build(ours, rivals)

    report = check(
        subject="Twenty-five models",
        preview="across nine providers",
        body=(
            "Twenty-five models across nine providers, behind one endpoint you already "
            "know how to call.\n\n"
            "Point it at one and read what comes back."
        ),
        positioning=positioning,
    )
    assert report.passed
    assert not report.advisory


def test_the_gate_degrades_to_the_closed_list_without_a_scan() -> None:
    """No competitors profiled must not mean "everything passes" - the frames
    are checkable on their own."""
    report = sameness_gate(SHIPPED, positioning=None)
    assert any(issue.severity is GateSeverity.BLOCKING for issue in report.issues)


def test_short_lines_are_left_alone() -> None:
    """Rhythm depends on short lines existing, and a ratio over four words
    means nothing."""
    report = check(
        subject="Three months, spent either way",
        preview="the build-versus-buy arithmetic nobody does",
        body="Three months either way.\n\nPoint it at one model and read what comes back.",
    )
    assert report.passed


def test_it_does_not_disturb_the_evidence_gate() -> None:
    """Regression guard for the interaction the new gate runs inside.

    The sameness check reads the same draft as the evidence gate and must
    neither license nor block a figure - the two answer different questions
    and a change to one that moved the other would be invisible in every
    other test.
    """
    ledger = EvidenceLedger(
        entries=[
            Evidence(
                id="E1",
                kind=EvidenceKind.METRIC,
                claim="25 models across 9 providers",
                verbatim="25 models across 9 providers, 5 minutes to your first call, "
                "1,500 free credits",
            )
        ]
    )
    report, _ = run_all(
        SHIPPED,
        evidence=EvidenceIndex(ledger, SourceCorpus().text),
        offer=OfferSheet(),
    )
    assert not [issue for issue in report.blocking if issue.gate == "evidence"], (
        "every figure in the draft is licensed by the ledger"
    )
    assert [issue for issue in report.blocking if issue.gate == "sameness"], (
        "and the draft is still stopped, for the reason it should be"
    )
