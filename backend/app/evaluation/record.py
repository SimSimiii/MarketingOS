"""One run's measurements, in a form two runs can be compared with.

Everything here is read off artifacts the pipeline already produces. Nothing
asks a model to score anything: a second judge introduced only for evaluation
is a judge nobody has calibrated, and it would be graded by the same family of
model that wrote the copy.

The one number to watch across versions is `cost_per_shipped_email`. Cost per
*run* rewards a run that gives up early, and quality alone rewards spending
without limit; the ratio is the only one of the three that gets worse when
either half does.
"""

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from app.evaluation.head_to_head import ControlResult
from app.marketing.pipeline import CampaignRunResult
from app.marketing.reader import PULL_THRESHOLD


class EmailRecord(BaseModel):
    """What happened to one email, from the artifacts that already exist."""

    position: int
    subject: str = ""
    single_idea: str = ""
    #: The panel's median pull on the version that shipped.
    pull: float = 0.0
    #: Whether a majority of the panel would have clicked.
    landed: bool = False
    #: How many rewrites it took. Zero means the bake-off found the angle
    #: first time, which is the cheapest good outcome the system has.
    rewrites: int = 0
    #: True when the loop stopped because rewriting stopped helping, rather
    #: than because it ran out of attempts.
    rewrites_stopped_helping: bool = False
    #: Did a cold reader who knew nothing correctly name what it sells? The
    #: cheapest single signal of whether the copy communicates at all.
    what_it_sells: str = ""
    #: What stopped the hardest reader on the panel - the thing to fix next.
    biggest_doubt: str = ""
    #: Deterministic checks still failing on the delivered version.
    unresolved: list[str] = Field(default_factory=list)
    #: How long the body ran. Watched because every additive pressure in the
    #: system shows up here first.
    word_count: int = 0
    #: What the Strategist said this email is built on.
    evidence_assigned: list[str] = Field(default_factory=list)
    #: Of those, the ones whose figure, name or quotation actually reached the
    #: page - see app.marketing.substantiation. Checked in code on the version
    #: that shipped, so it is a measurement rather than an intention.
    evidence_spent: list[str] = Field(default_factory=list)
    #: Third-party entries the copy names or quotes.
    attributions: int = 0
    #: Distinct checkable values from the material that appear in the copy.
    specifics: int = 0


