"""The sequence pass: judging the emails as a sequence, once they all exist.

Every email in the craft loop is judged alone, and alone is not how anyone
receives them. Five emails that are individually strong can still open the
same way twice, spend the same proof twice, or fail to escalate at all - and
none of that is visible from inside any one of them.

Two checks, in the order of what they cost. First the deterministic one:
repeated phrases, repeated opening moves and repeated subjects, found by
string comparison across the finished set. The old system's writing prompts
asked for exactly this ("never reuse an angle, a proof, an opening move") and
nothing ever verified it. Then the judgment one: a single strong-model read of
the whole sequence in order, against the arc it was supposed to have.
"""

import logging

from pydantic import BaseModel, Field

from app.ai.model_router import ModelTier
from app.marketing.briefs import CampaignBrief
from app.marketing.email_copy import Email, render_email
from app.marketing.gates import GateReport, overlap_gate
from app.runtime.model_session import ModelSession

logger = logging.getLogger("marketingos.marketing")

ROLE_ID = "sequence_reviewer"


class SequenceNote(BaseModel):
    """One thing wrong with the sequence, attached to the email that must fix it."""

    position: int = 1
    problem: str = ""
    fix: str = ""

    def render(self) -> str:
        return f"{self.problem} → {self.fix}"


class SequenceVerdict(BaseModel):
    escalates: bool = True
    promise_is_consistent: bool = True
    each_stands_alone: bool = True
    notes: list[SequenceNote] = Field(default_factory=list)
    summary: str = ""

    @property
    def passed(self) -> bool:
        return (
            self.escalates
            and self.promise_is_consistent
            and self.each_stands_alone
            and not self.notes
        )


class SequenceReport(BaseModel):
    """Everything wrong with the set, per email, ready to route back."""

    verdict: SequenceVerdict = Field(default_factory=SequenceVerdict)
    #: position -> the instructions that email's rework has to satisfy.
    rework: dict[int, list[str]] = Field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return not self.rework

    def instruction_for(self, position: int) -> str:
        return "\n".join(f"- {item}" for item in self.rework.get(position, []))

    def render(self) -> str:
        if self.passed:
            return f"The sequence holds together. {self.verdict.summary}".strip()
        lines = [f"Email {position}: {'; '.join(items)}" for position, items in sorted(self.rework.items())]
        return "\n".join(lines)


def cross_check(emails: list[Email]) -> dict[int, list[str]]:
    """Repetition across the finished set, found without a model.

    Each email is compared against every other one rather than only against
    the ones before it: by the time all five exist, "email 2 and email 4 open
    identically" is one fact, and it is cheaper to fix in the later of the two.
    """
    problems: dict[int, list[str]] = {}
    ordered = sorted(emails, key=lambda email: email.position)
    for index, email in enumerate(ordered):
        report: GateReport = overlap_gate(email, ordered[:index])
        if report.issues:
            problems[email.position] = [issue.detail for issue in report.issues]
    return problems


class SequenceReviewer:
    def __init__(self, session: ModelSession) -> None:
        self._session = session

    async def review(
        self, emails: list[Email], campaign: CampaignBrief, arc_read: bool = True
    ) -> SequenceReport:
        rework = cross_check(emails)
        if rework:
            logger.info("sequence: mechanical checks flagged %s", sorted(rework))

        verdict = SequenceVerdict()
        if arc_read and len(emails) > 1:
            verdict = await self._arc_read(emails, campaign)
            for note in verdict.notes:
                rework.setdefault(note.position, []).append(note.render())

        return SequenceReport(verdict=verdict, rework=rework)

    async def _arc_read(self, emails: list[Email], campaign: CampaignBrief) -> SequenceVerdict:
        rendered = "\n\n".join(
            f"===== EMAIL {email.position} =====\n{render_email(email)}"
            for email in sorted(emails, key=lambda item: item.position)
        )
        return await self._session.structured(
            role=ROLE_ID,
            tier=ModelTier.DEEP,
            template="sequence",
            variables={
                "sequence": rendered,
                "arc": campaign.arc or "not stated",
                "promise": campaign.promise or "not stated",
                "reader": campaign.reader or "not stated",
                "plan": campaign.render_arc(),
            },
            task=(
                "Read these in order, as one person receiving them over days, and judge them as "
                "a sequence rather than as individual emails."
            ),
            schema=SequenceVerdict,
        )
