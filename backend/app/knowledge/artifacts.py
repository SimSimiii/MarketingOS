"""The distilled knowledge every campaign is written from.

The old system put raw website markdown in front of every model call, newest
document first, truncated at four thousand characters each. That is the wrong
shape twice over: the writer re-reads a navigation menu on every call and pays
for it, and a pricing table halfway down a long page never reaches any model
at all.

These artifacts are what replaces it. Source material is read once, distilled
into six small structured documents, and those are what get inlined into
prompts - in full, because they are small by construction. Every factual entry
carries the quote that supports it, so nothing downstream has to take the
compiler's word for anything.

They belong to the business, not to one campaign: the second campaign for the
same product starts from everything the first one learned.
"""

import re
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from app.knowledge.ledger import EvidenceLedger


class Grounding(StrEnum):
    """Where a statement came from. The distinction is the whole reason to
    trust an artifact: a persona the compiler reasoned its way to is useful,
    but it must never be presented to a writer as something the company said."""

    GROUNDED = "grounded"
    INFERRED = "inferred"
    USER_STATED = "user_stated"


class Provenance(BaseModel):
    source: str = ""
    quote: str = ""
    document_id: str | None = None


class Fact(BaseModel):
    statement: str
    grounding: Grounding = Grounding.INFERRED
    provenance: Provenance | None = None

    def render(self) -> str:
        mark = {Grounding.GROUNDED: "", Grounding.INFERRED: " (inferred)",
                Grounding.USER_STATED: " (the user told us)"}[self.grounding]
        return f"{self.statement}{mark}"


def _render_facts(facts: list[Fact], empty: str) -> str:
    return "\n".join(f"- {fact.render()}" for fact in facts) or f"- {empty}"


def _render_list(items: list[str], empty: str) -> str:
    return "\n".join(f"- {item}" for item in items) or f"- {empty}"


_WORD_RE = re.compile(r"[a-z0-9]+")

#: How many meaningful words two descriptions of a person must share before
#: they are taken to be the same person. Two is enough for "solo founder with
#: early traction" to find "Founder with Early Traction Building First AI
#: Feature" and low enough that it costs nothing when a brief names its
#: segment outright, which is the normal case.
_MIN_SEGMENT_OVERLAP = 2

#: Words that appear in every description of every buyer and so carry no
#: signal about which buyer is meant.
_STOPWORDS = frozenset(
    {
        "with", "that", "this", "their", "they", "them", "from", "have", "having",
        "into", "your", "yours", "about", "using", "used", "when", "what", "who",
        "whose", "which", "been", "being", "some", "someone", "people", "person",
        "team", "teams", "company", "companies", "business", "businesses",
        "customer", "customers", "user", "users", "product", "products",
    }
)


def _significant_words(text: str) -> set[str]:
    return {
        word
        for word in _WORD_RE.findall(text.lower())
        if len(word) > 3 and word not in _STOPWORDS
    }


# ------------------------------------------------------------------- business


class BusinessProfile(BaseModel):
    """What this company is, in enough detail to stop a writer being generic."""

    company_name: str = ""
    what_it_does: str = ""
    category: str = ""
    business_model: str = ""
    facts: list[Fact] = Field(default_factory=list)
    #: The words this company actually uses about itself. Copy that reuses
    #: them sounds like the company; copy that invents synonyms sounds like
    #: an agency that skimmed the site.
    vocabulary: list[str] = Field(default_factory=list)

    def render(self) -> str:
        return (
            f"Company: {self.company_name or 'not named in the material'}\n"
            f"What it does: {self.what_it_does or 'unclear from the material'}\n"
            f"Category: {self.category or 'unclear'}\n"
            f"Business model: {self.business_model or 'unclear'}\n"
            f"Established facts:\n{_render_facts(self.facts, 'nothing established')}\n"
            f"Words they use about themselves: "
            f"{', '.join(self.vocabulary) or 'none captured'}"
        )


# ---------------------------------------------------------------------- offer


class Plan(BaseModel):
    name: str
    price: str = ""
    includes: list[str] = Field(default_factory=list)


class CallToAction(BaseModel):
    """Something a reader can actually be asked to do.

    An email that asks for a demo when the product is self-serve is worse than
    a weak email: it sends the reader somewhere that does not exist. Writers
    may only ask for things on this list.
    """

    label: str
    intent: str = ""
    url: str | None = None


