"""The positioning map: what we can say that nobody else can.

This is the artifact the whole package exists to produce, and it is computed
in code from claims that were extracted and quote-checked elsewhere. No model
decides what is differentiated - a model asked that question answers from
whichever claim was written more confidently, and it answers differently on
Tuesday.

The map sorts every axis of competition into four territories, and the
distinction between them is the only strategic input a copywriter actually
needs:

- **Open ground** - nobody else claims this. This is where an email should
  lead, and it is usually not the claim the company is proudest of.
- **Contested** - a few others claim it. Usable, but it has to be argued
  rather than asserted, because the reader has heard it.
- **Table stakes** - everybody claims it, us included. These sentences are not
  false and they are not persuasive: they are the price of being considered.
  Leading on one is how an email becomes invisible.
- **Exposed** - they claim it and we cannot. Not a weakness to hide; a
  comparison an email must not invite.

One rule here is worth stating out loud, because it is the non-obvious half of
the idea: **on a crowded axis, the only specific claim wins the axis.** If
every competitor promises fast setup and exactly one of them says "first API
call in under five minutes", that one is not competing on a crowded axis - it
is the only one making a claim a reader can check, and the rest are noise
around it. So specificity is scored, not just presence, and an axis where we
are alone in carrying a figure comes back as open ground.
"""

from collections import Counter
from enum import StrEnum

from pydantic import BaseModel, Field

from app.knowledge.artifacts import KnowledgeArtifacts
from app.knowledge.ledger import Evidence, value_of
from app.market.claims import Claim, ClaimAxis, ClaimSet, overlap, significant_words
from app.market.rivals import RivalProfile


class Territory(StrEnum):
    OPEN = "open"
    CONTESTED = "contested"
    TABLE_STAKES = "table_stakes"
    EXPOSED = "exposed"


#: The share of profiled rivals that has to claim an axis before it stops
#: differentiating anybody. Half: with three competitors, two making the same
#: promise is a category convention and one is a coincidence.
_TABLE_STAKES_SHARE = 0.5

#: How many rivals have to spend a word before it counts as category
#: vocabulary - the words that make a sentence interchangeable. Two, for the
#: same reason: one competitor sharing your phrasing is a coincidence.
_CROWD_WORD_RIVALS = 2


class AxisReading(BaseModel):
    """One dimension of competition, and who holds it."""

    axis: ClaimAxis
    territory: Territory
    ours: list[Claim] = Field(default_factory=list)
    #: Rival name -> the claims they make on this axis.
    theirs: dict[str, list[Claim]] = Field(default_factory=dict)
    #: True when we are the only one carrying a checkable figure here. The
    #: reason an axis several rivals claim can still be open ground.
    only_specific: bool = False

    @property
    def rivals_claiming(self) -> int:
        return len(self.theirs)

    def render(self) -> str:
        ours = "; ".join(claim.text for claim in self.ours) or "we claim nothing here"
        if self.territory is Territory.EXPOSED:
            who = ", ".join(self.theirs)
            return f"- **{self.axis}** - {who} claim this and we do not. {_EXPOSED_ADVICE}"
        crowd = (
            f" ({self.rivals_claiming} competitor(s) also claim it)"
            if self.rivals_claiming
            else " (nobody else claims it)"
        )
        specific = (
            " We are the only one here carrying a number a reader can check."
            if self.only_specific
            else ""
        )
        return f"- **{self.axis}** - {ours}{crowd}.{specific}"


_EXPOSED_ADVICE = (
    "Do not invite the comparison: an email that raises this axis loses on it."
)


