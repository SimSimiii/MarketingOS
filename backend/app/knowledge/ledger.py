"""The Evidence Ledger and the claim checker built on it.

This is the load-bearing idea of the knowledge layer. Telling a copywriter
"never invent a statistic" is an instruction, and instructions are followed
approximately. An email that says "set up in 8 minutes" when the site says ten
is not a style problem - it is the one failure a paying client notices
immediately, and it is invisible to any reviewer that reads the draft on its
own.

So the writer is given an inventory of what is true, every entry carrying the
verbatim text that supports it, and a deterministic gate reads the finished
draft back: every quantified claim, every quoted passage and every URL in the
copy must be licensed by that inventory or by the user's own material. No
model is asked whether the draft is honest - the question is answered by
string matching, for free, on every draft.

What is deliberately NOT checked: bare single-digit numbers ("three reasons to
switch"), which are rhetoric far more often than claims. Flagging those would
train everyone to ignore the gate, and a gate that gets ignored protects
nothing.
"""

import re
from enum import StrEnum

from pydantic import BaseModel, Field

from app.knowledge.corpus import fold
from app.knowledge.taxonomy import (
    CommercialValue,
    FactCategory,
    ValueBand,
    assess_value,
    classify,
)


class EvidenceKind(StrEnum):
    """What kind of true thing an entry is. The writer picks evidence by what
    it can do in an email - a metric opens, a testimonial answers a doubt."""

    METRIC = "metric"
    PRICE = "price"
    TESTIMONIAL = "testimonial"
    CUSTOMER = "customer"
    INTEGRATION = "integration"
    FEATURE = "feature"
    GUARANTEE = "guarantee"
    CERTIFICATION = "certification"
    AWARD = "award"


class EvidenceStrength(StrEnum):
    """How much weight a claim can rest on this. Strong = a specific, verifiable
    fact stated by the company itself; weak = real but vague."""

    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"


class Evidence(BaseModel):
    """One thing the copy is allowed to assert, and the text that proves it."""

    id: str
    kind: EvidenceKind
    #: The claim in a form a writer could use in a sentence.
    claim: str
    #: Verbatim text from the user's material. This is what licenses the
    #: numbers and names in `claim` - never paraphrase it.
    verbatim: str
    source: str = ""
    document_id: str | None = None
    strength: EvidenceStrength = EvidenceStrength.MODERATE
    #: Set by the compiler when a fact came from the user answering a gap
    #: question rather than from a document.
    user_attested: bool = False
    #: Which shelf of the knowledge base this sits on. Optional because
    #: artifact sets compiled before the taxonomy existed do not carry one,
    #: and `category_of` derives it for them at read time - a stored value
    #: costs nothing and a derived one costs a regex, so neither case needs a
    #: migration or a recompile.
    category: FactCategory | None = None

    @property
    def licensing_text(self) -> str:
        return f"{self.claim}\n{self.verbatim}"


def category_of(entry: Evidence) -> FactCategory:
    """The shelf for one fact, stored if the compiler set one, derived if not."""
    if entry.category is not None:
        return entry.category
    return classify(f"{entry.claim} {entry.verbatim}", str(entry.kind))


def value_of(entry: Evidence) -> CommercialValue:
    """What one fact is worth to a sale, and why. Always derived - the inputs
    are all on the entry, so a stored copy could only ever go stale."""
    return assess_value(
        category=category_of(entry),
        statement=entry.claim,
        verbatim=entry.verbatim,
        strength=str(entry.strength),
        user_attested=entry.user_attested,
    )


#: How many facts reach a writing or critiquing call. Comfortably more than
#: the three a brief may assign - the writer still needs the price, the CTA
#: and whatever answers the objection - and far below the hundred-plus a real
#: compile produces.
MAX_EVIDENCE_IN_PROMPT = 15

def _by_commercial_value(entries: list[Evidence]) -> list[Evidence]:
    """The facts a cold reader actually moves on, strongest first.

    This used to be a fixed list of kinds - testimonial, then customer, then
    metric, then guarantee, then price - which is the right ranking of kinds
    and the wrong ranking of facts. Under it a `feature` entry reading "SOC 2
    Type II, audited by Prescient in March" lost to every price on the page,
    because two thirds of a real ledger arrives labelled `feature` and the
    kind was the only thing being read. The scorer reads the entry: what it
    says, whether anybody is named in it, whether there is a number in it at
    all. See app.knowledge.taxonomy.
    """
    ranked = sorted(
        enumerate(entries), key=lambda pair: (-value_of(pair[1]).score, pair[0])
    )
    return [entry for _, entry in ranked]


