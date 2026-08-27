"""What a company asserts on its own pages, and how two assertions are compared.

The comparison is the load-bearing part, and it is deterministic on purpose.
Asking a model "is our claim different from theirs?" gets an answer shaped by
whichever claim was written more confidently; asking it "what axis is this
claim on?" gets an answer it is reliably good at, and leaves the comparison to
code that always returns the same verdict for the same inputs.

So a claim is extracted with an **axis** - the dimension it competes on - and
positioning is arithmetic over axes. That distinction matters more than it
looks. "First API call in under 5 minutes" and "get started in ten minutes,
not ten days" share not one distinctive word, and they are the *same claim*:
both bet the sale on setup speed. A reader deciding between the two products
does not experience them as two different promises, and copy that leads on
speed against a field that all leads on speed is invisible however precisely
it is worded.

Two levels of comparison, for two different consumers:

- **Axis overlap** decides positioning. It answers "what can we lead on?", and
  it is what the Strategist is planned against.
- **Phrase overlap** decides sameness. It answers "could this exact sentence
  have been pasted from a competitor?", and it is what the gate checks on
  every draft.
"""

import re
from enum import StrEnum

from pydantic import BaseModel, Field


class ClaimAxis(StrEnum):
    """The dimension a claim competes on.

    A closed list, and short. An open one is a taxonomy nobody can compare
    across - two competitors' claims tagged `developer_experience` and
    `ease_of_use` are on the same axis in every way that matters to a buyer,
    and on different ones to any code reading the strings. Anything that does
    not fit lands on `OTHER` and is reported rather than silently forced onto
    a neighbour.
    """

    #: How fast it is to start, to run, or to get a result.
    SPEED = "speed"
    #: What it costs, how it is charged, what is free.
    PRICE = "price"
    #: How much it covers - models, integrations, channels, formats.
    BREADTH = "breadth"
    #: How well it works: accuracy, reliability, uptime, quality of output.
    QUALITY = "quality"
    #: How little the buyer has to do: no code, no setup, no hire.
    EFFORT = "effort"
    #: How much the buyer keeps their hands on: self-hosting, portability,
    #: no lock-in, open source.
    CONTROL = "control"
    #: Compliance, privacy, certification, data handling.
    SECURITY = "security"
    #: Who else uses it and what happened to them.
    PROOF = "proof"
    #: Humans, onboarding, migration help, SLAs.
    SUPPORT = "support"
    #: Something that does not fit the list above.
    OTHER = "other"


#: Which axes a stranger can check for themselves in the time it takes to read
#: an email, and which ones they can only be asked to believe. Not a ranking of
#: importance - a ranking of what survives first contact with someone who has
#: never heard of you, which is the only audience cold copy has.
_CHECKABLE_AXES = frozenset(
    {ClaimAxis.PRICE, ClaimAxis.BREADTH, ClaimAxis.SPEED, ClaimAxis.SECURITY}
)


class Claim(BaseModel):
    """One assertion, in the words the company used, on one axis."""

    #: The claim as a buyer would summarise it: "first API call in 5 minutes".
    text: str
    #: The exact words on the page. This is what licenses everything else,
    #: exactly as `Evidence.verbatim` does - a claim we cannot quote is a
    #: claim we made up on somebody else's behalf.
    verbatim: str = ""
    #: Where it was read. A URL for a rival, a document title for us.
    source: str = ""
    axis: ClaimAxis = ClaimAxis.OTHER
    #: Whether the claim carries something a reader could check: a figure, a
    #: named limit, a named customer. Set by the extractor and re-derived when
    #: it is not - see `is_specific`.
    specific: bool | None = None

    @property
    def is_specific(self) -> bool:
        """Whether there is anything in here a reader could verify.

        Derived when the extractor did not say, because a specific claim and a
        confident one look identical to everything downstream that only reads
        `text`, and the difference is the entire distance between "25 models
        across 9 providers" and "the broadest model coverage available".
        """
        if self.specific is not None:
            return self.specific
        return bool(_FIGURE_RE.search(f"{self.text} {self.verbatim}"))

    @property
    def checkable_axis(self) -> bool:
        return self.axis in _CHECKABLE_AXES

    def render(self) -> str:
        mark = "" if self.is_specific else " (no figure - assertion only)"
        where = f" - {self.source}" if self.source else ""
        return f"[{self.axis}] {self.text}{mark}{where}"