class PositioningMap(BaseModel):
    """Where this company stands against the field it is actually judged in."""

    readings: list[AxisReading] = Field(default_factory=list)
    #: Words two or more competitors spend on their claims. A sentence built
    #: only out of these could have been sent by any of them - which is what
    #: `app.market.sameness` checks every draft for.
    crowd_words: list[str] = Field(default_factory=list)
    #: How many of the profiled rivals display a named customer, a quote or an
    #: attributed outcome, and whether we do. The one number on this map that
    #: no rewrite can move.
    rivals_with_proof: int = 0
    rivals_profiled: int = 0
    we_have_proof: bool = False
    #: Promises the field makes that we have no answer to at all.
    notes: list[str] = Field(default_factory=list)

    def of(self, territory: Territory) -> list[AxisReading]:
        return [reading for reading in self.readings if reading.territory is territory]

    @property
    def open_ground(self) -> list[AxisReading]:
        return self.of(Territory.OPEN)

    @property
    def is_empty(self) -> bool:
        """Whether anybody has actually been read.

        Deliberately not "are there any axis readings". A field of three
        competitors who publish a wall of customer logos and no checkable
        claim produces zero readings and is the *opposite* of an unscanned
        market - it is the case where the most important thing on this map,
        the proof asymmetry, is the only thing on it. Reading emptiness off
        the readings told the strategist nobody had looked, and threw that
        finding away.
        """
        return not self.rivals_profiled

    @property
    def proof_deficit(self) -> bool:
        """Whether every competitor can show somebody who bought it and we
        cannot. The single most expensive asymmetry in cold email, and the one
        the user can actually fix in an afternoon by sending us three
        customer names."""
        return bool(self.rivals_with_proof) and not self.we_have_proof

    def summary(self) -> str:
        if self.is_empty:
            return "No competitors have been profiled, so the copy is written blind to the field"
        open_axes = ", ".join(str(reading.axis) for reading in self.open_ground)
        return (
            f"{self.rivals_profiled} competitor(s) read - "
            + (f"open ground on {open_axes}" if open_axes else "no open ground found")
            + (
                f"; {self.rivals_with_proof} of them show a named customer and we show none"
                if self.proof_deficit
                else ""
            )
        )

    def render_for_strategy(self) -> str:
        """The section the Strategist plans against.

        Phrased as territory rather than as a competitor list on purpose. A
        strategist handed five competitor profiles writes an email about the
        competitors; a strategist handed "these two things are yours alone"
        writes an email about the product, which is the one that converts.
        """
        if self.is_empty:
            return (
                "Nobody has profiled this market yet, so nothing here says which of this "
                "company's claims are shared with every competitor. Write from the material, "
                "and prefer the claims that carry a figure - those are the ones least likely "
                "to be interchangeable."
            )

        blocks: list[str] = [self.summary() + "."]

        if open_ground := self.open_ground:
            blocks.append(
                "\n**Open ground - lead here.** Nothing else in this list differentiates "
                "this company, and a claim nobody else makes is worth more than a stronger "
                "claim everybody makes:\n"
                + "\n".join(reading.render() for reading in open_ground)
            )
        elif not self.readings:
            # Profiled, but nobody's pages carried a claim we could compare -
            # a field that sells on logos and adjectives. Silence here is a
            # finding, and it is not the same as not having looked.
            blocks.append(
                "\n**Nobody in this field makes a checkable claim.** Their pages were read "
                "and none of them carried a figure, a limit or a named result worth "
                "comparing. That is open ground of a different kind: in a category that "
                "argues entirely in adjectives, one email with a number in it is the only "
                "one the reader can check."
            )
        else:
            blocks.append(
                "\n**There is no open ground on the claims themselves.** Every axis this "
                "company competes on is claimed by somebody else too. That does not mean the "
                "email has to be generic - it means the difference has to come from "
                "specificity rather than from the claim: the one competitor carrying a real "
                "figure beats the four asserting the same thing without one."
            )

        if contested := self.of(Territory.CONTESTED):
            blocks.append(
                "\n**Contested - usable, but the reader has heard it.** Argue these, never "
                "assert them:\n" + "\n".join(reading.render() for reading in contested)
            )

        if stakes := self.of(Territory.TABLE_STAKES):
            blocks.append(
                "\n**Table stakes - true, and worth nothing as an argument.** Every "
                "competitor says these. An email that leads on one of them is an email the "
                "reader has already received:\n"
                + "\n".join(reading.render() for reading in stakes)
            )

        if exposed := self.of(Territory.EXPOSED):
            blocks.append(
                "\n**Where the field is ahead of us.** Do not raise these:\n"
                + "\n".join(reading.render() for reading in exposed)
            )

        if self.proof_deficit:
            blocks.append(
                f"\n**Proof asymmetry.** {self.rivals_with_proof} of the "
                f"{self.rivals_profiled} competitors read display a named customer or a "
                "quotation on their own site, and this company displays none. A reader "
                "comparing them is not comparing two sets of claims - they are comparing a "
                "claim to a claim with somebody's name under it. Plan an email that does not "
                "need to be believed on trust: something they can check, or test, in a "
                "minute."
            )

        if self.crowd_words:
            blocks.append(
                "\n**The category's own words.** Two or more competitors spend these. A "
                "sentence built only out of them says nothing about this company:\n- "
                + ", ".join(self.crowd_words[:24])
            )

        blocks.extend(f"\n{note}" for note in self.notes)
        return "\n".join(blocks)


