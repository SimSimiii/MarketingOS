"""The Knowledge Base: everything compiled about a business, on shelves.

The compiler produces six artifacts in six different shapes - a profile, an
offer sheet, an evidence ledger, a voice profile, an audience model, a gap
report - each shaped for the prompt that reads it. That is correct for the
machines and useless for a person. A user who wants to know what we found out
about their pricing has to open five panels and know which one holds it.

This module is the other view of the same data: one flat, classified, ranked,
searchable index where every fact - wherever in the artifacts it came from -
is an entry with a shelf, a commercial value, a provenance and a reason it
scored what it did.

Two audiences read it and they want the same thing for different reasons.

**The user** browses it. It is the only place the product tells them what it
actually knows about their business, and the shelf with nothing on it is the
most useful thing on the page: an empty "Trust & compliance" is a sentence
saying which page they should upload next, in return for which their emails
stop hedging.

**The agents** plan against it. A strategist handed 121 undifferentiated facts
picks the first three; the same strategist handed "6 commercial, 3 proof,
nothing technical" picks an angle the material can actually carry.

It is derived, never stored. Building it is a few hundred regex matches over
data already in memory, so there is no second copy to keep in sync, no
migration, and artifacts compiled before any of this existed get shelved and
scored the moment somebody opens the page.
"""

import re
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from app.knowledge.artifacts import Grounding, KnowledgeArtifacts
from app.knowledge.ledger import Evidence, category_of, value_of
from app.knowledge.taxonomy import (
    CATEGORY_ORDER,
    SHELVES,
    FactCategory,
    ValueBand,
    assess_value,
    classify,
)

_WORD_RE = re.compile(r"[a-z0-9]+")
_WHITESPACE_RE = re.compile(r"\s+")

#: How many of the strongest facts a shelf names when it is summarised for a
#: model. Enough to show what is on the shelf, few enough that the map stays a
#: map - the full inventory reaches the writer through the evidence slice.
_HIGHLIGHTS_PER_SHELF = 2


class EntryOrigin(StrEnum):
    """Which artifact a knowledge entry was lifted out of.

    It decides one thing that matters and several that are merely interesting:
    only entries from the evidence ledger carry an id a writer may cite, and
    only those are checked by the evidence gate. Everything else on the shelf
    is context - true, useful for deciding what an email argues, and not
    licensed to appear in the copy as a claim.
    """

    EVIDENCE = "evidence"
    PROFILE = "profile"
    OFFER = "offer"
    AUDIENCE = "audience"
    VOICE = "voice"


class KnowledgeEntry(BaseModel):
    """One thing known about the business, on a shelf, with a price on it."""

    id: str
    category: FactCategory
    statement: str
    #: The text from the user's own material that supports this. Empty for
    #: inferred entries, which is why `grounding` is next to it.
    verbatim: str = ""
    source: str = ""
    document_id: str | None = None
    origin: EntryOrigin
    #: The compiler's own label where it had one (`metric`, `testimonial`), or
    #: what this entry is when it came from elsewhere (`plan`, `objection`).
    kind: str = ""
    grounding: Grounding = Grounding.GROUNDED
    strength: str = ""
    #: 0-100. See app.knowledge.taxonomy.assess_value.
    value: int = 0
    band: ValueBand = ValueBand.BACKGROUND
    #: Why it scored that, in plain sentences. Shown to the user next to the
    #: number, because a ranking nobody can interrogate is a ranking nobody
    #: believes.
    why: list[str] = Field(default_factory=list)
    #: Whether a writer may cite this id in copy. True only for the evidence
    #: ledger - see EntryOrigin.
    citable: bool = False
    tags: list[str] = Field(default_factory=list)

    @property
    def haystack(self) -> str:
        return f"{self.statement} {self.verbatim} {self.source} {' '.join(self.tags)}"