_FIGURE_RE = re.compile(
    r"\d|\bzero\b|\bno\s+(?:card|code|setup|contract|commitment)\b", re.IGNORECASE
)

_WORD_RE = re.compile(r"[a-z0-9][a-z0-9'+-]*")

#: Words that appear in every company's claims and therefore separate none of
#: them. Deliberately larger than the knowledge layer's stopword list: this one
#: is used to decide whether a *sentence* is interchangeable, and marketing
#: copy is built almost entirely out of words like these.
_STOPWORDS = frozenset(
    {
        "the", "and", "for", "with", "from", "that", "this", "your", "you", "our", "we",
        "are", "can", "will", "have", "has", "not", "but", "all", "any", "get", "got",
        "one", "out", "its", "it's", "into", "than", "then", "them", "they", "their",
        "what", "when", "who", "how", "why", "was", "were", "been", "being", "more",
        "most", "much", "some", "just", "only", "also", "even", "over", "under", "up",
        "down", "off", "own", "same", "such", "each", "every", "other", "another",
        "new", "now", "today", "here", "there", "about", "without", "within", "across",
        "before", "after", "while", "still", "never", "always", "make", "makes", "made",
        "take", "takes", "use", "uses", "using", "used", "need", "needs", "want",
        "wants", "help", "helps", "let", "lets", "give", "gives", "run", "runs",
        # the words every B2B product says about itself
        "platform", "solution", "software", "tool", "tools", "product", "service",
        "system", "team", "teams", "company", "business", "customer", "customers",
        "user", "users", "people", "work", "works", "working", "build", "building",
        "built", "start", "started", "starting", "ship", "ships", "shipping",
        "best", "better", "great", "good", "easy", "easily", "simple", "simply",
        "fast", "faster", "quick", "quickly", "powerful", "modern", "leading",
    }
)


def significant_words(text: str) -> set[str]:
    """The words in a phrase that could tell one company apart from another.

    Everything a comparison here rests on: two sentences whose distinctive
    words are the same sentence, whatever the connective tissue between them.
    """
    return {
        word
        for word in _WORD_RE.findall(text.lower())
        if len(word) > 2 and word not in _STOPWORDS
    }


def overlap(left: str, right: str) -> float:
    """How much two phrases say the same thing, 0 to 1.

    Jaccard over significant words. Crude, and correctly crude: this decides
    whether to *show* a user two claims side by side, never whether to block
    anything, and a measure a user can re-derive by eye beats one they have to
    trust.
    """
    first, second = significant_words(left), significant_words(right)
    if not first or not second:
        return 0.0
    return len(first & second) / len(first | second)


#: How much two claims must share before they are shown as the same claim
#: worded differently. Low, because the axis has usually already established
#: that they compete; this only decides whether to present them as one row.
SAME_CLAIM_OVERLAP = 0.34


def same_claim(left: Claim, right: Claim) -> bool:
    """Whether two claims are the same bet.

    The axis first, because that is what a buyer compares. Wording second, and
    only as a tie-break inside `OTHER` - the bucket that exists precisely
    because its members have nothing structural in common, so an axis match
    there means nothing and the words have to carry it.
    """
    if left.axis is not right.axis:
        return False
    if left.axis is ClaimAxis.OTHER:
        return overlap(left.text, right.text) >= SAME_CLAIM_OVERLAP
    return True


class ClaimSet(BaseModel):
    """Every claim one company makes, in one place."""

    claims: list[Claim] = Field(default_factory=list)

    @property
    def axes(self) -> set[ClaimAxis]:
        return {claim.axis for claim in self.claims}

    def on(self, axis: ClaimAxis) -> list[Claim]:
        return [claim for claim in self.claims if claim.axis is axis]

    @property
    def specific(self) -> list[Claim]:
        return [claim for claim in self.claims if claim.is_specific]

    def vocabulary(self) -> set[str]:
        """Every distinctive word this company spends on its claims. The raw
        material of the sameness check: a sentence built only from words that
        appear in this set for *several* companies is a sentence any of them
        could have sent."""
        words: set[str] = set()
        for claim in self.claims:
            words |= significant_words(f"{claim.text} {claim.verbatim}")
        return words

    def render(self, limit: int = 12) -> str:
        return (
            "\n".join(f"- {claim.render()}" for claim in self.claims[:limit])
            or "- nothing captured"
        )