def build(
    ours: ClaimSet, rivals: list[RivalProfile], we_have_proof: bool = False
) -> PositioningMap:
    """Read our claims against the field's. Deterministic, free, repeatable."""
    profiled = [rival for rival in rivals if rival.verified]
    if not profiled:
        return PositioningMap(
            rivals_profiled=0,
            we_have_proof=we_have_proof,
            notes=(
                ["No competitor's site could be read, so nothing here is a comparison."]
                if rivals
                else []
            ),
        )

    threshold = max(1, round(len(profiled) * _TABLE_STAKES_SHARE))
    readings: list[AxisReading] = []

    for axis in ClaimAxis:
        mine = ours.on(axis)
        theirs = {
            rival.name: claims
            for rival in profiled
            if (claims := rival.claims.on(axis))
        }
        if not mine and not theirs:
            continue
        if not mine:
            readings.append(
                AxisReading(axis=axis, territory=Territory.EXPOSED, theirs=theirs)
            )
            continue

        # The specificity rule. An axis half the field claims is still ours if
        # we are the only one who put a number on it - see the module
        # docstring for why that is the interesting case rather than an edge
        # one.
        we_are_specific = any(claim.is_specific for claim in mine)
        they_are_specific = any(
            claim.is_specific for claims in theirs.values() for claim in claims
        )
        only_specific = we_are_specific and not they_are_specific and bool(theirs)

        if not theirs or only_specific:
            territory = Territory.OPEN
        elif len(theirs) >= threshold:
            territory = Territory.TABLE_STAKES
        else:
            territory = Territory.CONTESTED

        readings.append(
            AxisReading(
                axis=axis,
                territory=territory,
                ours=mine,
                theirs=theirs,
                only_specific=only_specific,
            )
        )

    return PositioningMap(
        readings=readings,
        crowd_words=_crowd_words(profiled),
        rivals_with_proof=sum(1 for rival in profiled if rival.proof_shown),
        rivals_profiled=len(profiled),
        we_have_proof=we_have_proof,
    )


#: How many of our own claims reach the map. A real ledger is not a
#: positioning statement: a compiled business runs to well over a hundred
#: entries, most of them true, minor and unarguable ("Email Inbox skips
#: messages older than 24 hours"). Putting all of them on the map does not
#: make it more complete, it makes it unreadable - and worse, it makes the
#: crowded-axis arithmetic meaningless, because an axis we touch in forty
#: incidental facts looks like an axis we compete on.
#:
#: Thirty is comfortably more than any company's real positioning and far
#: below the noise floor.
MAX_OUR_CLAIMS = 30


def claims_from_knowledge(artifacts: KnowledgeArtifacts) -> ClaimSet:
    """Our own claims, derived from what the compiler already established.

    Deliberately not a second extraction pass. Every entry in the evidence
    ledger is already a thing this company asserts, already carries the
    verbatim text that supports it, and has already been quote-checked
    against the corpus - which is the whole of what a claim is here. Paying a
    model to read the same material again to produce the same list would add
    a way for the two to disagree and nothing else.

    Ranked and capped by what each fact is worth to a sale, using the scorer
    the knowledge base already has. A positioning map is a statement about
    what this company competes on, and a fact nobody would ever lead an email
    with is not part of that statement however true it is.
    """
    ranked = sorted(artifacts.evidence.entries, key=lambda entry: -value_of(entry).score)
    claims: list[Claim] = []
    for entry in ranked:
        claim = Claim(
            text=entry.claim,
            verbatim=entry.verbatim,
            source=entry.source or "our own material",
            axis=_axis_for(entry),
            specific=None,
        )
        # A compiled ledger routinely holds the same fact several times over,
        # phrased slightly differently by different passes over different
        # pages - one real business had "Pro plan costs $29 per month",
        # "... with included credits" and "... with credits included" as three
        # entries. That is harmless in an inventory and ruinous on a map: it
        # buries the axis under one restated claim and spends the cap on it.
        if any(
            other.axis is claim.axis and overlap(other.text, claim.text) >= _SAME_WORDING
            for other in claims
        ):
            continue
        claims.append(claim)
        if len(claims) >= MAX_OUR_CLAIMS:
            break
    return ClaimSet(claims=claims)