class KnowledgeShelf(BaseModel):
    """One category, with everything on it and what its being empty costs."""

    category: FactCategory
    label: str
    blurb: str
    buyer_question: str
    sells_by: str
    when_empty: str
    entries: list[KnowledgeEntry] = Field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.entries)

    @property
    def headline_count(self) -> int:
        return sum(1 for entry in self.entries if entry.band is ValueBand.HEADLINE)

    @property
    def strongest(self) -> KnowledgeEntry | None:
        return self.entries[0] if self.entries else None

    def render(self) -> str:
        """One line of the map a strategist plans against."""
        if not self.entries:
            return f"- **{self.label}** - nothing here. {self.when_empty}"
        highlights = "; ".join(
            f'"{_collapse(entry.statement, 110)}" [{entry.id}]'
            for entry in self.entries[:_HIGHLIGHTS_PER_SHELF]
        )
        strength = (
            f"{self.headline_count} strong enough to lead an email"
            if self.headline_count
            else "none of them strong enough to lead an email on their own"
        )
        return f"- **{self.label}** - {self.count} fact(s), {strength}. Strongest: {highlights}"


class KnowledgeBase(BaseModel):
    """Everything known about one business, classified and priced."""

    entries: list[KnowledgeEntry] = Field(default_factory=list)
    shelves: list[KnowledgeShelf] = Field(default_factory=list)
    version: int = 0
    compiled_at: datetime | None = None
    built_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    #: Whether the compiler found anything at all. Not the same as "no
    #: entries": a bundle compiled from nothing still describes the house
    #: default voice, so counting entries would report three facts about a
    #: business we know nothing about.
    has_material: bool = True
    #: What the compiler could not establish, carried through unchanged. It
    #: belongs on this page rather than behind a separate tab: the gap and the
    #: empty shelf it explains are the same finding said twice.
    open_questions: list[str] = Field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.entries)

    @property
    def citable_total(self) -> int:
        return sum(1 for entry in self.entries if entry.citable)

    @property
    def headline_total(self) -> int:
        return sum(1 for entry in self.entries if entry.band is ValueBand.HEADLINE)

    @property
    def empty_shelves(self) -> list[KnowledgeShelf]:
        return [shelf for shelf in self.shelves if not shelf.entries]

    def shelf(self, category: FactCategory) -> KnowledgeShelf | None:
        return next((item for item in self.shelves if item.category is category), None)

    def top(self, limit: int = 10, category: FactCategory | None = None) -> list[KnowledgeEntry]:
        pool = self.entries if category is None else [
            entry for entry in self.entries if entry.category is category
        ]
        return pool[:limit]

    def search(
        self,
        query: str = "",
        category: FactCategory | None = None,
        band: ValueBand | None = None,
        origin: EntryOrigin | None = None,
        limit: int = 200,
    ) -> list[KnowledgeEntry]:
        """The entries a filtered view of the base should show, best first.

        Text matching is a word-overlap count rather than a substring test, so
        "pricing team plan" finds the Team plan without the user having to
        guess how the compiler phrased it. Within an equal number of matched
        words, commercial value decides - the ordering the base is built in.
        """
        results = [
            entry
            for entry in self.entries
            if (category is None or entry.category is category)
            and (band is None or entry.band is band)
            and (origin is None or entry.origin is origin)
        ]
        terms = {word for word in _WORD_RE.findall(query.lower()) if len(word) > 1}
        if terms:
            scored: list[tuple[int, int, KnowledgeEntry]] = []
            for index, entry in enumerate(results):
                words = set(_WORD_RE.findall(entry.haystack.lower()))
                overlap = len(terms & words)
                if overlap:
                    scored.append((overlap, index, entry))
            scored.sort(key=lambda item: (-item[0], item[1]))
            results = [entry for _, _, entry in scored]
        return results[:limit]

    def render_map(self) -> str:
        """The shelf map, for the one role that decides what a campaign says.

        Not the facts - the strategist already gets those. This is the shape
        of what exists: which arguments are available at all, which are thin,
        and which shelf being empty is the reason an obvious angle is not on
        the table. A strategist that can see "nothing under Trust & compliance"
        stops planning the security email that would have to be invented.
        """
        if not self.has_material or not self.entries:
            return (
                "Nothing has been compiled for this business. There are no facts to plan "
                "from - every specific in the copy would have to be invented."
            )
        header = (
            f"{self.total} fact(s) on {len([s for s in self.shelves if s.entries])} shelf(s), "
            f"{self.citable_total} of them citable in copy, "
            f"{self.headline_total} strong enough to lead an email."
        )
        lines = [header, ""] + [shelf.render() for shelf in self.shelves]
        if self.open_questions:
            lines.append(
                "\nStill unanswered:\n"
                + "\n".join(f"- {question}" for question in self.open_questions)
            )
        return "\n".join(lines)


