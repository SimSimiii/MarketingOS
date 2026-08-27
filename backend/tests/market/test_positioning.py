"""The positioning map: territory arithmetic over claims.

Everything here is deterministic by design, so these tests are about the
rules rather than about a model's behaviour - which is the point of computing
the map in code.
"""

from app.knowledge.artifacts import KnowledgeArtifacts
from app.knowledge.ledger import Evidence, EvidenceKind, EvidenceLedger
from app.market.claims import Claim, ClaimAxis, ClaimSet, overlap, significant_words
from app.market.positioning import Territory, build, claims_from_knowledge
from app.market.rivals import RivalProfile


def rival(name: str, *claims: Claim, proof: list[Claim] | None = None) -> RivalProfile:
    return RivalProfile(
        name=name,
        url=f"https://{name}.example",
        verified=True,
        claims=ClaimSet(claims=list(claims)),
        proof_shown=proof or [],
    )


def claim(text: str, axis: ClaimAxis, specific: bool = False) -> Claim:
    return Claim(text=text, verbatim=text, axis=axis, specific=specific)


# ------------------------------------------------------------------ territory


def test_an_axis_nobody_else_claims_is_open_ground() -> None:
    ours = ClaimSet(claims=[claim("self-hosted, no data leaves your VPC", ClaimAxis.CONTROL)])
    positioning = build(ours, [rival("alpha", claim("fastest setup", ClaimAxis.SPEED))])

    control = next(r for r in positioning.readings if r.axis is ClaimAxis.CONTROL)
    assert control.territory is Territory.OPEN
    assert control.rivals_claiming == 0


def test_an_axis_most_of_the_field_claims_is_table_stakes() -> None:
    ours = ClaimSet(claims=[claim("live in minutes", ClaimAxis.SPEED)])
    rivals = [
        rival("alpha", claim("up and running fast", ClaimAxis.SPEED)),
        rival("beta", claim("start in no time", ClaimAxis.SPEED)),
        rival("gamma", claim("quick to deploy", ClaimAxis.SPEED)),
    ]
    positioning = build(ours, rivals)

    speed = next(r for r in positioning.readings if r.axis is ClaimAxis.SPEED)
    assert speed.territory is Territory.TABLE_STAKES
    assert speed.rivals_claiming == 3


def test_one_rival_out_of_four_leaves_the_axis_contested() -> None:
    ours = ClaimSet(claims=[claim("SOC 2 Type II", ClaimAxis.SECURITY)])
    rivals = [
        rival("alpha", claim("SOC 2 audited", ClaimAxis.SECURITY)),
        rival("beta", claim("fast", ClaimAxis.SPEED)),
        rival("gamma", claim("cheap", ClaimAxis.PRICE)),
        rival("delta", claim("broad", ClaimAxis.BREADTH)),
    ]
    positioning = build(ours, rivals)

    security = next(r for r in positioning.readings if r.axis is ClaimAxis.SECURITY)
    assert security.territory is Territory.CONTESTED


def test_the_only_specific_claim_wins_a_crowded_axis() -> None:
    """The non-obvious half of the idea. Everybody promises fast setup; the
    one company that puts a number on it is not competing on a crowded axis,
    it is the only checkable claim in the field."""
    ours = ClaimSet(
        claims=[claim("first API call in under 5 minutes", ClaimAxis.SPEED, specific=True)]
    )
    rivals = [
        rival("alpha", claim("blazing fast setup", ClaimAxis.SPEED)),
        rival("beta", claim("get going in no time", ClaimAxis.SPEED)),
        rival("gamma", claim("the quickest way to start", ClaimAxis.SPEED)),
    ]
    positioning = build(ours, rivals)

    speed = next(r for r in positioning.readings if r.axis is ClaimAxis.SPEED)
    assert speed.territory is Territory.OPEN
    assert speed.only_specific
    assert speed.rivals_claiming == 3


def test_a_rival_with_a_figure_takes_the_axis_back() -> None:
    """The mirror of the rule above: specificity only wins while it is
    unique."""
    ours = ClaimSet(
        claims=[claim("first API call in under 5 minutes", ClaimAxis.SPEED, specific=True)]
    )
    rivals = [
        rival("alpha", claim("running in 4 minutes flat", ClaimAxis.SPEED, specific=True)),
        rival("beta", claim("get going in no time", ClaimAxis.SPEED)),
    ]
    positioning = build(ours, rivals)

    speed = next(r for r in positioning.readings if r.axis is ClaimAxis.SPEED)
    assert not speed.only_specific
    assert speed.territory is Territory.TABLE_STAKES


def test_an_axis_only_they_claim_is_exposed() -> None:
    positioning = build(
        ClaimSet(claims=[claim("cheap", ClaimAxis.PRICE)]),
        [rival("alpha", claim("dedicated migration engineer", ClaimAxis.SUPPORT))],
    )
    support = next(r for r in positioning.readings if r.axis is ClaimAxis.SUPPORT)
    assert support.territory is Territory.EXPOSED
    assert not support.ours
    assert "Do not" in support.render() or "do not" in support.render()


# --------------------------------------------------------------------- proof


