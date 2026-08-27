"""What changed in the market since we last looked.

This is the part that makes the difference between a tool and a subscription,
and the reasoning is worth stating plainly because it decided the shape of the
code.

Generating an email is an event. A user needs it, buys it, gets it, and has no
reason to come back until the next campaign - which for most small companies is
next quarter. Nothing about doing that job *better* changes the shape of that
relationship; it only makes the one purchase more satisfying.

Positioning, on the other hand, decays. The claim a company owned in March is
claimed by four competitors in September, and nobody tells them. The free tier
they beat on gets matched. A competitor starts naming customers. Every one of
those quietly makes the copy that is already written worse, and none of them
are visible from inside the company's own material.

So the market is re-read on a schedule, and the *diff* is the product. A user
with no campaign to write still has a reason to open this, and the thing they
open it for is the one thing they cannot get anywhere else.

The diffing is deterministic and free. Comparing two snapshots is set
arithmetic over claims that were already extracted and quote-checked, and a
model asked "what changed?" would re-derive it stochastically and occasionally
invent a change - which, in the one feature whose entire value is being
trustworthy about what moved, is the only unacceptable failure.
"""

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from app.market.claims import Claim, ClaimAxis, overlap
from app.market.positioning import PositioningMap, Territory
from app.market.rivals import RivalProfile


class RadarSeverity(StrEnum):
    """How much a change should interrupt somebody.

    Three levels, and the top one is rare on purpose. A feed where everything
    is urgent is a feed nobody reads, and the whole point of this is to be
    worth opening.
    """

    #: Something that makes copy already written worse. The user should know
    #: this week.
    ACTS_ON_COPY = "acts_on_copy"
    #: A real move in the market, no immediate consequence for the copy.
    NOTABLE = "notable"
    #: Recorded so the history is complete. Not worth an interruption.
    ROUTINE = "routine"


class RadarEvent(BaseModel):
    """One thing that changed, in terms of what it costs."""

    headline: str
    detail: str = ""
    severity: RadarSeverity = RadarSeverity.ROUTINE
    #: The competitor this is about, where it is about one.
    rival: str = ""
    axis: ClaimAxis | None = None
    #: What the user should do, where there is something to do. Empty is an
    #: honest answer and better than inventing an action for a change that
    #: does not need one.
    what_to_do: str = ""
    at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def render(self) -> str:
        return f"[{self.severity}] {self.headline}" + (f" - {self.detail}" if self.detail else "")


class MarketSnapshot(BaseModel):
    """The field as it was at one moment, and where we stood in it."""

    rivals: list[RivalProfile] = Field(default_factory=list)
    positioning: PositioningMap = Field(default_factory=PositioningMap)
    taken_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def by_name(self) -> dict[str, RivalProfile]:
        return {rival.name.strip().lower(): rival for rival in self.rivals}


#: How different two promises have to be before the change is worth reporting.
#: A company that reworded its home page has not repositioned, and a feed that
#: says it has is a feed that cries wolf.
_PROMISE_CHANGED_BELOW = 0.45


def diff(previous: MarketSnapshot, current: MarketSnapshot) -> list[RadarEvent]:
    """Everything that moved between two readings of the same market.

    Ordered by what it costs the user, not by when it was found.
    """
    events: list[RadarEvent] = []
    before, after = previous.by_name(), current.by_name()

    events.extend(_territory_events(previous.positioning, current.positioning))
    events.extend(_proof_events(previous, current))

    for name, rival in after.items():
        if name not in before:
            events.append(
                RadarEvent(
                    headline=f"{rival.name} is new in this market",
                    detail=rival.promise or rival.one_liner,
                    severity=RadarSeverity.NOTABLE,
                    rival=rival.name,
                    what_to_do=(
                        "Read what they promise. If it is what you promise, the claim you "
                        "lead on has just got more crowded."
                    ),
                )
            )
            continue
        events.extend(_rival_events(before[name], rival))

    for name, rival in before.items():
        if name not in after:
            events.append(
                RadarEvent(
                    headline=f"{rival.name} could not be read this time",
                    detail="their site did not answer, or they are no longer in the list",
                    severity=RadarSeverity.ROUTINE,
                    rival=rival.name,
                )
            )

    order = {
        RadarSeverity.ACTS_ON_COPY: 0,
        RadarSeverity.NOTABLE: 1,
        RadarSeverity.ROUTINE: 2,
    }
    return sorted(events, key=lambda event: order[event.severity])


