"""The Conversion Critic: what the reader felt, turned into what to change.

The blind reader reports behavior - they stopped here, they could not say what
it sells, they would not click today. That is evidence, not instruction.
Somebody has to decide what to do about it, and it cannot be the writer: the
writer knows what it meant, and reads its own draft as if the meaning were on
the page.

So the critic is a separate role with a separate context: the brief, the
ledger, the reader's report and the gate results, but not the writer's
reasoning and not its earlier attempts. Its independence is why it can see
brief drift - an email that reads beautifully and argues the wrong thing - and
unspent evidence, both of which are invisible from inside the draft.

It replaces the old outer review agent, which scored a truncated JSON digest
of the whole campaign against a rubric that half-duplicated the free
mechanical checks. This one reads one rendered email and names lines.
"""

from typing import Literal

from pydantic import BaseModel, Field

from app.ai.model_router import ModelTier
from app.knowledge.artifacts import KnowledgeArtifacts
from app.marketing.briefs import CampaignBrief, EmailBrief
from app.marketing.email_copy import Email, render_email
from app.marketing.gates import GateReport
from app.marketing.reader import PanelRead
from app.marketing.substantiation import Substantiation
from app.runtime.model_session import ModelSession

ROLE_ID = "conversion_critic"

#: How many non-blocking edits reach the writer in one pass.
#:
#: Not a limit on what the critic may notice - everything it found is recorded
#: and shown to the user. It is a limit on what one rewrite is asked to do.
#: Handed ten edits, a writer does not revise, it rewrites: the draft that
#: comes back is a different email, which draws a different ten edits, and the
#: loop spends its whole budget replacing drafts instead of improving one. The
#: edits are ranked most damaging first, so the top few are the ones worth the
#: turn, and whatever still matters will be found again on the next read.
MAX_EDITS_PER_PASS = 3


class Edit(BaseModel):
    """One thing to change, anchored to the line it is about."""

    #: Quoted from the email, so the writer cannot mistake which line.
    line: str = ""
    problem: str = ""
    #: What the fix must achieve - never the replacement copy. The critic
    #: diagnosing and the writer prescribing is how a draft keeps one voice.
    fix: str = ""
    severity: Literal["blocking", "major", "minor"] = "major"

    def render(self) -> str:
        anchor = f'"{self.line}" - ' if self.line else ""
        return f"({self.severity}) {anchor}{self.problem} → {self.fix}"


class Critique(BaseModel):
    verdict: Literal["ship", "revise"] = "revise"
    #: Where the draft executes something other than its brief. The failure
    #: that is invisible from inside the copy.
    brief_drift: str = ""
    #: Evidence this email was given and did not use.
    unspent_evidence: list[str] = Field(default_factory=list)
    edits: list[Edit] = Field(default_factory=list)
    summary: str = ""

    @property
    def blocking(self) -> list[Edit]:
        return [edit for edit in self.edits if edit.severity == "blocking"]

    @property
    def for_this_pass(self) -> list[Edit]:
        """The edits one rewrite is actually asked to make.

        Everything blocking, because a blocking edit is why the email cannot
        ship, plus the most damaging of the rest up to `MAX_EDITS_PER_PASS`.
        Order is the critic's own ranking, preserved.
        """
        room = MAX_EDITS_PER_PASS - len(self.blocking)
        kept: list[Edit] = []
        for edit in self.edits:
            if edit.severity == "blocking":
                kept.append(edit)
            elif room > 0:
                kept.append(edit)
                room -= 1
        return kept

    def render(self) -> str:
        parts: list[str] = []
        if self.brief_drift:
            parts.append(f"Brief drift: {self.brief_drift}")
        if self.unspent_evidence:
            parts.append(f"Evidence assigned but unused: {', '.join(self.unspent_evidence)}")
        shown = self.for_this_pass
        if shown:
            parts.append("\n".join(f"- {edit.render()}" for edit in shown))
        held_back = len(self.edits) - len(shown)
        if held_back:
            parts.append(
                f"({held_back} smaller note(s) held back - fix the ones above first. A rewrite "
                "that tries to answer every note at once comes back as a different email.)"
            )
        if self.summary:
            parts.append(self.summary)
        return "\n".join(parts) or "No changes requested."


class ConversionCritic:
    def __init__(self, session: ModelSession) -> None:
        self._session = session

    async def critique(
        self,
        *,
        email: Email,
        brief: EmailBrief,
        campaign: CampaignBrief,
        artifacts: KnowledgeArtifacts,
        read: PanelRead,
        gates: GateReport,
        substantiation: Substantiation | None = None,
    ) -> Critique:
        return await self._session.structured(
            role=ROLE_ID,
            tier=ModelTier.DEEP,
            template="critic",
            variables={
                "email": render_email(email),
                "brief": brief.render(),
                "reader": campaign.reader,
                "promise": campaign.promise,
                # The same slice the writer wrote from. The critic's job here
                # is to notice evidence this email needed and did not spend -
                # and against the full ledger of a real business that question
                # has a hundred answers, every one of them a reason to add
                # another sentence. It is the additive ratchet with a budget
                # line attached.
                "evidence": artifacts.evidence.slice_for(
                    brief.evidence_ids, brief.objection
                ).render(),
                "voice": artifacts.voice.render(),
                "reader_report": read.render(),
                "gate_report": gates.render(),
                # Which assigned facts are absent from the page is a string
                # comparison, and it is already done - see
                # app.marketing.substantiation. Handing the critic the answer
                # rather than the question is the same trade the rest of the
                # system makes everywhere else: a model asked to re-derive a
                # lookup answers it approximately, and spends the attention it
                # owed to brief drift doing it. What is left for the critic is
                # the part that is judgment - whether this email's argument
                # actually needed the fact it left out.
                "unspent_evidence": _unspent(substantiation),
            },
            task=(
                "Decide whether this email ships as it stands, and if not, name the lines that "
                "have to change and what each change has to achieve."
            ),
            schema=Critique,
        )


def _unspent(substantiation: Substantiation | None) -> str:
    if substantiation is None or not substantiation.unspent:
        return (
            "Every fact this email was assigned is on the page (or it was assigned none). "
            "There is nothing to add back."
        )
    listing = "\n".join(
        f"- [{entry.id}] {entry.claim}" for entry in substantiation.unspent
    )
    return (
        "These were assigned to this email and no trace of them reached the page - not the "
        f"figure, not the name, not the quotation:\n{listing}"
    )
