"""The campaign report: the user's receipt, and the next campaign's memory.

Two jobs, and the second one is the reason this exists at all. As a receipt it
tells the user what they got and how confident the system is in it. As memory
it is read by the Strategist on the next campaign for the same business - what
scored well, which angle needed three rewrites, which gap kept costing
specificity. Without it every campaign starts from the same blank state as the
first, which was true of the old system and is the difference between a tool
and a system that gets better at one company's marketing.
"""

from pydantic import BaseModel, Field

from app.marketing.reader import PULL_THRESHOLD, PanelRead


class ReaderVerdict(BaseModel):
    """What the cold reader actually said, kept.

    The system's most expensive judgment used to reach the user as a single
    digit. A run that scored 4/10 persisted exactly `{"pull": 4}` - and the
    reader had, in the same call, said what it thought the email was selling,
    where it stopped reading, what was really stopping it clicking, and the
    one thing the email would have had to say for it to click. All of it was
    thrown away at the end of the craft loop.

    That is the wrong thing to discard twice over. It is the only output in
    the system that says what to write *instead* rather than passing verdict
    on what was written - `reader.md` calls it the most valuable line in the
    report - and it is already paid for. A user shown "4/10" learns that
    something is wrong; a user shown "I could not tell what this company
    does" and "I would have clicked if it had told me who else uses it"
    learns what to do on Monday.

    Kept per email on the receipt, so it survives the run and is still there
    when they come back to the campaign a week later.
    """

    #: What a stranger thought was being offered, in their words. The single
    #: most diagnostic line here: an answer that does not match what the
    #: product is means the copy failed before any of its arguments were
    #: judged.
    what_it_sells: str = ""
    #: The first line where they lost interest, quoted from the email.
    stopped_at: str = ""
    #: The real reason they would not click.
    biggest_doubt: str = ""
    #: "I would have clicked if this email had told me ___".
    to_click_it_would_have_to: str = ""
    #: Lines they would cut or rewrite, quoted.
    fixes: list[str] = Field(default_factory=list)
    #: Out of a hundred people like them.
    opens_in_100: int | None = None
    clicks_in_100: int | None = None
    #: Which reader this was, when a panel read the same draft. Every panel
    #: member is kept rather than only the median: copy that one reader loved
    #: and another could not parse is not finished, and a single stored
    #: verdict hides exactly that.
    persona: str = ""
    pull: int = 0

    @classmethod
    def from_panel(cls, panel: PanelRead) -> list["ReaderVerdict"]:
        return [
            cls(
                what_it_sells=read.what_it_sells,
                stopped_at=read.stopped_at,
                biggest_doubt=read.biggest_doubt,
                to_click_it_would_have_to=read.to_click_it_would_have_to,
                fixes=list(read.fixes),
                opens_in_100=read.opens_in_100,
                clicks_in_100=read.clicks_in_100,
                persona=read.persona,
                pull=read.pull,
            )
            for read in panel.reported
        ]


