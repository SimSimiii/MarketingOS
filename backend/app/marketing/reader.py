"""The Blind Reader: the one role in the system defined by what it is not given.

It never sees the request, the brief, the positioning, the product docs or the
intent. That is not an oversight to be fixed - it is the entire mechanism. Ask
a model that has read the brief "what is this email selling you?" and it
answers from the brief; the gaps in the copy get filled in from context that
no real recipient will ever have. Ask a model that has only the email, and the
answer means something.

This is also the template for when a role deserves to exist at all in this
architecture. Not "a marketing team has a proofreader" - an org chart is not
an information-flow argument. A role earns its own context when its ignorance
or its independence is load-bearing. This one's is.

Carried over almost unchanged from the old email agent, where it was the best
idea in the codebase and was buried as a private method of one specialist.
"""

import asyncio
import statistics

from pydantic import BaseModel, Field

from app.ai.model_router import ModelTier
from app.knowledge.artifacts import AudienceModel, Segment
from app.marketing.email_copy import Email, render_email
from app.runtime.exceptions import OutputValidationError
from app.runtime.model_session import ModelSession

ROLE_ID = "blind_reader"

#: What a draft has to make a cold reader feel to ship untouched. Below it the
#: copy earns a rewrite against the reader's own words.
#:
#: The number only means something because the reader's own scale says the same
#: thing at the same point - see prompts/reader.md, where 7 is where they say
#: they would click. A threshold and a rubric that disagree produce a floor
#: nothing can reach: the scale used to anchor 7 at "you would click if the
#: week were calmer" while `landed` also required "would click today", so a
#: self-consistent reader scoring exactly 7 had to answer no, and the real
#: floor was 8 that nobody had written down.
PULL_THRESHOLD = 7


class BlindRead(BaseModel):
    """What happened to a person who read the email and knew nothing else."""

    opened: bool = False
    stopped_at: str = ""
    what_it_sells: str = ""
    biggest_doubt: str = ""
    would_act: bool = False
    pull: int = Field(default=0, ge=0, le=10)
    fixes: list[str] = Field(default_factory=list)
    #: Which reader this was, when a panel read the same draft.
    persona: str = ""
    #: False when this reader never came back with anything - a malformed
    #: response, not a verdict. Kept as a flag rather than encoded as a score,
    #: because every score is a claim about the copy and this one would be a
    #: lie in whichever direction it was rounded.
    reported: bool = True

    @property
    def landed(self) -> bool:
        return self.reported and self.opened and self.would_act and self.pull >= PULL_THRESHOLD

    def render(self) -> str:
        lines = [
            f"- Would they have opened it? {'yes' if self.opened else 'no'}",
            f"- What they think it sells: {self.what_it_sells or 'they could not say'}",
            f"- Where they stopped reading: {self.stopped_at or 'they read to the end'}",
            f"- What would stop them clicking: {self.biggest_doubt or 'nothing they named'}",
            f"- Would they click today? {'yes' if self.would_act else 'no'}",
            f"- How much they wanted it: {self.pull}/10",
        ]
        if self.fixes:
            lines.append("- Lines they would cut or change: " + "; ".join(self.fixes))
        return "\n".join(lines)


class PanelRead(BaseModel):
    """Several cold readers on the same draft.

    Variance is the signal a single read cannot give: copy that one person
    loves and another cannot parse is not finished, and a single score would
    hide that. Every reader's report goes back to the writer in full - see
    `render` - so the rewrite answers the hardest one, not the average one.
    """

    reads: list[BlindRead] = Field(default_factory=list)

    @property
    def reported(self) -> list[BlindRead]:
        return [read for read in self.reads if read.reported]

    @property
    def has_verdict(self) -> bool:
        """Whether anybody actually read this. A draft nobody could report on
        is not a draft that scored zero, and the difference decides whether
        the number downstream means anything."""
        return bool(self.reported)

    @property
    def pull(self) -> float:
        """The panel's one number: the middle reader, not the average one.

        A mean hands one reader who scores everything low a permanent veto
        over the campaign's headline number - and, through
        `EmailVersion.score`, over which rewrite is kept. The median answers
        the question that decides whether copy ships, which is what the middle
        reader felt, and one outlier in either direction cannot move it. With
        a single reader the two are the same number.
        """
        return statistics.median(read.pull for read in self.reported) if self.reported else 0.0

    @property
    def landed(self) -> bool:
        """Whether the panel would click: more than half of the readers who
        reported back would have.

        Not unanimity. Giving every reader a veto sounds like a higher
        standard and is really an unreachable one - the loop then always
        exhausts its rewrites, and "we ran out of rewrites" reaches the user
        as if it were the copy's score. One holdout in three is what copy that
        works looks like; two is a draft with a real problem.
        """
        landed = sum(1 for read in self.reported if read.landed)
        return bool(self.reported) and landed * 2 > len(self.reported)

    @property
    def worst(self) -> BlindRead:
        """The hardest verdict anyone actually gave. A reader who never came
        back has no verdict, and must not be counted as the harshest one."""
        return min(self.reported, key=lambda read: read.pull, default=BlindRead())

    @property
    def primary(self) -> BlindRead:
        return self.reads[0] if self.reads else BlindRead()

    def verdict_line(self) -> str:
        """What the panel would do, in one phrase for a timeline row.

        Here rather than at each call site: the craft loop and the persistence
        observer each used to build this sentence from `primary` alone, which
        printed one reader's answer beside the whole panel's score.
        """
        reported = self.reported
        if not reported:
            return "nobody could read it"
        clicked = sum(1 for read in reported if read.would_act)
        if len(reported) == 1:
            return "they would click today" if clicked else "they would not click"
        return f"{clicked} of {len(reported)} would click today"

    def render(self) -> str:
        if len(self.reads) == 1:
            return self.reads[0].render()
        return "\n\n".join(
            f"Reader: {read.persona or 'unnamed'}\n{read.render()}" for read in self.reads
        )


