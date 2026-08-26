"""What the copy can prove, settled before a word of it is written.

The compiler already works this out. `find_gaps` records that no customer is
named, that nothing measurable was found, that there is no action a reader can
be asked to take - with the cost of each hole and the question that would
close it - and every one of those reports has been rendered into prompts and
onto the finished report, where the user reads it after paying for the run.
Nothing has ever acted on it.

So a business with no testimonial, no named customer and no attributed outcome
gets an outcome-led campaign planned anyway. It gets written, disbelieved by a
cold reader, rewritten, and disbelieved again, because a rewrite has never
once added a proof that was not in the material. The loop is working exactly
as designed and cannot win: the copy is not underwritten, it is unprovable,
and those have different fixes.

This module makes the distinction before the money is spent. It costs no model
call - evidence is already typed by kind, and the gaps are already computed -
and it produces two things: the angles genuinely available to the Strategist,
and the one thing the user could hand over that would change the answer.
"""

from dataclasses import dataclass

from app.knowledge.artifacts import Gap, KnowledgeArtifacts
from app.knowledge.ledger import Evidence, EvidenceKind

#: Evidence that somebody other than the company vouched for it. A cold reader
#: discounts a company's claims about itself to roughly nothing on first
#: contact; these are the only entries that survive that discount.
PROOF_KINDS = (
    EvidenceKind.TESTIMONIAL,
    EvidenceKind.CUSTOMER,
    EvidenceKind.AWARD,
    EvidenceKind.CERTIFICATION,
)

#: Evidence a reader can check for themselves without trusting anyone. Weaker
#: than proof and not a substitute for it, but it is what makes an email
#: specific when no proof exists, and specific beats persuasive.
CHECKABLE_KINDS = (
    EvidenceKind.METRIC,
    EvidenceKind.PRICE,
    EvidenceKind.INTEGRATION,
    EvidenceKind.GUARANTEE,
)

#: Worst first. Gap severities as `find_gaps` assigns them.
_SEVERITY_ORDER = {"blocking": 0, "significant": 1, "minor": 2}


@dataclass(frozen=True)
class ProofPosture:
    """What this campaign is allowed to argue from, and what it is missing."""

    proof: list[Evidence]
    checkable: list[Evidence]
    #: Holes the compiler rated as making the campaign not worth writing as
    #: asked - no action to ask for, nobody established to write to.
    blocking: list[Gap]
    #: The questions that would close the holes, worst first, in the user's
    #: language rather than the compiler's.
    asks: list[str]

    @property
    def has_proof(self) -> bool:
        return bool(self.proof)

    @property
    def has_checkable(self) -> bool:
        return bool(self.checkable)

    @property
    def nothing_to_argue_from(self) -> bool:
        """Whether a campaign written from this would be assertion all the way
        down.

        Not the same as "no testimonials". A business with a price, a limit and
        a mechanism has plenty to write about even though nobody has vouched
        for it - see `render_for_strategy`, which lists the four angles that
        need no proof. This is the case where none of those angles exist
        either, or where the compiler found a hole a campaign cannot be
        written around at all, and it is the only case worth stopping a run
        over.
        """
        return (not self.has_proof and not self.has_checkable) or bool(self.blocking)

    def summary(self) -> str:
        """One line for the run log and the receipt."""
        if self.has_proof:
            return f"{len(self.proof)} third-party proof point(s) available to spend"
        if self.has_checkable:
            return (
                "Nothing here proves anyone uses this. The copy can be specific and checkable, "
                "but it cannot be believed on someone else's word"
            )
        return (
            "No proof and nothing checkable. Every sentence will be this company asserting "
            "something about itself"
        )

    def render_for_strategy(self) -> str:
        """The section the Strategist plans against.

        Phrased as which angles are open rather than as a warning, because a
        warning produces a hedge: a model told the evidence is thin writes
        vaguer copy, which is the opposite of the correct response. Missing
        proof does not mean claim less confidently, it means argue from
        something else.
        """
        lines: list[str] = [self.summary() + "."]

        if self.has_proof:
            lines.append(
                "\nSpend these deliberately - they are the only entries a stranger has any "
                "reason to believe, and there are not many:\n"
                + "\n".join(f"- [{entry.id}] {entry.claim}" for entry in self.proof)
            )
        else:
            lines.append(
                "\n**Do not plan an email around proof that does not exist.** No customer is "
                "named, nobody is quoted, and no outcome is attributed to anyone but this "
                "company. An angle that needs social proof, a named result, a before-and-after, "
                "or any form of \"companies like yours\" cannot be written from this material - "
                "the writer will either hedge it into nothing or invent it, and the evidence "
                "gate will send the invention straight back.\n\n"
                "These angles do not need proof, and one of them is what this campaign is:\n"
                "- **The mechanism, stated plainly enough to be judged.** How the thing actually "
                "works, in enough detail that the reader can decide for themselves whether it "
                "would work for them. This does not ask for trust, so its absence costs nothing.\n"
                "- **A specific they can check in a minute.** A price, a limit, a supported "
                "integration, an exact number of steps. Verifiable beats impressive.\n"
                "- **An invitation to test rather than believe.** Where the product is "
                "self-serve, the reader can settle the question themselves in less time than it "
                "takes to believe a claim - so ask them to, and stake the email on the thing "
                "holding up.\n"
                "- **The objection, named more precisely than they would name it.** Being "
                "understood is evidence of a kind, and it is the one kind this material can "
                "always supply."
            )

        if self.has_checkable:
            lines.append(
                "\nCheckable specifics - not proof, but the difference between an email that "
                "reads as written by someone who knows the product and one that reads as "
                "written about it:\n"
                + "\n".join(f"- [{entry.id}] {entry.claim}" for entry in self.checkable)
            )

        if self.blocking:
            lines.append(
                "\nThe material is missing something a campaign normally cannot do without. "
                "Plan around it and say so in `sequence_rationale`:\n"
                + "\n".join(f"- {gap.missing} - {gap.impact}" for gap in self.blocking)
            )

        if self.asks:
            lines.append(
                "\nEnd `sequence_rationale` with the single thing the user could send us that "
                "would most change this campaign. They are being asked these, worst first:\n"
                + "\n".join(f"- {ask}" for ask in self.asks)
            )
        return "\n".join(lines)


def assess(artifacts: KnowledgeArtifacts) -> ProofPosture:
    """Read the compiled knowledge for what it can and cannot support."""
    unanswered = sorted(
        artifacts.gaps.unanswered,
        key=lambda gap: _SEVERITY_ORDER.get(gap.severity, len(_SEVERITY_ORDER)),
    )
    return ProofPosture(
        proof=artifacts.evidence.of_kind(*PROOF_KINDS),
        checkable=artifacts.evidence.of_kind(*CHECKABLE_KINDS),
        blocking=[gap for gap in unanswered if gap.severity == "blocking"],
        asks=[gap.question for gap in unanswered if gap.question],
    )
