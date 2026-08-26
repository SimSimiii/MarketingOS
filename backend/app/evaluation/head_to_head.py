"""The system's email against one a person wrote, with the labels hidden.

Every other number in this package compares a run to an earlier run. That is
the right way to tell whether a change helped and it cannot answer the only
question anybody actually has, which is whether the output is any good: two
versions of a system can improve on each other for a year and both stay worse
than what a competent freelancer sends on a Tuesday. A control email is the one
measurement here with an outside referent.

Three things keep the answer honest, and each of them exists because the
obvious version of this test is worthless without it.

**It is a choice, not two scores.** The same argument as tournament.py: asking
a model to rate two emails out of ten and subtracting produces a difference
smaller than the noise. Asking which one gets the click produces a number that
moves.

**The grader is not the instrument the loop was tuned on.** The craft loop
optimises against a cold reader on the balanced tier, so grading with that
exact reader measures how well the run pleased its own judge. This runs on a
different model, with dispositions the loop never uses. Beating a judge you
trained against is not evidence; beating one you did not is.

**Ties are not wins.** A win rate counts votes for the system, and a draft that
merely holds its own against a person shows up as the 50% it is.
"""

from dataclasses import dataclass

from app.knowledge.artifacts import KnowledgeArtifacts
from app.marketing.email_copy import Email, EmailCopyError, parse_email
from app.marketing.tournament import PreferenceJudge
from app.runtime.model_session import ModelSession

#: Votes cast on one pairing. Six because the ballot is split evenly between
#: label orders and across three readers, and because a win rate off two votes
#: is a coin toss with a percentage sign on it.
VOTES = 6

#: The model that decides the benchmark. Deliberately not the one the loop's
#: readers run on - see the module docstring. It is a handful of calls per
#: case, so the strongest model is affordable here in a way it is not inside a
#: rewrite loop.
JUDGE_MODEL = "opus"


@dataclass(frozen=True)
class ControlResult:
    """How the delivered email did against the human-written one."""

    votes_for_system: int = 0
    votes_for_control: int = 0
    reasons: tuple[str, ...] = ()
    #: Set when there is no control for this case, or nothing was delivered to
    #: compare. Distinct from a 0-6 loss, which is a result.
    skipped: str = ""

    @property
    def cast(self) -> int:
        return self.votes_for_system + self.votes_for_control

    @property
    def win_rate(self) -> float:
        return self.votes_for_system / self.cast if self.cast else 0.0

    @property
    def beat_the_human(self) -> bool:
        return self.votes_for_system > self.votes_for_control

    def render(self) -> str:
        if self.skipped:
            return f"vs. human control: {self.skipped}"
        if not self.cast:
            return "vs. human control: nobody could choose"
        verdict = "beats it" if self.beat_the_human else (
            "level with it" if self.votes_for_system == self.votes_for_control else "loses to it"
        )
        return (
            f"vs. human control: {self.votes_for_system}-{self.votes_for_control} "
            f"({self.win_rate:.0%}), {verdict}"
        )


def assessor_panel(artifacts: KnowledgeArtifacts, segment_name: str) -> list[str]:
    """Who grades the benchmark.

    The same buyer the campaign was written for - grading copy as somebody it
    was not aimed at measures the mismatch - in three dispositions the craft
    loop never puts in front of a draft. The hostile one is allowed here and
    banned there for a reason worth stating: inside the loop a reader who
    rejects cold email outright is a constant that vetoes every draft and moves
    no rewrite, while in a comparison both emails face the same hostility, so
    it stops being a veto and starts being a discriminator.
    """
    segment = artifacts.audience.match(segment_name, "") or artifacts.audience.primary()
    person = (
        f"{segment.name}. {segment.situation}".strip(". ")
        if segment is not None and segment.name
        else "a busy professional who has never heard of this company"
    )
    return [
        f"{person} - and they get a dozen cold emails like this every week",
        f"{person} - and the last tool they bought like this went unused",
        f"{person} - and they are the person who would have to explain the spend",
    ]


async def against_control(
    *,
    judge_session: ModelSession,
    control_email: str,
    delivered: list[Email],
    artifacts: KnowledgeArtifacts | None,
    segment_name: str = "",
) -> ControlResult:
    """One duel: the campaign's first email against the human-written one.

    The first email and not the whole sequence, because the control is one
    email written to one brief and a sequence has no single thing to compare
    against it. In a run of three, email 1 is the one that has to earn the
    other two anyway.
    """
    if not control_email.strip():
        return ControlResult(skipped="no control written for this case")
    if not delivered:
        return ControlResult(skipped="the run delivered nothing to compare")
    try:
        control = parse_email(control_email, position=1)
    except EmailCopyError as exc:
        return ControlResult(skipped=f"the control email is not sendable ({exc})")
    if artifacts is None:
        return ControlResult(skipped="the run compiled no knowledge to pick a reader from")

    duel = await PreferenceJudge(judge_session).duel(
        challenger=delivered[0],
        champion=control,
        personas=assessor_panel(artifacts, segment_name),
        votes=VOTES,
    )
    return ControlResult(
        votes_for_system=duel.challenger_votes,
        votes_for_control=duel.champion_votes,
        reasons=duel.reasons,
    )