class EmailReportLine(BaseModel):
    position: int
    subject: str = ""
    single_idea: str = ""
    #: How much the cold reader wanted the thing, on the version that shipped.
    pull: float = 0.0
    revisions: int = 0
    #: False when the email shipped with an automatic check still failing -
    #: only possible when the run ran out of budget mid-repair.
    clean: bool = True
    #: Whether the cold reader would actually have clicked. False means the
    #: loop stopped rewriting, not that it decided this was good enough.
    landed: bool = True
    #: True when the loop stopped because rewriting had stopped improving the
    #: draft, rather than because it ran out of attempts. "We tried everything
    #: we had" and "we stopped because it was not working" are different
    #: answers to what the user should do next: buy more rewrites, or change
    #: what the copy is allowed to argue.
    rewrites_stopped_helping: bool = False
    #: False when no cold reader came back at all, which makes `pull` a
    #: placeholder rather than a score.
    read_reported: bool = True
    #: Ledger ids the Strategist said this email is built on.
    evidence_assigned: list[str] = Field(default_factory=list)
    #: Of those, the ones whose figure, name or quotation actually reached the
    #: page - checked in code on the version that shipped, not assumed from
    #: the brief. This field used to hold the *assignment*, which is a
    #: statement about the plan and reads on a receipt as a statement about
    #: the copy.
    evidence_spent: list[str] = Field(default_factory=list)
    #: How many third-party entries the copy names or quotes. The only kind of
    #: support that survives a stranger's first-contact discount.
    attributions: int = 0
    unresolved: list[str] = Field(default_factory=list)
    #: What the cold readers said about the version that shipped. Empty
    #: only when nobody could read it. See `ReaderVerdict`.
    reader_verdicts: list[ReaderVerdict] = Field(default_factory=list)
    #: Interchangeable openings and category boilerplate found in the
    #: shipped copy, as the free differentiation check reported them.
    #: Present on the receipt even when the run was too cheap to act on
    #: them, because they are the cheapest thing a user can fix by hand.
    sameness: list[str] = Field(default_factory=list)

    @property
    def what_would_have_worked(self) -> list[str]:
        """Every reader's answer to what the email should have said instead.

        The one place a user is told what to do rather than what went wrong.
        Deduplicated, because three panel members who wanted the same thing
        are one instruction and printing it three times reads as noise.
        """
        wanted: list[str] = []
        for verdict in self.reader_verdicts:
            line = verdict.to_click_it_would_have_to.strip()
            if line and line not in wanted:
                wanted.append(line)
        return wanted

    @property
    def argues_from_nothing(self) -> bool:
        """Built on assigned facts and carrying none of them.

        Not a failure the gates block - the copy invented nothing, which is
        what they check - and not one a cold reader reliably reports, which is
        why it is worth naming on the receipt in its own words.
        """
        return bool(self.evidence_assigned) and not self.evidence_spent

    def render(self) -> str:
        state = "" if self.clean else " (shipped with unresolved automatic checks)"
        rewrites = "no rewrites" if not self.revisions else f"{self.revisions} rewrite(s)"
        if not self.read_reported:
            score = "no cold reader reported back"
        elif self.landed:
            score = f"pull {self.pull:.0f}/10"
        else:
            # Named rather than left to be inferred from a number: a run that
            # stopped because it was out of rewrites and a run that stopped
            # because the copy worked both end, and only one of them is done.
            score = f"pull {self.pull:.0f}/10 - still below the {PULL_THRESHOLD}/10 floor" + (
                ", and rewriting had stopped moving it" if self.rewrites_stopped_helping else ""
            )
        proof = (
            " - and argues from none of the evidence it was assigned"
            if self.argues_from_nothing
            else ""
        )
        return (
            f"- Email {self.position} \"{self.subject}\": {self.single_idea or 'no idea recorded'}"
            f" - {score} after {rewrites}{state}{proof}"
        )