def _territory_events(
    before: PositioningMap, after: PositioningMap
) -> list[RadarEvent]:
    """Ground we lost or gained. The most valuable rows in the feed.

    A claim moving from open to contested is the single change that most
    reliably makes already-written copy worse, and it is invisible from
    everywhere else: nothing about the company changed, so nothing in the
    company's own material can report it.
    """
    if before.is_empty or after.is_empty:
        return []
    was = {reading.axis: reading for reading in before.readings}
    events: list[RadarEvent] = []

    for reading in after.readings:
        previous = was.get(reading.axis)
        if previous is None or previous.territory is reading.territory:
            continue
        lost = _rank(reading.territory) > _rank(previous.territory)
        if lost:
            newcomers = sorted(set(reading.theirs) - set(previous.theirs))
            claim_verb = "claims" if len(newcomers) == 1 else "claim"
            events.append(
                RadarEvent(
                    headline=(
                        f"You no longer own {_axis_name(reading.axis)} on your own"
                        if reading.territory is Territory.CONTESTED
                        else f"{_axis_name(reading.axis)} is now table stakes"
                    ),
                    detail=(
                        (
                            f"{', '.join(newcomers)} now {claim_verb} it too. "
                            if newcomers
                            else ""
                        )
                        + f"You were {_territory_name(previous.territory)}, you are now "
                        f"{_territory_name(reading.territory)}."
                    ),
                    severity=RadarSeverity.ACTS_ON_COPY,
                    axis=reading.axis,
                    what_to_do=(
                        "Any email leading on this claim is now an email your reader has "
                        "had from somebody else. Lead on your open ground instead, or make "
                        "this claim the only specific one in the field."
                    ),
                )
            )
        else:
            events.append(
                RadarEvent(
                    headline=f"{_axis_name(reading.axis)} opened up",
                    detail=(
                        f"you were {_territory_name(previous.territory)} here, you are now "
                        f"{_territory_name(reading.territory)}"
                    ),
                    severity=RadarSeverity.NOTABLE,
                    axis=reading.axis,
                    what_to_do="This is worth leading an email on while it lasts.",
                )
            )
    return events


def _proof_events(previous: MarketSnapshot, current: MarketSnapshot) -> list[RadarEvent]:
    before, after = previous.positioning, current.positioning
    if after.is_empty or before.is_empty:
        return []
    if after.rivals_with_proof > before.rivals_with_proof and not after.we_have_proof:
        return [
            RadarEvent(
                headline="Another competitor started naming customers",
                detail=(
                    f"{after.rivals_with_proof} of {after.rivals_profiled} now show a named "
                    "customer or a quotation on their own site. You show none."
                ),
                severity=RadarSeverity.ACTS_ON_COPY,
                what_to_do=(
                    "Three customer names and one sentence each is an afternoon's work and "
                    "it is the largest single gap between your copy and theirs."
                ),
            )
        ]
    return []


def _rival_events(before: RivalProfile, after: RivalProfile) -> list[RadarEvent]:
    if not after.verified:
        return []
    events: list[RadarEvent] = []

    if (
        before.verified
        and before.promise
        and after.promise
        and overlap(before.promise, after.promise) < _PROMISE_CHANGED_BELOW
    ):
        events.append(
                RadarEvent(
                    headline=f"{after.name} repositioned",
                    detail=f"was: {before.promise}\nnow: {after.promise}",
                    severity=RadarSeverity.NOTABLE,
                    rival=after.name,
                    what_to_do=(
                        "Check whether they have moved onto the claim you lead on."
                    ),
                )
            )

    if before.pricing and after.pricing and before.pricing != after.pricing:
        events.append(
            RadarEvent(
                headline=f"{after.name} changed their pricing",
                detail=f"was: {before.pricing}\nnow: {after.pricing}",
                severity=RadarSeverity.NOTABLE,
                rival=after.name,
                axis=ClaimAxis.PRICE,
            )
        )

    if not before.proof_shown and after.proof_shown:
        events.append(
            RadarEvent(
                headline=f"{after.name} started showing proof",
                detail="; ".join(item.text for item in after.proof_shown[:2]),
                severity=RadarSeverity.NOTABLE,
                rival=after.name,
                axis=ClaimAxis.PROOF,
            )
        )

    for claim in _added(before.claims.claims, after.claims.claims):
        events.append(
            RadarEvent(
                headline=f"{after.name} now claims {_axis_name(claim.axis)}",
                detail=claim.text,
                severity=RadarSeverity.ROUTINE,
                rival=after.name,
                axis=claim.axis,
            )
        )
    return events


def _added(before: list[Claim], after: list[Claim]) -> list[Claim]:
    """Claims present now and not before, compared by what they say rather
    than by how they are worded - a rewritten headline is not a new claim.

    The exact-text check is not redundant with the overlap one, and leaving it
    out was a real bug. `overlap` is computed over *distinctive* words, and a
    claim made entirely of category furniture ("also fast", "built for teams")
    has none - so it scored 0 against an identical copy of itself and was
    reported as new on every single scan. A feed that invents a change every
    week for a competitor who did nothing is the one failure this whole
    feature cannot survive.
    """
    return [
        claim
        for claim in after
        if not any(
            old.axis is claim.axis
            and (
                _normalized(old.text) == _normalized(claim.text)
                or overlap(old.text, claim.text) >= 0.5
            )
            for old in before
        )
    ]


def _normalized(text: str) -> str:
    return " ".join(text.lower().split())


#: What each axis and territory is called in a sentence a person reads. The
#: enum values are identifiers - "table_stakes" with an underscore in the
#: middle of a feed row is the machine's vocabulary leaking into the product.
_AXIS_NAMES: dict[ClaimAxis, str] = {ClaimAxis.BREADTH: "coverage"}
_TERRITORY_NAMES: dict[Territory, str] = {
    Territory.OPEN: "alone on it",
    Territory.CONTESTED: "contested",
    Territory.TABLE_STAKES: "table stakes",
    Territory.EXPOSED: "not claiming it",
}


def _axis_name(axis: ClaimAxis) -> str:
    return _AXIS_NAMES.get(axis, str(axis))


def _territory_name(territory: Territory) -> str:
    return _TERRITORY_NAMES[territory]


def _rank(territory: Territory) -> int:
    return {
        Territory.OPEN: 0,
        Territory.CONTESTED: 1,
        Territory.TABLE_STAKES: 2,
        Territory.EXPOSED: 3,
    }[territory]