class BlindReader:
    def __init__(self, session: ModelSession) -> None:
        self._session = session

    async def read(self, email: Email, personas: list[str]) -> PanelRead:
        """Every persona reads the same draft, at the same time.

        Concurrently because they are genuinely independent: no reader sees
        another's report, which is the whole point of a panel. Read in
        sequence, a three-person panel spent three model calls' worth of
        wall-clock on a step that costs the same either way - in a measured
        run, a bake-off read took nearly four minutes. `gather` preserves
        input order, so the panel's membership stays stable across a run.
        """
        chosen = personas or [_FALLBACK_PERSONA]
        reads = await asyncio.gather(
            *(self._read_once(email, persona) for persona in chosen)
        )
        return PanelRead(reads=list(reads))

    async def _read_once(self, email: Email, persona: str) -> BlindRead:
        # The reader's whole prompt is who they are and what arrived. Rendered
        # here rather than by the session's template path because the email
        # under review is part of the system prompt, not the task.
        system_prompt = self._session.render(
            "reader", {"reader_profile": persona, "email": render_email(email)}
        )
        try:
            read = await self._session.structured(
                role=ROLE_ID,
                tier=ModelTier.BALANCED,
                system_prompt=system_prompt,
                task="React now, as the person described above, reading this for the first time.",
                schema=BlindRead,
            )
        except OutputValidationError:
            # A reader who could not report is not a reason to throw away a
            # draft: it is no verdict, and the copy stands on the other
            # checks. What it must never become is a passing score - scoring
            # the failure at the threshold shipped drafts nobody had read,
            # and averaged a number nobody had given into the campaign's
            # headline result.
            return BlindRead(
                reported=False,
                persona=persona,
                what_it_sells="(the reader did not report)",
            )
        read.persona = persona
        return read


_FALLBACK_PERSONA = "a busy professional who has never heard of this company"


def personas_for(audience: AudienceModel, chosen: Segment | None, panel: bool) -> list[str]:
    """Who reads the draft cold.

    Never the brief's reader description - that sentence was written to help a
    writer and is full of intent. A cold reader is a person, described only as
    a person. But it must be the *right* person: `chosen` is the segment the
    Strategist decided this campaign is for, and reading the copy as anyone
    else measures the mismatch instead of the copy.

    A panel varies the reader's disposition, never their identity. Handing the
    same draft to two different segments looks like more coverage and is the
    opposite: a panel that spans segments can only be satisfied by copy vague
    enough to work on all of them, and the rewrite loop spends its budget
    sanding a specific email into a general one.

    The dispositions have to be about the *claim*, never about the medium. A
    reader defined as skeptical of cold email is answering a question no
    rewrite can move - they reject the envelope, and their score is a constant
    that only ever drags the panel down and vetoes every draft in the run. A
    reader who has been sold this exact promise before is the same person in a
    harder mood, and copy can answer them.
    """
    segment = chosen or audience.primary()
    person = (
        f"{segment.name}. {segment.situation}".strip(". ")
        if segment is not None and segment.name
        else _FALLBACK_PERSONA
    )
    if not panel:
        return [person]
    # The variants are dispositions the same person turns up in. The hard one
    # is added rather than found: an audience model describes people who might
    # buy, and the reader who nearly would not is the one whose objection the
    # copy has to survive.
    return [
        person,
        f"{person} - and they already use something that mostly works",
        (
            f"{person} - and they have been promised exactly this before by a product "
            "that did not deliver"
        ),
    ]