#: How much two of our own claims have to share before one is treated as a
#: restatement of the other. Higher than `SAME_CLAIM_OVERLAP`, because this
#: decides whether to *drop* a claim rather than whether to show two side by
#: side, and dropping a real second claim costs more than showing a duplicate.
_SAME_WORDING = 0.7


#: Which axis a fact of each evidence kind competes on, where the kind alone
#: settles it. The rest are read from the words - see `_axis_for`.
_AXIS_BY_KIND: dict[str, ClaimAxis] = {
    "price": ClaimAxis.PRICE,
    "testimonial": ClaimAxis.PROOF,
    "customer": ClaimAxis.PROOF,
    "award": ClaimAxis.PROOF,
    "certification": ClaimAxis.SECURITY,
    "integration": ClaimAxis.BREADTH,
    "guarantee": ClaimAxis.SUPPORT,
}

#: Words that place a claim on an axis when its kind does not. Ordered by how
#: unambiguous each signal is: a claim mentioning both "minutes" and "models"
#: is about speed, because a time is a harder signal than a count.
_AXIS_WORDS: tuple[tuple[ClaimAxis, tuple[str, ...]], ...] = (
    (ClaimAxis.SPEED, ("minute", "minutes", "second", "seconds", "instant", "instantly",
                       "latency", "faster", "same-day", "overnight", "real-time", "realtime",
                       "in an hour", "within hours", "in a day", "within a day", "same day",
                       "in a week", "within a week", "time to first", "setup time")),
    (ClaimAxis.SECURITY, ("soc", "gdpr", "hipaa", "iso", "encrypt", "encrypted", "privacy",
                          "compliance", "compliant", "audit", "audited", "sso", "residency")),
    # A claim is about price when it names a *cost*, not when it names a plan.
    # "Pro plan includes Teams & RBAC" is a coverage claim that happens to
    # mention a tier, and routing it here put twenty feature rows on the price
    # axis of a real business and buried the two claims that were about money.
    (ClaimAxis.PRICE, ("free", "price", "pricing", "costs", "cost ", "$", "€", "£",
                       "per month", "per seat", "per user", "no card", "trial",
                       "credits on signup", "billing", "no seat fees", "hidden costs")),
    (ClaimAxis.CONTROL, ("open source", "open-source", "self-host", "self-hosted", "export",
                         "lock-in", "lock in", "on-premise", "on-prem", "portable", "byo")),
    (ClaimAxis.EFFORT, ("no code", "no-code", "without code", "no setup", "no engineer",
                        "no hire", "no plumbing", "glue code", "out of the box", "zero config")),
    (ClaimAxis.BREADTH, ("providers", "provider", "models", "integrations", "integration",
                         "connectors", "channels", "languages", "formats", "sources", "apps",
                         "supports", "works with", "any framework")),
    (ClaimAxis.SUPPORT, ("support team", "onboarding", "migration", "success manager",
                         "sla", "dedicated engineer", "dedicated support", "help you",
                         "we help", "hands-on")),
    (ClaimAxis.QUALITY, ("accuracy", "accurate", "uptime", "reliable", "reliability",
                         "precision", "quality", "error rate", "benchmark")),
)


def _axis_for(entry: Evidence) -> ClaimAxis:
    kind = _AXIS_BY_KIND.get(str(entry.kind))
    if kind is not None:
        return kind
    text = f"{entry.claim} {entry.verbatim}".lower()
    for axis, markers in _AXIS_WORDS:
        if any(marker in text for marker in markers):
            return axis
    return ClaimAxis.OTHER


def _crowd_words(rivals: list[RivalProfile]) -> list[str]:
    """The vocabulary of the category, as opposed to of any one company.

    Counted per rival rather than per claim: a competitor who says "seamless"
    on every one of eight claims has said it once as far as this is concerned,
    or one wordy site would define the category's language on its own.
    """
    counts: Counter[str] = Counter()
    for rival in rivals:
        words = rival.claims.vocabulary() | {
            word for term in rival.vocabulary for word in significant_words(term)
        }
        counts.update(words)
    return sorted(
        (word for word, seen in counts.items() if seen >= _CROWD_WORD_RIVALS),
        key=lambda word: (-counts[word], word),
    )