class OfferSheet(BaseModel):
    plans: list[Plan] = Field(default_factory=list)
    free_entry: str = ""
    guarantees: list[str] = Field(default_factory=list)
    calls_to_action: list[CallToAction] = Field(default_factory=list)
    purchase_motion: str = ""

    def render(self) -> str:
        plans = "\n".join(
            f"- {plan.name}: {plan.price or 'price not published'}"
            + (f" - includes {', '.join(plan.includes)}" if plan.includes else "")
            for plan in self.plans
        ) or "- no plans or prices found in the material"
        ctas = "\n".join(
            f"- {cta.label}" + (f" ({cta.intent})" if cta.intent else "")
            + (f" -> {cta.url}" if cta.url else "")
            for cta in self.calls_to_action
        ) or "- none found - ask only for a reply"
        return (
            f"Plans:\n{plans}\n"
            f"Free entry: {self.free_entry or 'none found'}\n"
            f"Guarantees: {', '.join(self.guarantees) or 'none found'}\n"
            f"How people buy: {self.purchase_motion or 'unclear'}\n"
            f"Actions a reader can be asked to take:\n{ctas}"
        )


# ---------------------------------------------------------------------- voice


class VoiceProfile(BaseModel):
    """How this company sounds, learned from its own copy where any exists.

    `exemplars` matter more than every adjective in this model put together.
    Telling a writer "warm but direct" produces the average of every email
    ever written; showing it three paragraphs the company actually sent
    produces that company's voice.
    """

    learned: bool = False
    tone: str = ""
    rhythm: str = ""
    person: str = ""
    greetings: list[str] = Field(default_factory=list)
    sign_offs: list[str] = Field(default_factory=list)
    exemplars: list[str] = Field(default_factory=list)
    prefer_words: list[str] = Field(default_factory=list)
    avoid_words: list[str] = Field(default_factory=list)

    @classmethod
    def house_default(cls) -> "VoiceProfile":
        """What the system sounds like when the user gave it nothing to learn
        from. Recorded as an explicit artifact rather than left implicit in a
        prompt, so the user can see the choice that was made for them."""
        return cls(
            learned=False,
            tone="plain and direct - one person writing to one person, no marketing register",
            rhythm="short opening line, paragraphs of one to three lines, varied sentence length",
            person="first person singular, signed by a name or the product team",
            greetings=["Hi there,"],
            sign_offs=["- the team"],
        )

    def render(self) -> str:
        exemplars = "\n\n".join(f"    {passage}" for passage in self.exemplars)
        learned = (
            "Learned from copy this company actually sent."
            if self.learned
            else "No existing copy was provided - this is the system default, not their voice."
        )
        block = (
            f"{learned}\n"
            f"Register: {self.tone}\n"
            f"Rhythm: {self.rhythm}\n"
            f"Person: {self.person}\n"
            f"Greetings they use: {', '.join(self.greetings) or 'none captured'}\n"
            f"Sign-offs they use: {', '.join(self.sign_offs) or 'none captured'}\n"
        )
        if self.prefer_words:
            block += f"Words they reach for: {', '.join(self.prefer_words)}\n"
        if self.avoid_words:
            block += f"Words they never use: {', '.join(self.avoid_words)}\n"
        if exemplars:
            block += f"\nPassages they actually sent - match this, do not describe it:\n\n{exemplars}"
        return block


# ------------------------------------------------------------------- audience


class Sophistication(StrEnum):
    """How much the reader already knows. It decides where an email can start:
    a product-aware reader does not need the problem explained, and explaining
    it anyway is how an email loses them in the first two lines."""

    UNAWARE = "unaware"
    PROBLEM_AWARE = "problem_aware"
    SOLUTION_AWARE = "solution_aware"
    PRODUCT_AWARE = "product_aware"
    MOST_AWARE = "most_aware"


#: What a reader at each awareness stage does not need explained, and what
#: they do. The stage is decided by the compiler and used by the strategist,
#: but the sentence that makes it actionable belongs next to the enum: telling
#: a writer "sophistication: solution_aware" communicates nothing a writer can
#: act on, and it is the one line that decides where an email may open.
_WHERE_TO_START: dict["Sophistication", str] = {
    "unaware": (
        "They do not know they have this problem. Name what is happening to them before "
        "you name anything else - and never assume they are looking for a fix."
    ),
    "problem_aware": (
        "They know the problem and have not gone looking for a fix. Do not explain the "
        "problem back to them; show that it is solvable at all."
    ),
    "solution_aware": (
        "They know fixes like this exist and are probably doing something manual instead. "
        "Explaining what the category is loses them - go straight at why this one is "
        "different from what they do today."
    ),
    "product_aware": (
        "They already know roughly what this product is. Explaining it again loses them in "
        "two lines - answer the thing that has stopped them signing up."
    ),
    "most_aware": (
        "They know the product and are close. They need a reason that this is the moment, "
        "not another description of what it does."
    ),
}


