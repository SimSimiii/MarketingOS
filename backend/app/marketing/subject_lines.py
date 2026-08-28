"""The eight words that decide whether any of the others are read.

Conversion is a product, not a sum: opened, then read, then clicked. The system
spent its whole budget on the second and third terms and nothing at all on the
first. A subject line arrived as a by-product of whichever draft won the
bake-off, was scored only as part of the email underneath it, and was never
compared against an alternative - so the highest-leverage sentence in the
deliverable was the one sentence nothing in the loop was trying to improve.

That is also why it is cheap to fix. A subject can be tested against the
decision it actually faces - a person looking at a sender, a line of text and a
preview, deciding in a quarter of a second - and that decision needs none of
the email underneath it. Writing eight alternatives costs one writer turn, and
judging them costs one reaction per reader, because they are judged together:
"which of these five would you tap" is a comparison, and a comparison is the
question a reader answers reliably. See tournament.py, which is the same
argument about whole emails.

The body is not touched. What comes out is the same email with the line most of
a hundred people would open, or the original if none of the alternatives beat
it - the incumbent wins ties here for the same reason it does everywhere else.
"""

import asyncio
import logging
import statistics
from collections.abc import Callable

from pydantic import BaseModel, Field

from app.ai.model_router import ModelTier
from app.knowledge.artifacts import KnowledgeArtifacts
from app.marketing.briefs import EmailBrief
from app.marketing.email_copy import (
    MAX_PREVIEW_CHARS,
    MAX_SUBJECT_CHARS,
    Email,
    normalized,
)
from app.runtime.exceptions import ModelRuntimeError
from app.runtime.model_session import ModelSession

logger = logging.getLogger("marketingos.marketing")

WRITER_ROLE_ID = "subject_writer"
SCANNER_ROLE_ID = "inbox_scanner"


class SubjectOption(BaseModel):
    """One subject line and the preview text that extends it."""

    subject: str = ""
    preview: str = ""
    #: What this line is betting on - "names the cost", "asks the question they
    #: are already asking". Kept because it is what a person reading the run
    #: log learns from, and what stops four options being one line reworded.
    approach: str = ""

    @property
    def sendable(self) -> bool:
        """Checked here rather than by asking for a rewrite: length is
        arithmetic, and an option that fails it is dropped for free while the
        others are still worth judging."""
        return bool(
            self.subject
            and self.preview
            and len(self.subject) <= MAX_SUBJECT_CHARS
            and len(self.preview) <= MAX_PREVIEW_CHARS
            and normalized(self.subject) != normalized(self.preview)
        )

    def render(self, label: int) -> str:
        return f"{label}. Subject: {self.subject}\n   Preview: {self.preview}"


class SubjectSet(BaseModel):
    options: list[SubjectOption] = Field(default_factory=list)


class OptionScore(BaseModel):
    """One reader on one line: how many of a hundred people tap it."""

    #: The number the option was listed under. Matched back by position, and
    #: anything that does not name a listed option is dropped.
    option: int = 0
    opens_in_100: int = Field(default=0, ge=0, le=100)
    why: str = ""


class InboxVerdict(BaseModel):
    scores: list[OptionScore] = Field(default_factory=list)
    reported: bool = True


def _swapped(email: Email, option: SubjectOption) -> Email:
    """The email this option would produce. The body is never touched - the
    reading already on the record still describes what ships."""
    return email.model_copy(
        update={"subject": option.subject, "preview_text": option.preview}
    )


