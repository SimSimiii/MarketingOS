"""The positioning map: differences among captured, verified claims.

This is the artifact the whole package exists to produce, and it is computed
in code from claims that were extracted and quote-checked elsewhere. No model
decides what is differentiated - a model asked that question answers from
whichever claim was written more confidently, and it answers differently on
Tuesday.

Each reading concerns a proposition, not a whole category such as price or
proof. Related propositions carry an explicit comparison and its limits.
Territory identifiers remain compatible with saved artifacts: open means no
related proposition captured, contested means related claims need inspection,
table stakes means equivalent captured claims recur, and exposed means our
captured material has no match. None establishes superiority or incapability.
"""

import re
from collections import Counter
from enum import StrEnum
from math import ceil
from typing import Literal

from pydantic import BaseModel, Field

from app.knowledge.artifacts import KnowledgeArtifacts
from app.knowledge.corpus import fold
from app.knowledge.ledger import Evidence, EvidenceKind, category_of, context_of, value_of
from app.knowledge.taxonomy import FactCategory
from app.market.claims import (
    Claim,
    ClaimAxis,
    ClaimSet,
    ComparisonStatus,
    comparable_claim,
    compare_claims,
    is_own_assertion,
    monetary_outcome,
    overlap,
    proposition_words,
    same_claim,
    significant_words,
)
from app.market.rivals import RivalProfile


class Territory(StrEnum):
    OPEN = "open"
    CONTESTED = "contested"
    TABLE_STAKES = "table_stakes"
    EXPOSED = "exposed"


#: Equivalent captured propositions must recur in at least half the profiles
#: and at least two independent rivals before being labelled common.
_TABLE_STAKES_SHARE = 0.5

#: How many rivals have to spend a word before it counts as category
#: vocabulary - the words that make a sentence interchangeable. Two, for the
#: same reason: one competitor sharing your phrasing is a coincidence.
_CROWD_WORD_RIVALS = 2

MAX_STRATEGY_CHARS = 10_000
MAX_STRATEGY_PROPOSITIONS = 18


class AxisReading(BaseModel):
    """One captured proposition, grouped under a broad browsing axis."""

    axis: ClaimAxis
    territory: Territory
    ours: list[Claim] = Field(default_factory=list)
    #: Rival name -> the claims they make on this axis.
    theirs: dict[str, list[Claim]] = Field(default_factory=dict)
    #: Informational only. A figure never establishes superior performance.
    only_specific: bool = False
    proposition: str = ""
    comparison_status: Literal[
        "equivalent", "documented_difference", "potential_difference", "unknown"
    ] = "unknown"
    comparisons: dict[str, ComparisonStatus] = Field(default_factory=dict)
    comparison_notes: list[str] = Field(default_factory=list)

    @property
    def rivals_claiming(self) -> int:
        return len(self.theirs)

    def render(self) -> str:
        label = self.proposition or str(self.axis)
        ours = "; ".join(claim.text for claim in self.ours) or "no matching claim in our captured material"
        if self.territory is Territory.EXPOSED:
            who = ", ".join(self.theirs)
            return f"- **{label}** - {who}: {ours}. {_EXPOSED_ADVICE}"
        crowd = (
            f" ({self.rivals_claiming} competitor(s) have related captured claims)"
            if self.rivals_claiming
            else " (no competing claim captured on the pages read; rival capability remains unknown)"
        )
        specific = (
            " Only our captured proposition is marked specific; that is not superior performance."
            if self.only_specific
            else ""
        )
        notes = " ".join(self.comparison_notes)
        return f"- **{label}** [{self.comparison_status}] - {ours}{crowd}.{specific} {notes}".rstrip()