class Segment(BaseModel):
    """One buyer, specific enough to write to. "Small business owners" is not
    a segment; "a solo consultant losing an evening a week to invoicing" is."""

    name: str
    situation: str = ""
    job_to_be_done: str = ""
    trigger: str = ""
    sophistication: Sophistication = Sophistication.PROBLEM_AWARE
    pains: list[Fact] = Field(default_factory=list)

    def render(self) -> str:
        return (
            f"- {self.name}\n"
            f"    situation: {self.situation or 'unspecified'}\n"
            f"    what they are trying to get done: {self.job_to_be_done or 'unspecified'}\n"
            f"    what makes them start looking: {self.trigger or 'unspecified'}\n"
            f"    how much they already know: {self.sophistication}\n"
            f"    what hurts: "
            + ("; ".join(pain.render() for pain in self.pains) or "not established")
        )

    def render_for_writing(self) -> str:
        """The person, addressed to whoever has to write the first sentence.

        Same facts as `render`, arranged as instructions rather than as a
        record. The writer is told to "open on the reader's situation, in the
        words they would use for it themselves" - and used to hold exactly one
        sentence about that situation beside twenty thousand characters about
        the product, which is how an email becomes a product description.
        """
        pains = "\n".join(f"    - {pain.render()}" for pain in self.pains)
        return (
            f"{self.name}\n\n"
            f"Their situation right now: {self.situation or 'not established'}\n"
            f"What they are actually trying to get done: "
            f"{self.job_to_be_done or 'not established'}\n"
            f"What makes someone like this start looking: "
            f"{self.trigger or 'not established'}\n"
            + (f"What it costs them today:\n{pains}\n" if pains else "")
            + f"\nWhere you can start: {_WHERE_TO_START.get(str(self.sophistication), '')}"
        )


class Objection(BaseModel):
    """A reason this person does not buy. The writer answers these by name;
    `answer` is what in the evidence lets them."""

    objection: str
    severity: str = "strong"
    answer: str = ""
    grounding: Grounding = Grounding.INFERRED
    evidence_ids: list[str] = Field(default_factory=list)

    def render(self) -> str:
        answer = self.answer or "nothing in the material answers this yet"
        ids = f" [{', '.join(self.evidence_ids)}]" if self.evidence_ids else ""
        return f"- ({self.severity}) {self.objection}\n    answered by: {answer}{ids}"


class AudienceModel(BaseModel):
    segments: list[Segment] = Field(default_factory=list)
    objections: list[Objection] = Field(default_factory=list)

    def render(self) -> str:
        segments = "\n".join(segment.render() for segment in self.segments) or "- not established"
        objections = (
            "\n".join(objection.render() for objection in self.objections) or "- not established"
        )
        return f"Segments:\n{segments}\n\nWhy they say no:\n{objections}"

    def primary(self) -> Segment | None:
        return self.segments[0] if self.segments else None

    def match(self, name: str, description: str = "") -> Segment | None:
        """The segment a campaign brief means, or None if it named nobody here.

        A campaign is written to one of these people and must be judged by
        that same person. Falling back to `primary()` when the brief named
        someone else is not a small inaccuracy - it grades an email against a
        reader who does not have the problem the email opens on, and every
        rewrite driven by that reading makes the copy worse for the person it
        was written for.

        Matching is forgiving on purpose. The name comes back from a model
        that was shown this list, so it is usually exact, but a strategist
        that writes "the solo founder" for "Founder with early traction" has
        still picked correctly, and being strict here lands on the fallback
        this method exists to avoid.
        """
        if not self.segments:
            return None
        wanted = " ".join(name.lower().split())
        if wanted:
            for segment in self.segments:
                if " ".join(segment.name.lower().split()) == wanted:
                    return segment
            for segment in self.segments:
                known = " ".join(segment.name.lower().split())
                if known and (wanted in known or known in wanted):
                    return segment
        # Nothing matched by name. The brief still described a person in
        # `reader`, and that sentence was written from one of these segments.
        probe = _significant_words(f"{name} {description}")
        if not probe:
            return None
        scored = [
            (len(probe & _significant_words(f"{item.name} {item.situation}")), item)
            for item in self.segments
        ]
        overlap, segment = max(scored, key=lambda pair: pair[0])
        return segment if overlap >= _MIN_SEGMENT_OVERLAP else None