class CampaignReport(BaseModel):
    request: str = ""
    delivered: int = 0
    promised: int = 0
    contract_violations: list[str] = Field(default_factory=list)
    emails: list[EmailReportLine] = Field(default_factory=list)
    #: Gaps in the business's knowledge that visibly constrained this campaign.
    limiting_gaps: list[str] = Field(default_factory=list)
    #: The one question the user could answer that would change the next run
    #: most, taken from the worst unanswered gap.
    what_would_help_most: str = ""
    #: Everything the run needs answered before it is worth spending anything,
    #: worst first. Only ever filled on a run that stopped to ask - see
    #: `EmailCampaignPipeline._needs_input`. On every other run the same
    #: material reaches the user as `what_would_help_most`, which is advice
    #: rather than a blocker.
    questions: list[str] = Field(default_factory=list)
    sequence_summary: str = ""
    knowledge_version: int = 0
    notes: list[str] = Field(default_factory=list)

    @property
    def average_pull(self) -> float:
        """Averaged over the emails somebody actually read. Counting a missing
        read as a zero, or as anything else, reports a number no reader gave."""
        scored = [line for line in self.emails if line.read_reported]
        if not scored:
            return 0.0
        return sum(line.pull for line in scored) / len(scored)

    @property
    def all_clean(self) -> bool:
        return all(line.clean for line in self.emails) and not self.contract_violations

    @property
    def unsubstantiated(self) -> list[EmailReportLine]:
        """Emails that spent none of the proof they were built on.

        Distinct from `below_floor`, and it has to be: an email can read
        beautifully to a cold panel and still be this company asserting things
        about itself, which is the failure that only shows up when a real
        recipient declines to believe it. Nothing in the run blocks on it -
        the writer is told, the loop prefers the version that carries the
        proof, and past that it is the user's call.
        """
        return [line for line in self.emails if line.argues_from_nothing]

    @property
    def below_floor(self) -> list[EmailReportLine]:
        return [line for line in self.emails if line.read_reported and not line.landed]

    @property
    def healthy(self) -> bool:
        """Whether this run produced what it set out to produce.

        The deterministic checks are not the whole question. An email that
        passes every gate, spends its evidence and is delivered on time can
        still be one a stranger told us they would not click - and a run that
        reports that as success is a run whose headline number the user has
        no reason to trust the next time it is high.
        """
        return (
            self.all_clean
            and not self.below_floor
            and bool(self.emails)
            and all(line.read_reported for line in self.emails)
        )

    def render(self) -> str:
        lines = [
            f"Request: {self.request}",
            (
                f"Delivered {self.delivered} of {self.promised} email(s). "
                f"Average cold-reader pull {self.average_pull:.1f}/10."
            ),
            *[line.render() for line in self.emails],
        ]
        if self.below_floor:
            positions = ", ".join(str(line.position) for line in self.below_floor)
            lines.append(
                f"Email(s) {positions} never reached the {PULL_THRESHOLD}/10 floor. The loop "
                "stopped rewriting them; it did not decide these were ready to send."
            )
        if self.sequence_summary:
            lines.append(f"Sequence: {self.sequence_summary}")
        if self.unsubstantiated:
            positions = ", ".join(str(line.position) for line in self.unsubstantiated)
            lines.append(
                f"Email(s) {positions} made no use of the evidence they were built on. "
                "Nothing in them is invented - but nothing in them is checkable either, and a "
                "stranger has no reason to believe a company describing itself."
            )
        if self.contract_violations:
            lines.append("Contract problems: " + "; ".join(self.contract_violations))
        if self.limiting_gaps:
            lines.append(
                "What held the copy back: " + "; ".join(self.limiting_gaps)
            )
        if self.questions:
            lines.append(
                "Answer these and this campaign becomes writable:\n"
                + "\n".join(f"- {question}" for question in self.questions)
            )
        elif self.what_would_help_most:
            lines.append(f"What would help most next time: {self.what_would_help_most}")
        lines.extend(self.notes)
        return "\n".join(lines)

    def render_learnings(self) -> str:
        """What the next campaign for this business should know.

        Deliberately about angles and constraints rather than scores: a future
        Strategist can use "the pricing objection needed three rewrites before
        it landed" and can do nothing at all with "7.4 average".
        """
        if not self.emails:
            return ""
        worked = [line for line in self.emails if line.pull >= 7 and line.revisions == 0]
        struggled = [line for line in self.emails if line.revisions >= 2 or line.pull < 6]
        parts = [f'Previous campaign: "{self.request}"']
        if worked:
            parts.append(
                "Landed immediately: "
                + "; ".join(f"{line.single_idea}" for line in worked if line.single_idea)
            )
        if struggled:
            parts.append(
                "Needed rework: "
                + "; ".join(
                    f"{line.single_idea or f'email {line.position}'}" for line in struggled
                )
            )
        if self.limiting_gaps:
            parts.append("Still missing: " + "; ".join(self.limiting_gaps))
        return "\n".join(part for part in parts if part.strip())
