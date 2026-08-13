"""The campaign brief: the single artifact that decides whether the copy is good.

Everything before this phase gathers; everything after it executes. A writer
handed a brief that names one idea, the evidence that carries it and the
objection it has to beat cannot write a generic email - there is no room left
for one. A writer handed "write a compelling onboarding email" has nothing but
room.

The briefs are also where sequence design happens, and it happens before a
single word is written. Deciding email 3's angle after emails 1 and 2 have
already spent the two strongest proofs is how sequences end up with a good
opener and four pieces of filler.
"""

from pydantic import BaseModel, Field

from app.marketing.contract import DeliverableContract


class EmailBrief(BaseModel):
    """One slot in the sequence, decided before any of it is written."""

    position: int = 1
    #: What this email is for. "Get them to connect a data source", not
    #: "introduce the product".
    job: str = ""
    #: The one thing it argues. Two briefs must never be able to swap these.
    single_idea: str = ""
    #: What the reader believes before this email and what they believe after
    #: it. The field that says where an email belongs in a sequence: `job` is
    #: the outcome and `single_idea` is the claim, but neither says what has
    #: to change in the reader's head - which is the whole difference between
    #: email 1 and email 3, and the thing a sequence can be checked against.
    belief_shift: str = ""
    #: Ledger ids this email spends. Evidence is finite: an id used here
    #: should not be the backbone of another email.
    evidence_ids: list[str] = Field(default_factory=list)
    #: What this email deliberately does not say, though it could. The one
    #: field here that subtracts: everything else a brief carries is a reason
    #: to put something on the page, and a system with only additive pressure
    #: turns every email into a product page by the third rewrite.
    must_not_say: list[str] = Field(default_factory=list)
    #: The reason this reader would not act, which this email answers by name.
    objection: str = ""
    #: How it should feel - "matter-of-fact", "slightly impatient", "warm".
    tone: str = ""
    #: The single thing it asks for, taken from the offer sheet.
    call_to_action: str = ""
    subject_strategy: str = ""
    #: Angles, proofs and opening moves already spent by earlier emails.
    must_not_reuse: list[str] = Field(default_factory=list)

    def render(self) -> str:
        return (
            f"Position: {self.position}\n"
            f"Its job: {self.job}\n"
            f"The one idea it owns: {self.single_idea}\n"
            f"What has to change in their head: {self.belief_shift or 'not specified'}\n"
            f"Evidence it spends: {', '.join(self.evidence_ids) or 'none assigned'}\n"
            f"What it leaves out on purpose: {'; '.join(self.must_not_say) or 'nothing named'}\n"
            f"The objection it answers: {self.objection or 'none assigned'}\n"
            f"Register: {self.tone or 'plain and direct'}\n"
            f"What it asks for: {self.call_to_action or 'the single next step'}\n"
            f"Subject approach: {self.subject_strategy or 'concrete, no clickbait'}\n"
            f"Do not reuse: {'; '.join(self.must_not_reuse) or 'nothing spent yet'}"
        )

    def summary(self) -> str:
        return f"#{self.position} {self.single_idea or self.job}"


class CampaignBrief(BaseModel):
    """What this campaign says, to whom, in what order."""

    #: How the request was read, stated out loud. An onboarding request is not
    #: a sales request, and getting that wrong silently is how a run produces
    #: five well-written emails aimed at the wrong person.
    interpretation: str = ""
    #: One person, in a situation. Never a segment.
    reader: str = ""
    #: The name of the audience segment `reader` was drawn from, exactly as
    #: the audience model spells it. This is what decides who reads the drafts
    #: cold: a campaign aimed at a founder with no engineer, graded by a
    #: mid-market product manager, fails on a premise the reader does not
    #: have, and every rewrite after that answers the wrong person's doubts.
    reader_segment: str = ""
    #: The one promise the whole campaign makes.
    promise: str = ""
    #: How the sequence escalates from first to last.
    arc: str = ""
    sequence_rationale: str = ""
    emails: list[EmailBrief] = Field(default_factory=list)
    #: Anything about voice this campaign needs beyond the brand's default.
    voice_notes: str = ""
    contract: DeliverableContract = Field(default_factory=DeliverableContract)

    def render(self) -> str:
        emails = "\n\n".join(
            f"### Email {brief.position}\n{brief.render()}" for brief in self.emails
        )
        return (
            f"How the request was read: {self.interpretation}\n"
            f"Writing to: {self.reader}\n"
            f"The promise: {self.promise}\n"
            f"The arc: {self.arc}\n"
            f"Why this order: {self.sequence_rationale}\n\n"
            f"{emails}"
        )

    def render_arc(self) -> str:
        """The shape of the sequence without the detail - what a single email's
        writer needs to know about the ones it is not writing."""
        return "\n".join(
            f"- Email {brief.position}: {brief.job} - {brief.single_idea}"
            for brief in self.emails
        ) or "- single email, no sequence"

    def brief_for(self, position: int) -> EmailBrief | None:
        return next((brief for brief in self.emails if brief.position == position), None)
