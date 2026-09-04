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
    #: --- the argument, in four beats -------------------------------------
    #:
    #: `single_idea` is the claim this email makes. These four are the
    #: argument that makes the claim mean anything, and until they existed
    #: the brief had no place to put one. A writer given a claim, proof for
    #: the claim and an objection to answer writes an assertion with a
    #: citation attached: true, checkable, and no reason for a stranger to
    #: care. What was missing is the shape every piece of persuasion has -
    #: here is what you are living with, here is what you do about it now,
    #: here is why that keeps failing, here is what this does instead.
    #:
    #: Filled by the Strategist, the only role with both the audience model
    #: and the positioning map in front of it. Left empty they render as a
    #: refusal to invent one, which is the honest answer and the one that
    #: tells the writer to argue from what it does have.
    #:
    #: The problem as the reader would say it out loud, in their words. Not
    #: the problem the product solves - the one they would name unprompted if
    #: somebody asked what their week was like.
    felt_need: str = ""
    #: What they do about it today. A spreadsheet, an in-house script, an
    #: agency, a junior's Thursday, or nothing at all. Every reader is
    #: already solving this somehow, and copy that does not know how is
    #: arguing against an alternative it has never met.
    status_quo: str = ""
    #: Where that approach structurally falls short - the reason it fails
    #: that is about the approach and not about the people using it. This is
    #: the beat the system had no field for and could therefore never argue.
    #: It is what makes a claim land: "we are fast" is a boast, and "the
    #: reason every one of these is slow is that it re-reads the whole corpus
    #: per call" is an argument. Only the second earns the sentence after it.
    #:
    #: About the category's approach, never about a named competitor. Naming
    #: a rival moves the email onto their ground and hands the reader a
    #: second brand to think about; naming the mechanism they all share is
    #: the same insight with none of that cost.
    why_it_fails: str = ""
    #: What this product does instead, at the level of how rather than what.
    #: The reason it is not subject to the failure above - the design
    #: decision, the constraint, the thing it does differently. Not a
    #: benefit: "so you save time" is where a mechanism gets thrown away and
    #: replaced by the adjective it was supposed to have earned.
    mechanism: str = ""
    #: Other claims this slot could have owned, best first.
    #:
    #: Which argument a stranger responds to is not derivable from the brief -
    #: it is the one thing about a campaign that has to be found out - and
    #: until this existed the strategist picked one and the whole run defended
    #: it. The bake-off wrote several openings onto the same claim, so three
    #: drafts were three first sentences over one bet, and every rewrite was
    #: told to keep the idea. A run could therefore discover that the idea was
    #: wrong and had no way to act on it.
    #:
    #: These are what the bake-off actually varies, and what the loop pivots to
    #: when rewriting stops moving the copy.
    alternative_ideas: list[str] = Field(default_factory=list)
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
    #: V2 product facts that remain in the complete ledger for gates/history
    #: but must not enter writer or critic prompt material.
    forbidden_evidence_ids: list[str] = Field(default_factory=list)
    #: Capability ids the current product profile does not license. Unlike a
    #: prose warning, these feed a deterministic scope gate on every draft.
    forbidden_capability_ids: list[str] = Field(default_factory=list)
    #: The reason this reader would not act, which this email answers by name.
    objection: str = ""
    #: How it should feel - "matter-of-fact", "slightly impatient", "warm".
    tone: str = ""
    #: The single thing it asks for, taken from the offer sheet.
    call_to_action: str = ""
    subject_strategy: str = ""
    #: Angles, proofs and opening moves already spent by earlier emails.
    must_not_reuse: list[str] = Field(default_factory=list)

    def render_argument(self) -> str:
        """The four beats, as the shape of the email rather than as fields.

        Rendered together and in order, because the order is the point. A
        writer handed `why_it_fails` inside a flat list of eleven attributes
        treats it as one more thing that could go on the page; handed it as
        the third beat of an argument, it is the sentence without which the
        fourth one means nothing.
        """
        beats = [
            ("What they are actually living with", self.felt_need),
            ("What they do about it today", self.status_quo),
            ("Why that keeps falling short", self.why_it_fails),
            ("What this does instead, and how", self.mechanism),
        ]
        written = [(label, value.strip()) for label, value in beats if value.strip()]
        if not written:
            return (
                "    Not established - nothing was handed down about what this reader does "
                "today or why it falls short. Do not invent a status quo to knock down: "
                "argue from the evidence and the specifics you were given."
            )
        return "\n".join(
            f"    {index}. {label}: {value}"
            for index, (label, value) in enumerate(written, start=1)
        )

    def render(self) -> str:
        # Deliberately without `alternative_ideas`. A writer shown the claims
        # this email could have argued writes an email that gestures at all of
        # them; the alternatives are for the loop to choose between, one draft
        # at a time, and each draft is told about exactly one idea - its own.
        return (
            f"Position: {self.position}\n"
            f"Its job: {self.job}\n"
            f"The one idea it owns: {self.single_idea}\n"
            f"The argument it makes, in this order:\n{self.render_argument()}\n"
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
    #: What this company sells, in one plain sentence a stranger could repeat
    #: back. The sentence every email in the sequence has to leave the reader
    #: holding, however it gets there.
    #:
    #: Campaign-level rather than per-email because it is the same sentence
    #: every time and it is not the argument - each email argues its own idea
    #: and all of them are selling the same thing. Written by the Strategist
    #: rather than lifted from the business profile because the profile says
    #: what the company does and this says what it is *to this reader*: the
    #: same product is "a way to stop losing Friday afternoons" to one
    #: segment and "an audit trail your compliance team will accept" to
    #: another, and a writer handed the wrong one writes past its reader.
    #:
    #: This exists because of a specific, repeatable failure. Every rule the
    #: writer follows pushes the product off the page - open on the reader,
    #: argue one idea, prefer specifics to adjectives, stay under two hundred
    #: words - and followed well they produce an email that describes a
    #: Tuesday with real precision and never says what is being sold. The
    #: cold reader would report it and nothing consumed the report. Now the
    #: sentence is decided once, in the brief, where it can be checked.
    orientation: str = ""
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
            f"What we are selling them, in one sentence: {self.orientation}\n"
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