class EvidenceLedger(BaseModel):
    """Everything true about this business, in one inventory."""

    entries: list[Evidence] = Field(default_factory=list)

    def get(self, evidence_id: str) -> Evidence | None:
        return next((entry for entry in self.entries if entry.id == evidence_id), None)

    def of_kind(self, *kinds: EvidenceKind) -> list[Evidence]:
        return [entry for entry in self.entries if entry.kind in kinds]

    def of_category(self, *categories: FactCategory) -> list[Evidence]:
        """Every fact on one shelf of the knowledge base."""
        return [entry for entry in self.entries if category_of(entry) in categories]

    def headline_facts(self) -> list[Evidence]:
        """The entries strong enough to carry an email on their own."""
        return [
            entry
            for entry in _by_commercial_value(self.entries)
            if value_of(entry).band is ValueBand.HEADLINE
        ]

    @property
    def ids(self) -> set[str]:
        return {entry.id for entry in self.entries}

    def render(self) -> str:
        return render_entries(self.entries)

    def slice_for(
        self,
        assigned_ids: list[str],
        objection: str = "",
        cap: int = MAX_EVIDENCE_IN_PROMPT,
        excluded_ids: set[str] | frozenset[str] = frozenset(),
    ) -> "EvidenceLedger":
        """The facts one email plausibly needs, out of everything true.

        The whole ledger used to go into every writer and critic call. For a
        real business that is ~18,000 characters, re-sent on every attempt -
        the single largest line in a campaign's bill, and it points the wrong
        way twice over. The brief assigns at most three facts and names what
        the email must leave out; handing the writer 121 of them alongside
        those instructions is putting the temptation and the prohibition in
        the same prompt, and the prompt's centre of gravity decides which one
        wins.

        Kept, in order: the facts this email was assigned, then anything that
        looks like an answer to the objection it has to beat, then whatever is
        worth the most commercially - see `_by_commercial_value`. Deliberately
        not "the first N": an arbitrary prefix of the ledger is how the
        assigned evidence ends up missing from the writer's own evidence list.

        Nothing is lost by this. The evidence *gate* still reads the finished
        draft against the complete ledger and the raw corpus, for free, so a
        fact outside the slice that the writer happens to know is still
        licensed - it simply stops being shouted at every draft.
        """
        by_id = {
            entry.id: entry for entry in self.entries if entry.id not in excluded_ids
        }
        kept: list[Evidence] = [
            by_id[id_] for id_ in dict.fromkeys(assigned_ids) if id_ in by_id
        ]
        seen = {entry.id for entry in kept}

        eligible = [entry for entry in self.entries if entry.id not in excluded_ids]
        for entry in _answering(eligible, objection):
            if entry.id not in seen and len(kept) < cap:
                kept.append(entry)
                seen.add(entry.id)

        for entry in _by_commercial_value(eligible):
            if entry.id not in seen and len(kept) < cap:
                kept.append(entry)
                seen.add(entry.id)
        return EvidenceLedger(entries=kept)


def _answering(entries: list[Evidence], objection: str) -> list[Evidence]:
    """Entries that share meaningful words with the objection this email has
    to beat. Crude on purpose: it is a retrieval hint feeding a cap, not a
    ranking anyone downstream depends on."""
    probe = {
        word
        for word in re.findall(r"[a-z0-9]{4,}", objection.lower())
        if word not in _OBJECTION_STOPWORDS
    }
    if not probe:
        return []
    scored = [
        (len(probe & set(re.findall(r"[a-z0-9]{4,}", entry.licensing_text.lower()))), entry)
        for entry in entries
    ]
    return [entry for overlap, entry in sorted(scored, key=lambda p: -p[0]) if overlap]


_OBJECTION_STOPWORDS = frozenset(
    {"already", "have", "this", "that", "with", "would", "them", "they", "there", "just", "does"}
)


def render_entries(entries: list[Evidence]) -> str:
    """The inventory as a writer or critic reads it.

    The shelf is printed alongside the kind because it is what the fact can
    *do* in an email - a `feature` entry filed under trust answers a doubt,
    the same entry filed under technical answers "will it fit" - and because
    a writer that can see six product facts and one commercial one beside
    each other stops reaching for the product facts by default.
    """
    if not entries:
        return "No evidence was found in the user's material. Make no factual claims."
    return "\n".join(
        f"- [{entry.id}] ({category_of(entry)}/{entry.kind}, {entry.strength}) {entry.claim}\n"
        f'      source says: "{_collapse(entry.verbatim, 240)}"'
        for entry in entries
    )