class SubjectBakeOff:
    """Writes alternative subject lines for a finished email and picks one."""

    def __init__(self, session: ModelSession) -> None:
        self._session = session

    async def improve(
        self,
        *,
        email: Email,
        brief: EmailBrief,
        artifacts: KnowledgeArtifacts,
        personas: list[str],
        variants: int,
        screen: Callable[[Email], bool] | None = None,
    ) -> tuple[Email, str]:
        """The same email, with the subject most people would open.

        Returns the email and one line saying what happened, which the caller
        announces. A no-op - no alternatives, none sendable, none preferred -
        returns the email it was given, unchanged and undamaged.

        `screen` is the free checks, pointed at the email each option would
        produce. Everything else in this loop screens before it pays - the
        gates run before a cold read, near-identical candidates are dropped
        before the bake-off reads them - and this step did not: an option that
        repeated an earlier email's subject word for word, or carried a figure
        the ledger does not license, was written, scanned at full price, could
        win the field, and was then thrown away by the caller's re-check. The
        run kept the line it started with even when a clean alternative had
        scanned better than it. Screened here, the field the readers rank is
        the field the winner can actually be taken from.
        """
        options = await self._write(email, brief, artifacts, variants)
        sendable = [option for option in options if option.sendable]
        clean = [option for option in sendable if screen is None or screen(_swapped(email, option))]
        dropped = len(sendable) - len(clean)
        if not clean:
            return email, (
                f"no alternative subject line survived the automatic checks ({dropped} dropped)"
                if dropped
                else "no alternative subject line came back sendable"
            )

        # The line the email already has, judged on the same terms as the
        # alternatives. Without it in the running the bake-off can only replace
        # the subject, never keep it, and a set of four weak alternatives would
        # evict a strong incumbent every time. Never screened: it is what ships
        # if nothing beats it, and it has already been through these checks as
        # part of the draft that won.
        incumbent = SubjectOption(
            subject=email.subject, preview=email.preview_text, approach="the line it already had"
        )
        field = [incumbent, *clean]
        opens = await self.rank(field, artifacts.business.company_name, personas)
        if not opens:
            return email, "nobody could judge the subject lines"

        best = max(range(len(field)), key=lambda index: (opens[index], -index))
        summary = (
            "subject lines scored "
            + ", ".join(f"{opens[index]:.0f}/100" for index in range(len(field)))
            + (
                f" ({dropped} more broke an automatic check and was never read)"
                if dropped
                else ""
            )
            + f' - kept "{field[best].subject}"'
        )
        if best == 0:
            return email, summary
        return _swapped(email, field[best]), summary

    # ------------------------------------------------------------- internals

    async def _write(
        self,
        email: Email,
        brief: EmailBrief,
        artifacts: KnowledgeArtifacts,
        variants: int,
    ) -> list[SubjectOption]:
        try:
            written = await self._session.structured(
                role=WRITER_ROLE_ID,
                tier=ModelTier.DEEP,
                template="subject_lines",
                variables={
                    "body": email.body,
                    "current_subject": email.subject,
                    "current_preview": email.preview_text,
                    "single_idea": brief.single_idea or brief.job,
                    "objection": brief.objection or "none assigned",
                    "subject_strategy": brief.subject_strategy or "concrete, no clickbait",
                    "voice": artifacts.voice.render(),
                },
                task=(
                    f"Write {variants} subject lines for the email below, each betting on a "
                    "different thing."
                ),
                schema=SubjectSet,
            )
        except ModelRuntimeError as exc:
            # Polishing the subject is the last thing that happens to an email
            # and the most optional: the body is already judged and shipping.
            # Losing it to a blip is a slightly worse subject line; losing the
            # run to one is the whole campaign.
            logger.info(
                "subject: no alternatives came back for email %d - %s", email.position, exc
            )
            return []
        return written.options[:variants]

    async def rank(
        self, field: list[SubjectOption], sender: str, personas: list[str]
    ) -> list[float]:
        """Every reader ranks the whole field in one turn.

        One call per reader rather than one per line: the open decision is made
        by comparison - a subject is tapped or skipped relative to what sits
        above and below it - and asking about one line in isolation is asking a
        question the inbox never poses.

        Public because this is the instrument that makes the open decision,
        and the craft loop is not the only thing that needs to ask it: the
        judge bench does too, for the one damaged pair whose two emails are
        identical below the subject line.
        """
        listing = "\n".join(option.render(index + 1) for index, option in enumerate(field))
        sender = sender or "a company you have not heard of"
        verdicts = await asyncio.gather(
            *(self._scan_once(listing, sender, persona) for persona in personas or [""])
        )
        by_option: list[list[int]] = [[] for _ in field]
        for verdict in verdicts:
            if not verdict.reported:
                continue
            for score in verdict.scores:
                if 1 <= score.option <= len(field):
                    by_option[score.option - 1].append(score.opens_in_100)
        if not any(by_option):
            return []
        return [statistics.median(scores) if scores else 0.0 for scores in by_option]

    async def _scan_once(self, listing: str, sender: str, persona: str) -> InboxVerdict:
        system_prompt = self._session.render(
            "inbox", {"reader_profile": persona, "sender": sender, "options": listing}
        )
        try:
            return await self._session.structured(
                role=SCANNER_ROLE_ID,
                tier=ModelTier.BALANCED,
                system_prompt=system_prompt,
                task="Say how many of a hundred people like you would tap each one.",
                schema=InboxVerdict,
            )
        except ModelRuntimeError:
            return InboxVerdict(reported=False)