def test_the_proof_asymmetry_is_reported() -> None:
    rivals = [
        rival("alpha", proof=[claim("Ramp cut review time", ClaimAxis.PROOF)]),
        rival("beta", proof=[claim("Linear uses this daily", ClaimAxis.PROOF)]),
        rival("gamma"),
    ]
    positioning = build(ClaimSet(), rivals, we_have_proof=False)

    assert positioning.rivals_with_proof == 2
    assert positioning.proof_deficit
    assert "named customer" in positioning.render_for_strategy()


def test_no_deficit_when_we_have_proof_too() -> None:
    rivals = [rival("alpha", proof=[claim("Ramp uses it", ClaimAxis.PROOF)])]
    positioning = build(ClaimSet(), rivals, we_have_proof=True)
    assert not positioning.proof_deficit


# ------------------------------------------------------------- crowd of words


def test_crowd_words_need_two_rivals() -> None:
    """One competitor sharing a word is a coincidence; two is the category."""
    rivals = [
        rival("alpha", claim("agentic orchestration everywhere", ClaimAxis.OTHER)),
        rival("beta", claim("agentic orchestration for teams", ClaimAxis.OTHER)),
        rival("gamma", claim("bespoke idiosyncratic wording", ClaimAxis.OTHER)),
    ]
    positioning = build(ClaimSet(), rivals)

    assert "agentic" in positioning.crowd_words
    assert "orchestration" in positioning.crowd_words
    assert "bespoke" not in positioning.crowd_words


def test_a_wordy_rival_cannot_define_the_category_alone() -> None:
    """Counted per rival, not per claim: one site that says "seamless" eight
    times has said it once."""
    rivals = [
        rival(
            "alpha",
            *[claim(f"seamless thing number {n}", ClaimAxis.OTHER) for n in range(8)],
        ),
        rival("beta", claim("something else entirely", ClaimAxis.OTHER)),
    ]
    positioning = build(ClaimSet(), rivals)
    assert "seamless" not in positioning.crowd_words


# --------------------------------------------------------- reading our claims


def test_our_claims_come_from_the_ledger_without_a_second_model_call() -> None:
    artifacts = KnowledgeArtifacts(
        evidence=EvidenceLedger(
            entries=[
                Evidence(
                    id="E1",
                    kind=EvidenceKind.PRICE,
                    claim="1,500 free credits, no card",
                    verbatim="Start with 1,500 free credits. No card required.",
                ),
                Evidence(
                    id="E2",
                    kind=EvidenceKind.FEATURE,
                    claim="first API call in under 5 minutes",
                    verbatim="From sign-up to your first API call takes under 5 minutes.",
                ),
                Evidence(
                    id="E3",
                    kind=EvidenceKind.TESTIMONIAL,
                    claim="Ramp says it saved them a quarter",
                    verbatim="It saved us a quarter of engineering time.",
                ),
            ]
        )
    )
    ours = claims_from_knowledge(artifacts)

    axes = {claim.text: claim.axis for claim in ours.claims}
    # The kind settles it where it can.
    assert axes["1,500 free credits, no card"] is ClaimAxis.PRICE
    assert axes["Ramp says it saved them a quarter"] is ClaimAxis.PROOF
    # And the words settle it where the kind cannot - a `feature` entry about
    # minutes is a speed claim, whatever it is filed as.
    assert axes["first API call in under 5 minutes"] is ClaimAxis.SPEED
    assert all(claim.verbatim for claim in ours.claims)


def test_a_figure_makes_a_claim_specific_without_being_told() -> None:
    assert Claim(text="25 models across 9 providers").is_specific
    assert Claim(text="no card required").is_specific
    assert not Claim(text="the broadest coverage available").is_specific
    # An explicit answer always wins over the derivation.
    assert not Claim(text="25 models", specific=False).is_specific


# ------------------------------------------------------------------ degrading


def test_an_unread_field_is_not_an_empty_one() -> None:
    """A competitor whose site would not load must not be counted as a
    competitor who claims nothing - that would hand us open ground we have
    not earned."""
    unread = RivalProfile(name="alpha", url="https://alpha.example", verified=False)
    positioning = build(ClaimSet(claims=[claim("fast", ClaimAxis.SPEED)]), [unread])

    assert positioning.is_empty
    assert positioning.rivals_profiled == 0
    assert "could be read" in " ".join(positioning.notes)


def test_the_strategist_is_told_when_nobody_has_looked() -> None:
    rendered = build(ClaimSet(), []).render_for_strategy()
    assert "Nobody has profiled this market" in rendered
    assert "carry a figure" in rendered


# -------------------------------------------------------------- text helpers


def test_significant_words_drops_the_words_every_company_uses() -> None:
    """A sentence made entirely of B2B furniture has no distinctive words at
    all, and saying so is the whole basis of the swap test."""
    assert significant_words("The best platform for teams building fast software") == set()
    assert significant_words("25 models across 9 providers") == {"models", "providers"}


def test_overlap_sees_through_rewording() -> None:
    assert overlap("cut onboarding from three days", "onboarding cut from three days") > 0.9
    assert overlap("self-hosted and portable", "priced per seat") == 0.0
