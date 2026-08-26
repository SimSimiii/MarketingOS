"""Which of two drafts a reader would actually act on, asked as a choice.

Every judgment in this system used to be an absolute score: a reader was handed
one email and asked how much they wanted the thing, out of ten. That question
is the one a model answers worst. It has no unit, no reference point and no way
to be wrong, so the answer drifts with the phrasing of the prompt and clusters
wherever the persona's disposition puts it - and two drafts a page apart in
quality come back a tenth of a point apart, or the same.

A choice between two concrete things has none of those problems. The reader is
not asked to locate a draft on a scale nobody defined; they are asked which of
two emails in front of them gets the click, which is the question a real inbox
actually poses. It is also the question the whole system exists to answer:
"better" is a comparison, and a comparison is what a bake-off, a rewrite and a
benchmark against a human copywriter all need.

Two things make the answer mean something:

**Position is cancelled, not trusted.** A model shown two options prefers one
of the slots regardless of what is in them. So every duel is run an even number
of times with the labels swapped, and a preference that only exists in one
direction shows up as the tie it is.

**The incumbent wins ties.** A challenger has to be preferred, not merely not
disliked. This is the same rule as `better_of` in the craft loop, for the same
reason: a rewrite that did not measurably improve anything is a rewrite that
sanded the edges off a draft that already worked.
"""

import asyncio
import logging
from dataclasses import dataclass

from pydantic import BaseModel

from app.ai.model_router import ModelTier
from app.marketing.email_copy import Email, render_email
from app.runtime.exceptions import ModelRuntimeError
from app.runtime.model_session import ModelSession

logger = logging.getLogger("marketingos.marketing")

ROLE_ID = "preference_judge"

#: The fewest comparisons a duel is worth running. Two, because one of each
#: label order is what makes the result a preference between the emails rather
#: than a preference for the letter A.
_MIN_VOTES = 2


class Vote(BaseModel):
    """One reader, shown two emails, choosing between them."""

    #: Which of the two labels they picked, as they saw them.
    winner: str = "A"
    #: Why, in their words. Collected because the reason a reader preferred a
    #: draft is the only part of a duel a writer can act on.
    why: str = ""
    #: How much in it there was. A run of `toss-up` verdicts means the two
    #: drafts are the same bet with different words, which is a fact about the
    #: bake-off rather than about either draft.
    margin: str = "clear"
    reported: bool = True


@dataclass(frozen=True)
class Duel:
    """Every vote cast between one pair of drafts, and what it settled."""

    challenger_votes: int
    champion_votes: int
    reasons: tuple[str, ...] = ()
    #: Votes that never came back. A duel nobody could judge decides nothing,
    #: and must not read as a tie the incumbent then wins on a technicality.
    unreported: int = 0

    @property
    def cast(self) -> int:
        return self.challenger_votes + self.champion_votes

    @property
    def decided(self) -> bool:
        return self.cast > 0

    @property
    def challenger_wins(self) -> bool:
        """Strictly preferred, or it does not take the title."""
        return self.challenger_votes > self.champion_votes

    def render(self) -> str:
        if not self.decided:
            return "nobody could choose between them"
        head = f"{self.challenger_votes}-{self.champion_votes}"
        if self.challenger_votes == self.champion_votes:
            return f"{head}, a tie - the version that already worked stands"
        who = "the new version" if self.challenger_wins else "the version already chosen"
        return f"{head} to {who}" + (f" - {self.reasons[0]}" if self.reasons else "")


class PreferenceJudge:
    """Runs duels between drafts, for the people the copy is aimed at."""

    def __init__(self, session: ModelSession) -> None:
        self._session = session

    async def duel(
        self,
        *,
        challenger: Email,
        champion: Email,
        personas: list[str],
        votes: int | None = None,
    ) -> Duel:
        """Ask each reader which of the two they would act on.

        Concurrently, and with the label order alternating across the ballot:
        the readers are independent, and the pairing that matters is (persona,
        which email was shown first), not persona alone.
        """
        ballot = _ballot(personas, votes)
        results = await asyncio.gather(
            *(
                self._one_vote(challenger, champion, persona, swapped)
                for persona, swapped in ballot
            )
        )
        for_challenger = sum(1 for vote, swapped in results if _picked_challenger(vote, swapped))
        for_champion = sum(
            1
            for vote, swapped in results
            if vote.reported and not _picked_challenger(vote, swapped)
        )
        return Duel(
            challenger_votes=for_challenger,
            champion_votes=for_champion,
            reasons=tuple(vote.why for vote, _ in results if vote.reported and vote.why),
            unreported=sum(1 for vote, _ in results if not vote.reported),
        )

    # ------------------------------------------------------------- internals

    async def _one_vote(
        self, challenger: Email, champion: Email, persona: str, swapped: bool
    ) -> tuple[Vote, bool]:
        # `swapped` says which email wore which label, and it is returned
        # alongside the vote rather than undone here: a caller that reads
        # "winner: A" without knowing what A was is reading a coin flip.
        first, second = (champion, challenger) if swapped else (challenger, champion)
        system_prompt = self._session.render(
            "duel",
            {
                "reader_profile": persona,
                "email_a": render_email(first),
                "email_b": render_email(second),
            },
        )
        try:
            vote = await self._session.structured(
                role=ROLE_ID,
                tier=ModelTier.BALANCED,
                system_prompt=system_prompt,
                task="Pick the one you would act on, as the person described above.",
                schema=Vote,
            )
        except ModelRuntimeError as exc:
            # Any runtime failure, not only a malformed ballot. The votes are
            # cast concurrently, so a transport failure on one of them used to
            # escape `gather` and end the run - and `Duel` already models a
            # vote that never came back, counts it in neither column, and
            # leaves the incumbent standing when nothing decided.
            logger.info("tournament: a vote did not come back - %s", exc)
            return Vote(reported=False), swapped
        return vote, swapped


def _picked_challenger(vote: Vote, swapped: bool) -> bool:
    if not vote.reported:
        return False
    chose_a = vote.winner.strip().upper().startswith("A")
    # A is the challenger unless the labels were swapped for this ballot line.
    return chose_a is not swapped


def _ballot(personas: list[str], votes: int | None) -> list[tuple[str, bool]]:
    """Who votes, and in which order they see the two emails.

    Rounded up to an even number so the label orders divide exactly. An odd
    ballot cannot tie, which sounds like an advantage and is really a
    guaranteed winner produced by whichever order got the extra vote.
    """
    people = personas or [_FALLBACK_PERSONA]
    wanted = max(_MIN_VOTES, votes if votes is not None else len(people))
    wanted += wanted % 2
    return [(people[index % len(people)], bool(index % 2)) for index in range(wanted)]


_FALLBACK_PERSONA = "a busy professional who has never heard of this company"