# ----------------------------------------------------------------- building


def build_knowledge_base(
    artifacts: KnowledgeArtifacts, version: int = 0
) -> KnowledgeBase:
    """Flatten every compiled artifact into one classified, ranked index.

    Order of construction matters only for id stability: an entry's id is what
    the UI keys on and what a user quotes back in a bug report, so it is
    derived from where the fact came from rather than from its position after
    sorting.
    """
    entries: list[KnowledgeEntry] = []
    entries.extend(_from_evidence(artifacts))
    entries.extend(_from_profile(artifacts))
    entries.extend(_from_offer(artifacts))
    entries.extend(_from_audience(artifacts))
    entries.extend(_from_voice(artifacts))

    entries = _dedupe(entries)
    entries.sort(key=lambda entry: (-entry.value, entry.id))

    shelves = [
        KnowledgeShelf(
            category=category,
            label=SHELVES[category].label,
            blurb=SHELVES[category].blurb,
            buyer_question=SHELVES[category].buyer_question,
            sells_by=SHELVES[category].sells_by,
            when_empty=SHELVES[category].when_empty,
            entries=[entry for entry in entries if entry.category is category],
        )
        for category in CATEGORY_ORDER
    ]
    return KnowledgeBase(
        entries=entries,
        shelves=shelves,
        version=version or artifacts.version,
        compiled_at=artifacts.compiled_at,
        has_material=not artifacts.is_empty,
        open_questions=[
            f"{gap.missing} - {gap.impact}".rstrip(" -") for gap in artifacts.gaps.unanswered
        ],
    )


def _entry(
    *,
    id: str,
    statement: str,
    origin: EntryOrigin,
    kind: str = "",
    verbatim: str = "",
    source: str = "",
    document_id: str | None = None,
    grounding: Grounding = Grounding.GROUNDED,
    strength: str = "",
    category: FactCategory | None = None,
    citable: bool = False,
    tags: tuple[str, ...] = (),
    user_attested: bool = False,
) -> KnowledgeEntry:
    resolved = category or classify(f"{statement} {verbatim}", kind)
    value = assess_value(
        category=resolved,
        statement=statement,
        verbatim=verbatim,
        strength=strength,
        user_attested=user_attested,
    )
    return KnowledgeEntry(
        id=id,
        category=resolved,
        statement=_collapse(statement),
        verbatim=_collapse(verbatim, 400),
        source=source,
        document_id=document_id,
        origin=origin,
        kind=kind,
        grounding=grounding,
        strength=strength,
        value=value.score,
        band=value.band,
        why=value.reasons,
        citable=citable,
        tags=list(tags),
    )


def _from_evidence(artifacts: KnowledgeArtifacts) -> list[KnowledgeEntry]:
    """The ledger, which is the only part of the base a writer may cite.

    Scoring goes through the ledger's own helpers rather than being recomputed
    here, so a fact ranks identically whether an agent is choosing what to put
    in an email or a user is reading down the page.
    """
    results: list[KnowledgeEntry] = []
    for item in artifacts.evidence.entries:
        value = value_of(item)
        results.append(
            KnowledgeEntry(
                id=item.id,
                category=category_of(item),
                statement=_collapse(item.claim),
                verbatim=_collapse(item.verbatim, 400),
                source=item.source,
                document_id=item.document_id,
                origin=EntryOrigin.EVIDENCE,
                kind=str(item.kind),
                grounding=(
                    Grounding.USER_STATED if item.user_attested else Grounding.GROUNDED
                ),
                strength=str(item.strength),
                value=value.score,
                band=value.band,
                why=value.reasons,
                citable=True,
                tags=_evidence_tags(item),
            )
        )
    return results


def _evidence_tags(item: Evidence) -> list[str]:
    tags = [str(item.kind)]
    if item.user_attested:
        tags.append("you told us")
    if item.source:
        tags.append("cited")
    return tags