class RunRecord(BaseModel):
    """One golden-set case, run end to end."""

    case: str
    request: str
    preset: str
    run_status: str = ""
    at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    delivered: int = 0
    promised: int = 0
    emails: list[EmailRecord] = Field(default_factory=list)

    #: Whether the sequence held together when read as a sequence.
    sequence_passed: bool = True
    sequence_summary: str = ""

    #: Blind votes between this run's first email and one a person wrote for
    #: the same brief, judged by a panel and a model the loop does not optimise
    #: against. The only number in this record with a referent outside the
    #: system - everything else says whether a change helped, and this says
    #: whether the output is worth sending.
    control_votes_for: int = 0
    control_votes_against: int = 0
    control_note: str = ""
    control_reasons: list[str] = Field(default_factory=list)

    model_calls: int = 0
    calls_by_role: dict[str, int] = Field(default_factory=dict)
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    duration_seconds: float = 0.0
    #: Writer turns spent re-emitting a draft that broke the field protocol.
    repairs: int = 0

    @property
    def average_pull(self) -> float:
        scored = [email.pull for email in self.emails]
        return sum(scored) / len(scored) if scored else 0.0

    @property
    def landed_rate(self) -> float:
        if not self.emails:
            return 0.0
        return sum(1 for email in self.emails if email.landed) / len(self.emails)

    @property
    def first_draft_ship_rate(self) -> float:
        """How often the bake-off found the angle without a rewrite.

        The metric that separates "the system got better at writing" from
        "the system got better at rewriting". Rewrites are the expensive half
        and the one with diminishing returns; a change that raises this is
        worth more than the same quality bought three attempts in.
        """
        if not self.emails:
            return 0.0
        return sum(1 for email in self.emails if email.rewrites == 0) / len(self.emails)

    @property
    def substantiation_rate(self) -> float:
        """The share of emails that actually spent the proof they were built on.

        The one metric here that reads the *copy* against the *material*
        rather than against another model's opinion, which makes it the only
        line on this record that cannot be moved by a judge drifting. It is
        also the thing the architecture spends most of its money on: the
        crawl, the ledger, the quote verification and the per-email evidence
        assignment all exist to raise this number, and until it existed
        nothing said whether any of that reached the page.

        Emails the Strategist assigned nothing are not counted either way -
        there was nothing to spend, and scoring them would make the number
        depend on how the brief was written.
        """
        assigned = [email for email in self.emails if email.evidence_assigned]
        if not assigned:
            return 0.0
        return sum(1 for email in assigned if email.evidence_spent) / len(assigned)

    @property
    def attributed_rate(self) -> float:
        """The share of emails that name or quote somebody other than the
        company. Reported beside `substantiation_rate` rather than folded into
        it: spending a price is not the same act as citing a customer, and a
        run can move one without moving the other."""
        if not self.emails:
            return 0.0
        return sum(1 for email in self.emails if email.attributions > 0) / len(self.emails)

    @property
    def control_win_rate(self) -> float:
        """The share of blind votes the system's email took off the human's.

        Read it against 50%, not against 100%: the control is what a competent
        person sends, so drawing with it is already the system doing the job,
        and the number to move is the distance above the half.
        """
        cast = self.control_votes_for + self.control_votes_against
        return self.control_votes_for / cast if cast else 0.0

    @property
    def cost_per_shipped_email(self) -> float:
        """Cost per email a cold reader would actually have clicked.

        Emails below the floor are not free failures - they were paid for -
        so they count in the numerator and not the denominator. A run that
        delivers nothing anybody would click has no cost per shipped email,
        and reporting one would be the most flattering possible lie.
        """
        shipped = sum(1 for email in self.emails if email.landed)
        return self.cost_usd / shipped if shipped else float("inf")

    def summary(self) -> str:
        shipped = sum(1 for email in self.emails if email.landed)
        per_email = (
            f"${self.cost_per_shipped_email:.2f}" if shipped else "nothing shipped"
        )
        cast = self.control_votes_for + self.control_votes_against
        control = (
            f"vs. human {self.control_votes_for}-{self.control_votes_against} "
            f"({self.control_win_rate:.0%})"
            if cast
            else self.control_note or "no control"
        )
        return (
            f"{self.case} [{self.preset}] {self.run_status}: "
            f"{control}, "
            f"{self.delivered}/{self.promised} delivered, "
            f"{shipped} above the {PULL_THRESHOLD}/10 floor, "
            f"avg pull {self.average_pull:.1f}, "
            f"first-draft ships {self.first_draft_ship_rate:.0%}, "
            f"proof on the page {self.substantiation_rate:.0%}, "
            f"{self.model_calls} calls, {self.repairs} repair(s), "
            f"${self.cost_usd:.2f} total, {per_email}/shipped email, "
            f"{self.duration_seconds:.0f}s"
        )


def record_from(
    case: str,
    preset: str,
    result: CampaignRunResult,
    duration_seconds: float,
    repairs: int = 0,
    control: ControlResult | None = None,
) -> RunRecord:
    """Read one finished run into a comparable record."""
    calls_by_role: dict[str, int] = {}
    for call in result.usage.calls:
        calls_by_role[call.role] = calls_by_role.get(call.role, 0) + 1

    emails = [
        EmailRecord(
            position=outcome.brief.position,
            subject=outcome.email.subject,
            single_idea=outcome.brief.single_idea,
            pull=outcome.best.read.pull,
            landed=outcome.best.read.landed,
            rewrites=len(outcome.versions) - 1,
            rewrites_stopped_helping=outcome.stopped_early,
            what_it_sells=outcome.best.read.primary.what_it_sells,
            biggest_doubt=outcome.best.read.worst.biggest_doubt,
            unresolved=[issue.detail for issue in outcome.best.gates.blocking],
            word_count=len(outcome.email.body.split()),
            evidence_assigned=outcome.brief.evidence_ids,
            evidence_spent=list(outcome.best.substantiation.carried),
            attributions=outcome.best.substantiation.attributions,
            specifics=outcome.best.substantiation.specifics,
        )
        for outcome in result.outcomes
    ]
    return RunRecord(
        case=case,
        request=result.report.request,
        preset=preset,
        run_status=result.status,
        delivered=result.report.delivered,
        promised=result.report.promised,
        emails=emails,
        sequence_passed=result.sequence.passed if result.sequence else True,
        sequence_summary=result.sequence.verdict.summary if result.sequence else "",
        model_calls=len(result.usage.calls),
        calls_by_role=calls_by_role,
        input_tokens=result.usage.billable_input_tokens,
        output_tokens=result.usage.output_tokens,
        cost_usd=round(result.usage.cost_usd, 4),
        duration_seconds=round(duration_seconds, 1),
        repairs=repairs,
        control_votes_for=control.votes_for_system if control else 0,
        control_votes_against=control.votes_for_control if control else 0,
        control_note=control.skipped if control else "",
        control_reasons=list(control.reasons) if control else [],
    )