# --------------------------------------------------------------------- claims


class ClaimKind(StrEnum):
    MONEY = "money"
    PERCENT = "percent"
    MULTIPLIER = "multiplier"
    DURATION = "duration"
    QUANTITY = "quantity"
    QUOTE = "quote"
    URL = "url"


class Claim(BaseModel):
    """One assertion lifted out of a draft, in the form the checker compares."""

    kind: ClaimKind
    #: Exactly as it appears in the copy, for quoting back to the writer.
    text: str
    #: Whitespace/case/unit-normalized, so "10 mins" and "10 minutes" match.
    normalized: str


_MONEY_RE = re.compile(
    r"[$€£]\s?\d[\d,]*(?:\.\d+)?\s?[kmb]?\b"
    r"|\b\d[\d,]*(?:\.\d+)?\s?(?:usd|eur|gbp|dollars?|euros?|pounds?)\b",
    re.IGNORECASE,
)
#: No trailing \b after "%": a word boundary cannot exist between "%" and the
#: end of a string, so requiring one silently demotes every percentage to a
#: bare quantity.
_PERCENT_RE = re.compile(
    r"\b\d[\d,]*(?:\.\d+)?\s?%|\b\d[\d,]*(?:\.\d+)?\s?percent\b", re.IGNORECASE
)
_MULTIPLIER_RE = re.compile(r"\b\d[\d,]*(?:\.\d+)?\s?[x×]\b", re.IGNORECASE)
_DURATION_RE = re.compile(
    r"\b\d[\d,]*(?:\.\d+)?[\s-]?"
    r"(seconds?|secs?|minutes?|mins?|hours?|hrs?|days?|weeks?|months?|years?)\b",
    re.IGNORECASE,
)
#: Two digits or more only. A single bare digit is almost always rhetoric
#: ("one ask", "three reasons"); demanding evidence for those would make the
#: gate noise. Anything genuinely quantitative at single-digit scale ("$9",
#: "9%", "9 minutes") is already caught by the typed patterns above.
#:
#: The grouped-thousands alternative comes first and must: "1,500" read by the
#: plain pattern starts matching after the comma and yields "500", which is a
#: different number and would fail the gate on a figure the source states.
_QUANTITY_RE = re.compile(r"\b\d{1,3}(?:,\d{3})+(?:\.\d+)?\+?|\b\d{2,}(?:\.\d+)?\+?\b")
_URL_RE = re.compile(r"https?://[^\s<>()\[\]\"']+", re.IGNORECASE)
#: Double quotes only - a bare apostrophe is not a quote delimiter, it is what
#: every contraction and possessive in ordinary prose uses. Including it here
#: meant any two contractions in the same sentence ("it's ... you'd") bounded
#: a 25-400 char span that got flagged as a fabricated testimonial - the gate
#: was blocking drafts for sentences that never claimed to quote anyone.
_QUOTE_RE = re.compile(r"[“”\"]{1}([^“”\"\n]{25,400})[“”\"]{1}")

#: The shortest quoted span worth treating as an attributed quotation rather
#: than a turn of phrase in quote marks.
_MIN_QUOTE_WORDS = 6

_UNIT_CANON = {
    "sec": "seconds", "secs": "seconds", "second": "seconds",
    "min": "minutes", "mins": "minutes", "minute": "minutes",
    "hr": "hours", "hrs": "hours", "hour": "hours",
    "day": "days", "week": "weeks", "month": "months", "year": "years",
    "percent": "%",
    "dollar": "usd", "dollars": "usd", "euro": "eur", "euros": "eur",
    "pound": "gbp", "pounds": "gbp",
}

_WHITESPACE_RE = re.compile(r"\s+")
_TOKEN_SPLIT_RE = re.compile(r"^([\$€£]?)\s*([\d,.]+)\s*(.*)$")


def _collapse(text: str, limit: int | None = None) -> str:
    flat = _WHITESPACE_RE.sub(" ", text).strip()
    if limit is not None and len(flat) > limit:
        return flat[:limit].rstrip() + "…"
    return flat


def _normalize_measure(raw: str) -> str:
    """'1,500 mins' and '1500 minutes' must be the same string, or the gate
    fires on the writer's formatting rather than on its honesty."""
    flat = _collapse(raw).lower().replace("×", "x").rstrip("+")
    match = _TOKEN_SPLIT_RE.match(flat)
    if match is None:
        return flat
    symbol, number, unit = match.groups()
    number = number.replace(",", "").rstrip(".")
    if "." in number:
        number = number.rstrip("0").rstrip(".")
    unit = _UNIT_CANON.get(unit.strip(), unit.strip())
    return f"{symbol}{number}{(' ' + unit) if unit else ''}".strip()