_EXPOSED_ADVICE = (
    "Our captured material does not support a matching promise. Do not infer a missing "
    "capability or competitor superiority; verify it before making a comparison."
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
    #: Capture limitations and research questions.
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
        """Whether rivals display customer evidence absent from our capture.

        A source gap, never a verdict about product performance or suitability
        for a functional campaign.
        """
        return bool(self.rivals_with_proof) and not self.we_have_proof

    def summary(self) -> str:
        if self.is_empty:
            return "No competitors have been profiled, so the copy is written blind to the field"
        unmatched = len(self.open_ground)
        documented = sum(row.comparison_status == "documented_difference" for row in self.readings)
        return (
            f"{self.rivals_profiled} competitor(s) read - "
            + f"{documented} documented difference(s); {unmatched} unmatched captured proposition(s) "
            "need verification, not an exclusivity conclusion"
            + (
                f"; {self.rivals_with_proof} show customer evidence; none captured for us"
                if self.proof_deficit
                else ""
            )
        )

    def render_for_strategy(self, audience: str = "") -> str:
        """A bounded decision brief; the full map remains available for inspection.

        Rank supported product propositions by the selected audience's words,
        preserve coverage across dimensions, and keep only a few explicit
        research gaps. This is selection of existing facts, not a new fit claim.
        """
        if self.is_empty:
            return (
                "Nobody has profiled this market yet, so nothing here says which of this "
                "company's claims are shared with every competitor. Write from the material, "
                "and prefer the claims that carry a figure - those are the ones least likely "
                "to be interchangeable."
            )

        blocks: list[str] = [
            self.summary() + ".",
            (
                "This map compares captured claims from the pages read, not complete product "
                "capabilities. Unread pages and extraction omissions remain unknown. Open ground "
                "is a hypothesis to verify, never proof of exclusivity or of a rival's inability."
            ),
        ]

        if not self.readings:
            blocks.append(
                "\n**No comparable claims were captured.** The profiles may be incomplete. "
                "Do not infer that competitors lack specific claims or capabilities. "
                "Prefer a supported detail the reader can inspect in our own material."
            )
        elif not self.open_ground:
            blocks.append(
                "\n**No unmatched proposition was identified.** Inspect the individual "
                "comparisons and their conditions. A more specific figure alone does not "
                "establish superiority or a different capability."
            )

        if self.proof_deficit:
            blocks.append(
                f"\n**Proof asymmetry.** {self.rivals_with_proof} of the "
                f"{self.rivals_profiled} competitors read display a named customer or a "
                "quotation on their own site, and this company has no captured equivalent. "
                "This is a gap in captured customer evidence, not product performance. "
                "Official documentation can support a functional claim without a testimonial. "
                "Outcome promises need evidence for that outcome, within its customer context."
            )

        if self.crowd_words:
            blocks.append(
                "\n**Shared category vocabulary.** Two or more competitors use these. "
                "Keep the words needed to explain the product; common vocabulary alone "
                "does not make a proposition generic. Avoid unsupported superlatives:\n- "
                + ", ".join(word for word in self.crowd_words[:16] if len(word) <= 60)
            )

        blocks.extend(f"\n{note[:600]}" for note in self.notes[:3])
        words = proposition_words(audience)
        ranked = sorted(
            self.readings,
            key=lambda row: (
                -len(words & proposition_words(" ".join(claim.text for claim in row.ours)
                                               or row.proposition)),
                not bool(row.ours),
                row.comparison_status != "documented_difference",
            ),
        )
        # The most relevant rows lead. A second pass gives each product axis
        # a turn, so a long price list cannot consume the bounded brief.
        own_rows = [row for row in ranked if row.ours]
        grouped: dict[ClaimAxis, list[AxisReading]] = {}
        for row in own_rows:
            grouped.setdefault(row.axis, []).append(row)
        selected: list[AxisReading] = []
        depth = 0
        while len(selected) < MAX_STRATEGY_PROPOSITIONS:
            current = [items[depth] for items in grouped.values() if len(items) > depth]
            if not current:
                break
            selected.extend(current[:MAX_STRATEGY_PROPOSITIONS - len(selected)])
            depth += 1
        missing = [row for row in ranked if not row.ours][:3]
        sections = [
            (("\n**Supported product propositions.** Use their stated conditions. "
              "An unmatched capture is a question to verify, not exclusivity."), selected),
            (("\n**Information missing from our captured material.** Research before comparing. "
              "Do not infer a missing capability or competitor superiority."), missing),
        ]
        shown = 0
        for heading, rows in sections:
            if not rows:
                continue
            blocks.append(heading)
            for reading in rows:
                line = _strategy_line(reading)
                # Leave room for an explicit omission count rather than cut a
                # proposition's terms halfway through its sentence.
                if sum(len(block) + 1 for block in blocks) + len(line) > MAX_STRATEGY_CHARS - 220:
                    continue
                blocks.append(line)
                shown += 1
        omitted = len(self.readings) - shown
        if omitted:
            blocks.append(f"\n{omitted} additional captured propositions remain in the full map. "
                          "This brief prioritises product facts; omitted gaps are not evidence of incapability.")
        return "\n".join(blocks)


def _strategy_line(reading: AxisReading) -> str:
    label = reading.proposition or "; ".join(claim.text for claim in reading.ours) or str(reading.axis)
    parts = [f"- **{label}** [{reading.axis}; {reading.comparison_status}]"]
    if not reading.ours:
        parts.append(_EXPOSED_ADVICE)
    elif not reading.theirs:
        parts.append("no competing claim captured; rival capability remains unknown.")
    else:
        names = list(reading.theirs)
        parts.append("Related captures: " + ", ".join(names[:3])
                     + (f" and {len(names) - 3} others." if len(names) > 3 else "."))
        reasons = list(dict.fromkeys(note.partition(": ")[2] or note
                                     for note in reading.comparison_notes))
        parts.extend(reasons[:2])
    for claim in reading.ours:
        details = [claim.context.conditions, claim.context.temporal_scope, claim.context.limitations]
        parts.extend(detail for detail in details if detail)
    return " ".join(parts)


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

    rival_names = tuple(rival.name for rival in rivals)
    ours = ClaimSet(claims=[claim for claim in ours.claims
                           if is_own_assertion(claim, rival_names=rival_names)])
    threshold = max(2, ceil(len(profiled) * _TABLE_STAKES_SHARE))
    readings: list[AxisReading] = []

    for axis in ClaimAxis:
        mine = _claims_on(ours, axis)
        theirs = {
            rival.name: claims
            for rival in profiled
            if (claims := _claims_on(rival.claims, axis))
        }
        if not mine and not theirs:
            continue
        for own in mine:
            related = {
                name: [claim for claim in claims if comparable_claim(own, claim)]
                for name, claims in theirs.items()
            }
            related = {name: claims for name, claims in related.items() if claims}
            comparisons: dict[str, ComparisonStatus] = {}
            notes: list[str] = []
            for name, claims in related.items():
                judged = [compare_claims(own, claim) for claim in claims]
                # An equivalent is enough to show that this particular promise
                # is shared; a different plan need not erase that match.
                status, reason = min(judged, key=lambda item: {
                    "equivalent": 0, "documented_difference": 1, "potential_difference": 2,
                }[item[0]])
                comparisons[name] = status
                notes.append(f"{name}: {reason}")
            equivalent = sum(status == "equivalent" for status in comparisons.values())
            territory = (
                Territory.TABLE_STAKES if equivalent >= threshold
                else Territory.CONTESTED if related else Territory.OPEN
            )
            status = (
                "potential_difference" if "potential_difference" in comparisons.values()
                else "documented_difference" if "documented_difference" in comparisons.values()
                else "equivalent" if comparisons else "unknown"
            )
            readings.append(AxisReading(
                axis=axis, proposition=own.text, territory=territory, ours=[own],
                theirs=related, comparisons=comparisons, comparison_status=status,
                comparison_notes=notes or [
                    "No equivalent proposition captured; competitors' capabilities remain unknown."
                ],
                only_specific=(own.is_specific and bool(related) and not any(
                    claim.is_specific for claims in related.values() for claim in claims
                )),
            ))
        # Rival-only propositions are gaps in our information, never a
        # capability verdict. Do not repeat claims already beside our row.
        for name, claims in theirs.items():
            for candidate in claims:
                if any(comparable_claim(own, candidate) for own in mine):
                    continue
                existing = next((reading for reading in readings
                                 if reading.axis is axis and not reading.ours
                                 and reading.theirs and same_claim(
                                     next(iter(reading.theirs.values()))[0], candidate)), None)
                if existing is not None:
                    existing.theirs.setdefault(name, []).append(candidate)
                    continue
                readings.append(AxisReading(
                    axis=axis, proposition=candidate.text, territory=Territory.EXPOSED,
                    theirs={name: [candidate]}, comparison_status="unknown",
                    comparison_notes=[
                        "No matching claim in our captured material; investigate rather than infer a weakness."
                    ],
                ))

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
    candidates: list[Claim] = []
    core_words = proposition_words(artifacts.business.what_it_does)
    core: list[tuple[int, Claim]] = []
    for entry in ranked:
        if category_of(entry) in {FactCategory.COMPANY, FactCategory.BRAND, FactCategory.MARKET}:
            continue
        if _is_limitation(f"{entry.claim} {entry.verbatim}"):
            continue
        claim = Claim(
            text=entry.claim,
            verbatim=entry.verbatim,
            source=entry.source or "our own material",
            axis=axis_for_evidence(entry),
            specific=None,
            context=context_of(entry),
        )
        if not is_own_assertion(claim, company_name=artifacts.business.company_name):
            continue
        # A compiled ledger routinely holds the same fact several times over,
        # phrased slightly differently by different passes over different
        # pages - one real business had "Pro plan costs $29 per month",
        # "... with included credits" and "... with credits included" as three
        # entries. That is harmless in an inventory and ruinous on a map: it
        # buries the axis under one restated claim and spends the cap on it.
        if any(
            other.axis is claim.axis and (
                (other.source == claim.source and other.text == claim.text
                 and other.verbatim == claim.verbatim and other.context == claim.context)
                or (same_claim(other, claim)
                    and overlap(other.text, claim.text) >= _SAME_WORDING)
            )
            for other in candidates
        ):
            continue
        candidates.append(claim)
        relevance = len(core_words & proposition_words(claim.text))
        if entry.kind is EvidenceKind.FEATURE and relevance >= 2:
            core.append((relevance, claim))
    # A price list must not consume the entire map before a documented
    # capability is considered. Round-robin the existing broad browsing axes,
    # retaining commercial ranking within each one and the same overall cap.
    selected = _diverse_claims(candidates, MAX_OUR_CLAIMS)
    protected: list[Claim] = []
    for _, central in sorted(core, key=lambda pair: -pair[0])[:2]:
        protected.append(central)
        if central not in selected:
            replace = next((index for index in reversed(range(len(selected)))
                            if selected[index].axis is central.axis and selected[index] not in protected), None)
            if replace is not None:
                selected[replace] = central
    return ClaimSet(claims=selected)


def _diverse_claims(claims: list[Claim], limit: int) -> list[Claim]:
    grouped: dict[ClaimAxis, list[Claim]] = {}
    for claim in claims:
        grouped.setdefault(claim.axis, []).append(claim)
    selected: list[Claim] = []
    depth = 0
    while len(selected) < limit:
        row = [items[depth] for items in grouped.values() if len(items) > depth]
        if not row:
            break
        selected.extend(row[:limit - len(selected)])
        depth += 1
    return selected


def build_current(
    artifacts: KnowledgeArtifacts, rivals: list[RivalProfile], *, we_have_proof: bool = False,
) -> PositioningMap:
    """Current product facts against saved rival captures, without history writes."""
    result = build(claims_from_knowledge(artifacts), rivals, we_have_proof=we_have_proof)
    if rivals:
        result.notes.append(
            "Current product knowledge is compared with saved competitor pages; check "
            "their capture dates before making time-sensitive comparisons."
        )
    return result


# Limits and missing evidence belong in the knowledge gaps, not in a list of
# positive competitive promises. Keep this narrow: "no monthly fees" and
# "no data leaves your VPC" are supported benefits, not missing capabilities.
_LIMITATION = re.compile(
    r"\b(?:does not|do not|cannot|can't|doesn't) guarantee\b"
    r"|\b(?:does not|do not|cannot|can't|doesn't)\b[^.!?;\n]{0,100}"
    r"\b(?:or|nor) guarantee\b"
    r"|\b(?:cannot|can't) export\b"
    r"|\b(?:does not|do not|doesn't) (?:support|allow) exports?\b"
    r"|\b(?:quality|performance|results)\b.{0,90}"
    r"\b(?:has not|is not|not yet|hasn't|isn't)\b.{0,40}"
    r"\b(?:established|validated|verified|measured)\b"
    r"|\b(?:generation|run|request|compilation)\b.{0,35}"
    r"\b(?:can|may|could) take several (?:minutes|hours|days)\b"
    r"|\bno (?:public )?(?:subscription price|customer testimonials?|"
    r"customer names|measurable results)\b"
)


def _is_limitation(text: str) -> bool:
    return bool(_LIMITATION.search(fold(text))) or _negated_control(text)


def _claims_on(claims: ClaimSet, axis: ClaimAxis) -> list[Claim]:
    """Count explicit portability even when extraction filed it under effort.

    One verified sentence can support more than one dimension. Preserve its
    quotation and source; never infer a capability from a model's paraphrase.
    """
    matches: list[Claim] = []
    for claim in claims.claims:
        if _is_limitation(f"{claim.text} {claim.verbatim}"):
            continue
        if monetary_outcome(claim):
            if axis is not ClaimAxis.PROOF:
                continue
            candidate = claim.model_copy(update={"axis": ClaimAxis.PROOF})
        elif claim.axis is axis:
            candidate = claim
        elif axis is ClaimAxis.CONTROL and _explicit_control(claim.verbatim):
            candidate = claim.model_copy(update={"axis": axis})
        else:
            continue
        if not any((item.text, item.source, item.verbatim, item.context) ==
                   (candidate.text, candidate.source, candidate.verbatim, candidate.context)
                   for item in matches):
            matches.append(candidate)
    return matches


def rebuild(positioning: PositioningMap, rivals: list[RivalProfile]) -> PositioningMap:
    """Recompute arithmetic from saved claims without changing scan history.

    No current knowledge or new pages are mixed into the historical corpus.
    Legacy snapshots without profiles cannot support proposition comparisons.
    Preserve their own claims but mark the comparison unknown on read.
    """
    if not rivals:
        if positioning.rivals_profiled and any(not row.proposition for row in positioning.readings):
            note = (
                "Legacy category comparisons have no saved competitor profiles. Rescan "
                "before using competitive conclusions; proposition equivalence is unknown."
            )
            readings = [
                AxisReading(axis=row.axis, proposition=claim.text, territory=Territory.CONTESTED,
                            ours=[claim], comparison_status="unknown", comparison_notes=[note])
                for row in positioning.readings for claim in row.ours
            ]
            return positioning.model_copy(update={
                "readings": readings,
                "notes": list(dict.fromkeys([*positioning.notes, note])),
            })
        return positioning
    ours = ClaimSet(claims=[claim for reading in positioning.readings for claim in reading.ours])
    updated = build(ours, rivals, we_have_proof=positioning.we_have_proof)
    updated.notes = list(dict.fromkeys([*positioning.notes, *updated.notes]))
    return updated


def _explicit_portability(quote: str) -> bool:
    text = re.sub(r"[\"'\u2018\u2019\u201c\u201d]", "", fold(quote))
    if re.search(r"\b(?:cannot|cant|can not|does not|do not|doesnt|dont|no)\b"
                 r".{0,45}\b(?:export|copy)\b", text):
        return False
    return bool(re.search(
        r"\bexport(?:ing|s|ed)?\s+(?:your\s+)?"
        r"(?:emails?|drafts?|content|data|results|contacts|files|campaigns)\b"
        r"|\bexport(?:ing|s|ed)?\s+(?:to|as|in)\b.{0,45}"
        r"\b(?:esp|html|csv|pdf|json|your own|your existing)\b"
        r"|\bcopy\b.{0,35}\b(?:text|content|email)\b.{0,25}"
        r"\b(?:for use|to use|into|to)\b.{0,25}\b(?:elsewhere|another|your own)\b",
        text,
    ))


def _explicit_control(quote: str) -> bool:
    """Brand ownership and portability are control even when misfiled upstream."""
    text = fold(quote)
    if _negated_control(text):
        return False
    return _explicit_portability(quote) or bool(re.search(
        r"\bcustom\s+(?:\(sub\)|sub)?domains?\b|\b(?:your\s+)?own\s+domains?\b|"
        r"\bwhite[- ]label(?:ed|led|ing)?\b|"
        r"\b(?:remove|removes|removing|hide|hides)\s+(?:[\w'-]+\s+){0,3}branding\b|"
        r"\btransfer(?:ring)?\b.{0,35}\b(?:ownership|forms?|projects?|workspaces?)\b",
        text,
    ))


def _negated_control(text: str) -> bool:
    subject = r"(?:custom\s+(?:\(sub\)|sub)?domains?|branding|white[- ]label(?:ing)?)"
    return bool(re.search(
        r"\b(?:cannot|can't|does not|doesn't|do not|not supported|no support for)\b"
        r"[^.!?;\n]{0,65}\b" + subject + r"\b|\b" + subject +
        r"\b[^.!?;\n]{0,50}\b(?:not (?:yet )?(?:supported|available)|unsupported|unavailable)\b",
        fold(text),
    ))


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
    # A trial *offer* belongs here; trial signup/conversion statistics do not.
    (ClaimAxis.PRICE, ("free", "price", "pricing", "costs", "cost ", "$", "€", "£",
                       "per month", "per seat", "per user", "no card",
                       "day trial", "week trial", "month trial",
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


def axis_for_evidence(entry: Evidence) -> ClaimAxis:
    """The market axis a verified ledger entry competes on.

    Public because relevance dossiers use the same deterministic taxonomy to
    attach an existing territory to an evidence id.  It is classification of
    a product fact, never a new market claim.
    """
    if monetary_outcome(Claim(text=entry.claim, verbatim=entry.verbatim, context=context_of(entry))):
        return ClaimAxis.PROOF
    if (str(entry.kind) == "metric"
            and context_of(entry).claim_scope not in {"capability", "offer"}
            and re.search(r"\b\d[\d,.+]*\s+(?:\w+\s+){0,5}"
                          r"(?:creators?|companies|customers?|users?|businesses|teams?|freelancers?|agencies|organizations?)\b",
                          entry.claim, re.IGNORECASE)
            and re.search(r"\b(?:use|uses|using|trust|trusted|collect and share|serve|served)\b",
                          entry.claim, re.IGNORECASE)):
        return ClaimAxis.PROOF
    text = f"{entry.claim} {entry.verbatim}".lower()
    if re.search(r"\b(?:rate limit|requests? allowed|maximum.{0,20}requests?|api.{0,20}limit)\b", text):
        return ClaimAxis.BREADTH
    if str(entry.kind) == "feature" and _explicit_control(entry.verbatim):
        return ClaimAxis.CONTROL
    kind = _AXIS_BY_KIND.get(str(entry.kind))
    if kind is not None:
        return kind
    # A policy duration is not product performance. Classify the policy before
    # the broad time-unit hints, which otherwise turn SSO expiry into speed.
    if re.search(r"\b(?:session|sso|password|salt)\b.{0,90}\b(?:expir|timeout|rotat)", text):
        return ClaimAxis.SECURITY
    if re.search(r"\b(?:overage|upgrade|subscription|billing)\b.{0,130}\b(?:lock|notice|week|days?)\b", text):
        return ClaimAxis.PRICE
    for axis, markers in _AXIS_WORDS:
        if any((marker in text if marker in {"$", "€", "£"} else re.search(
            r"(?<!\w)" + re.escape(marker.strip()) + r"(?!\w)", text,
        )) for marker in markers):
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
        (word for word, seen in counts.items()
         if seen >= _CROWD_WORD_RIVALS and any(char.isalpha() for char in word)),
        key=lambda word: (-counts[word], word),
    )