def _from_profile(artifacts: KnowledgeArtifacts) -> list[KnowledgeEntry]:
    business = artifacts.business
    results: list[KnowledgeEntry] = []

    if business.what_it_does:
        results.append(
            _entry(
                id="P-what",
                statement=f"{business.company_name or 'The company'}: {business.what_it_does}",
                origin=EntryOrigin.PROFILE,
                kind="positioning",
                category=FactCategory.PRODUCT,
                strength="moderate",
                tags=("identity",),
            )
        )
    if business.category:
        results.append(
            _entry(
                id="P-category",
                statement=f"A buyer would search for this as: {business.category}",
                origin=EntryOrigin.PROFILE,
                kind="positioning",
                category=FactCategory.MARKET,
                grounding=Grounding.INFERRED,
                tags=("identity",),
            )
        )
    if business.business_model:
        results.append(
            _entry(
                id="P-model",
                statement=f"How money changes hands: {business.business_model}",
                origin=EntryOrigin.PROFILE,
                kind="business model",
                category=FactCategory.COMMERCIAL,
                tags=("identity",),
            )
        )
    for index, fact in enumerate(business.facts, start=1):
        results.append(
            _entry(
                id=f"P{index}",
                statement=fact.statement,
                origin=EntryOrigin.PROFILE,
                kind="established fact",
                verbatim=fact.provenance.quote if fact.provenance else "",
                source=fact.provenance.source if fact.provenance else "",
                document_id=fact.provenance.document_id if fact.provenance else None,
                grounding=fact.grounding,
                strength="moderate" if fact.grounding is Grounding.GROUNDED else "weak",
            )
        )
    if business.vocabulary:
        results.append(
            _entry(
                id="P-vocabulary",
                statement="Words this company uses about itself: "
                + ", ".join(business.vocabulary),
                origin=EntryOrigin.PROFILE,
                kind="vocabulary",
                category=FactCategory.BRAND,
                tags=("voice",),
            )
        )
    return results


def _from_offer(artifacts: KnowledgeArtifacts) -> list[KnowledgeEntry]:
    offer = artifacts.offer
    results: list[KnowledgeEntry] = []

    for index, plan in enumerate(offer.plans, start=1):
        includes = f" Includes {', '.join(plan.includes)}." if plan.includes else ""
        results.append(
            _entry(
                id=f"O-plan{index}",
                statement=f"{plan.name}: {plan.price or 'price not published'}.{includes}",
                origin=EntryOrigin.OFFER,
                kind="plan",
                category=FactCategory.COMMERCIAL,
                strength="strong" if plan.price else "weak",
                tags=("pricing",),
            )
        )
    if offer.free_entry:
        results.append(
            _entry(
                id="O-free",
                statement=f"Free entry: {offer.free_entry}",
                origin=EntryOrigin.OFFER,
                kind="free entry",
                category=FactCategory.COMMERCIAL,
                strength="strong",
                tags=("pricing", "risk reversal"),
            )
        )
    for index, guarantee in enumerate(offer.guarantees, start=1):
        results.append(
            _entry(
                id=f"O-guarantee{index}",
                statement=guarantee,
                origin=EntryOrigin.OFFER,
                kind="guarantee",
                category=FactCategory.TRUST,
                strength="strong",
                tags=("risk reversal",),
            )
        )
    if offer.purchase_motion:
        results.append(
            _entry(
                id="O-motion",
                statement=f"How people buy: {offer.purchase_motion}",
                origin=EntryOrigin.OFFER,
                kind="purchase motion",
                category=FactCategory.COMMERCIAL,
                tags=("buying",),
            )
        )
    for index, cta in enumerate(offer.calls_to_action, start=1):
        detail = f" ({cta.intent})" if cta.intent else ""
        link = f" -> {cta.url}" if cta.url else ""
        results.append(
            _entry(
                id=f"O-cta{index}",
                statement=f"A reader can be asked to: {cta.label}{detail}{link}",
                origin=EntryOrigin.OFFER,
                kind="call to action",
                # Commercial rather than operations: what a reader can be
                # asked to do is how this business is bought, and it sits
                # next to the purchase motion that describes the same thing.
                category=FactCategory.COMMERCIAL,
                strength="strong",
                tags=("call to action",),
            )
        )
    return results