# ----------------------------------------------------------------------- gaps


class Gap(BaseModel):
    """Something the compiler could not establish, and what it costs.

    A gap is only worth reporting if it changes the copy. "No employee count"
    is not a gap; "no price anywhere in the material" is, because it decides
    whether an email can name one.
    """

    id: str
    missing: str
    impact: str = ""
    question: str = ""
    severity: str = "significant"
    answer: str = ""

    def render(self) -> str:
        answered = f"\n    the user answered: {self.answer}" if self.answer else ""
        return f"- [{self.id}] ({self.severity}) {self.missing} - {self.impact}{answered}"


class GapReport(BaseModel):
    gaps: list[Gap] = Field(default_factory=list)

    @property
    def unanswered(self) -> list[Gap]:
        return [gap for gap in self.gaps if not gap.answer]

    @property
    def blocking(self) -> list[Gap]:
        return [gap for gap in self.unanswered if gap.severity == "blocking"]

    def render(self) -> str:
        return "\n".join(gap.render() for gap in self.gaps) or "- nothing material is missing"


# ------------------------------------------------------------------ the bundle


class KnowledgeArtifacts(BaseModel):
    """Everything the system knows about one business, at one point in time."""

    business: BusinessProfile = Field(default_factory=BusinessProfile)
    offer: OfferSheet = Field(default_factory=OfferSheet)
    evidence: EvidenceLedger = Field(default_factory=EvidenceLedger)
    voice: VoiceProfile = Field(default_factory=VoiceProfile.house_default)
    audience: AudienceModel = Field(default_factory=AudienceModel)
    gaps: GapReport = Field(default_factory=GapReport)

    version: int = 1
    compiled_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    source_document_ids: list[str] = Field(default_factory=list)
    #: Documents that existed but were not readable, so a thin profile is
    #: explainable rather than mysterious.
    notes: list[str] = Field(default_factory=list)

    def render_for_strategy(self) -> str:
        """Everything, for the one role that decides what the campaign says."""
        return (
            f"## The business\n{self.business.render()}\n\n"
            f"## What they sell\n{self.offer.render()}\n\n"
            f"## Who buys\n{self.audience.render()}\n\n"
            f"## Evidence available (cite these ids)\n{self.evidence.render()}\n\n"
            f"## How they sound\n{self.voice.render()}\n\n"
            f"## What we could not establish\n{self.gaps.render()}"
        )

    def render_for_writing(self, evidence: EvidenceLedger | None = None) -> str:
        """What a writer needs at the moment of writing. The gap report and
        the business model are strategy's problem, not the writer's - by the
        time a brief exists those decisions are already made.

        `evidence` is the slice this email is written from (see
        EvidenceLedger.slice_for). Passing the whole ledger still works and is
        what a caller with no brief in hand should do; passing the slice is
        what stops a 121-entry inventory being the loudest thing in a prompt
        whose brief assigned three facts.
        """
        ledger = self.evidence if evidence is None else evidence
        return (
            f"## The business\n{self.business.render()}\n\n"
            f"## What they sell\n{self.offer.render()}\n\n"
            f"## Evidence you may use (nothing outside this list)\n{ledger.render()}"
        )

    def objection_detail(self, objection: str) -> str:
        """The full entry for an objection a brief named, with what answers it.

        The brief carries the objection as one line of text. That line says
        what the reader's doubt is and nothing about what in the material
        resolves it - so a writer told to "answer the no" has been told the
        no and not the answer, and writes around it.
        """
        if not objection:
            return "This email was assigned no particular objection to answer."
        wanted = _significant_words(objection)
        best: Objection | None = None
        overlap = 0
        for candidate in self.audience.objections:
            score = len(wanted & _significant_words(candidate.objection))
            if score > overlap:
                best, overlap = candidate, score
        if best is None or overlap < _MIN_SEGMENT_OVERLAP:
            return (
                f"{objection}\n"
                "    Nothing in the audience model matches this objection, so nothing here "
                "tells you what answers it - answer it from the evidence or leave it alone."
            )
        return best.render()

    @property
    def is_empty(self) -> bool:
        return not (
            self.business.what_it_does or self.evidence.entries or self.audience.segments
        )