def _normalize_url(raw: str) -> str:
    return _collapse(raw).lower().rstrip(".,);:!?").removeprefix("https://").removeprefix(
        "http://"
    ).removeprefix("www.").rstrip("/")


def extract_claims(text: str) -> list[Claim]:
    """Every assertion in a piece of copy that must be backed by something.

    Typed patterns run first and their spans are consumed, so "$29" is one
    money claim rather than also a bare quantity.
    """
    claims: list[Claim] = []
    consumed: list[tuple[int, int]] = []

    def take(pattern: re.Pattern[str], kind: ClaimKind, normalize=_normalize_measure) -> None:
        for match in pattern.finditer(text):
            span = match.span()
            if any(start < span[1] and span[0] < end for start, end in consumed):
                continue
            consumed.append(span)
            claims.append(
                Claim(kind=kind, text=match.group(0).strip(), normalized=normalize(match.group(0)))
            )

    take(_URL_RE, ClaimKind.URL, _normalize_url)
    take(_MONEY_RE, ClaimKind.MONEY)
    take(_PERCENT_RE, ClaimKind.PERCENT)
    take(_MULTIPLIER_RE, ClaimKind.MULTIPLIER)
    take(_DURATION_RE, ClaimKind.DURATION)
    take(_QUANTITY_RE, ClaimKind.QUANTITY)

    for match in _QUOTE_RE.finditer(text):
        quoted = match.group(1).strip()
        if len(quoted.split()) >= _MIN_QUOTE_WORDS:
            # Folded, not merely lower-cased. The page a quotation is checked
            # against was published through a CMS that made every apostrophe
            # curly and every range an en dash; the copy quoting it back is
            # plain ASCII about half the time. An exact substring test between
            # those two forms fails on a testimonial that is genuinely word
            # for word - and this gate blocks, so the draft is sent back to be
            # rewritten over a character. See corpus.fold.
            claims.append(
                Claim(kind=ClaimKind.QUOTE, text=quoted, normalized=fold(quoted))
            )
    return claims


class UnsupportedClaim(BaseModel):
    """A claim in the draft that nothing in the user's world backs up."""

    claim: Claim
    reason: str

    def as_issue(self) -> str:
        return f'"{self.claim.text}" - {self.reason}'


class EvidenceIndex:
    """What this campaign's copy is allowed to say, and the check that enforces it.

    The licensed set is built from two places: the ledger (facts the compiler
    committed to, with their verbatim support) and the raw source corpus (so a
    true detail the compiler did not think to promote does not get the writer
    blocked). Both are needed - the ledger alone is too strict to write
    against, the corpus alone would license any number that ever appeared on
    any page.
    """

    def __init__(self, ledger: EvidenceLedger, source_text: str = "") -> None:
        self._ledger = ledger
        licensing = "\n".join(entry.licensing_text for entry in ledger.entries)
        self._licensed: set[str] = {
            claim.normalized for claim in extract_claims(f"{licensing}\n{source_text}")
        }
        # Quoted passages are checked against the full text rather than against
        # extracted claims: a testimonial is quoted in the copy but sits
        # unquoted in the source page it came from. Folded on both sides so
        # the match survives the typography a CMS applied to the page.
        self._corpus = fold(f"{licensing}\n{source_text}")

    @property
    def licensed_values(self) -> set[str]:
        return set(self._licensed)

    def unsupported(self, text: str) -> list[UnsupportedClaim]:
        """Every claim in `text` with nothing behind it, phrased as the fix."""
        found: list[UnsupportedClaim] = []
        for claim in extract_claims(text):
            if claim.kind is ClaimKind.QUOTE:
                if claim.normalized not in self._corpus:
                    found.append(
                        UnsupportedClaim(
                            claim=claim,
                            reason=(
                                "this is presented as something a real person said, but it "
                                "appears nowhere in the material - cut it or replace it with a "
                                "testimonial from the evidence"
                            ),
                        )
                    )
                continue
            if claim.normalized in self._licensed:
                continue
            if claim.kind is ClaimKind.URL:
                found.append(
                    UnsupportedClaim(
                        claim=claim,
                        reason="this link does not exist in the user's material - never invent a URL",
                    )
                )
                continue
            found.append(
                UnsupportedClaim(
                    claim=claim,
                    reason=(
                        "no evidence entry or source document contains this figure - use a "
                        "number from the evidence or drop the claim"
                    ),
                )
            )
        return found