def _from_audience(artifacts: KnowledgeArtifacts) -> list[KnowledgeEntry]:
    results: list[KnowledgeEntry] = []

    for index, segment in enumerate(artifacts.audience.segments, start=1):
        detail = " ".join(
            part
            for part in (
                segment.situation,
                f"They are trying to {segment.job_to_be_done}." if segment.job_to_be_done else "",
                f"They start looking when {segment.trigger}." if segment.trigger else "",
            )
            if part
        )
        results.append(
            _entry(
                id=f"A-segment{index}",
                statement=f"{segment.name}. {detail}",
                origin=EntryOrigin.AUDIENCE,
                kind="segment",
                category=FactCategory.MARKET,
                grounding=Grounding.INFERRED,
                strength="moderate",
                tags=("who buys", str(segment.sophistication).replace("_", " ")),
            )
        )
        for pain_index, pain in enumerate(segment.pains, start=1):
            results.append(
                _entry(
                    id=f"A-pain{index}.{pain_index}",
                    statement=f"{segment.name} - what it costs them today: {pain.statement}",
                    origin=EntryOrigin.AUDIENCE,
                    kind="pain",
                    category=FactCategory.MARKET,
                    verbatim=pain.provenance.quote if pain.provenance else "",
                    source=pain.provenance.source if pain.provenance else "",
                    grounding=pain.grounding,
                    tags=("pain",),
                )
            )

    for index, objection in enumerate(artifacts.audience.objections, start=1):
        answered = objection.answer or "nothing in the material answers this yet"
        cites = f" [{', '.join(objection.evidence_ids)}]" if objection.evidence_ids else ""
        results.append(
            _entry(
                id=f"A-objection{index}",
                statement=f'They say no because: "{objection.objection}". Answered by: '
                f"{answered}{cites}",
                origin=EntryOrigin.AUDIENCE,
                kind="objection",
                category=FactCategory.MARKET,
                grounding=objection.grounding,
                strength="strong" if objection.evidence_ids else "weak",
                tags=("objection", objection.severity),
            )
        )
    return results


def _from_voice(artifacts: KnowledgeArtifacts) -> list[KnowledgeEntry]:
    voice = artifacts.voice
    results: list[KnowledgeEntry] = []

    descriptors = [
        ("tone", voice.tone),
        ("rhythm", voice.rhythm),
        ("person", voice.person),
    ]
    for name, text in descriptors:
        if not text:
            continue
        results.append(
            _entry(
                id=f"V-{name}",
                statement=f"{name.title()}: {text}",
                origin=EntryOrigin.VOICE,
                kind=name,
                category=FactCategory.BRAND,
                grounding=Grounding.GROUNDED if voice.learned else Grounding.INFERRED,
                tags=("voice", "learned" if voice.learned else "house default"),
            )
        )
    for index, passage in enumerate(voice.exemplars, start=1):
        results.append(
            _entry(
                id=f"V-exemplar{index}",
                statement="A passage this company actually published",
                origin=EntryOrigin.VOICE,
                kind="exemplar",
                verbatim=passage,
                category=FactCategory.BRAND,
                strength="strong",
                tags=("voice", "verbatim"),
            )
        )
    return results


def _dedupe(entries: list[KnowledgeEntry]) -> list[KnowledgeEntry]:
    """Drop the second copy of a fact the compiler wrote down twice.

    The profile's `facts` and the evidence ledger are extracted by different
    passes over the same pages, so a business's one memorable number often
    lands in both. Evidence wins because it is the citable one - it is built
    first, so first-seen is the right rule.
    """
    seen: set[str] = set()
    kept: list[KnowledgeEntry] = []
    for entry in entries:
        key = _WHITESPACE_RE.sub(" ", entry.statement.lower()).strip().rstrip(".")
        if key and key in seen:
            continue
        seen.add(key)
        kept.append(entry)
    return kept


def _collapse(text: str, limit: int | None = None) -> str:
    flat = _WHITESPACE_RE.sub(" ", text).strip()
    if limit is not None and len(flat) > limit:
        return flat[:limit].rstrip() + "…"
    return flat
