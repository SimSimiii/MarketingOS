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
from datetime import UTC, datetime
from enum import StrEnum
from urllib.parse import urlsplit

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


class EvidenceContext(BaseModel):
    """The boundary of a fact, not another source of facts.

    Empty fields mean unknown. Old ledgers have no context at all; reading
    one must never silently infer a customer outcome, current price or launch.
    The prose fields deliberately preserve source-specific terms rather than
    turning every offer into a large, partly invented pricing schema.
    """

    subject: str = ""
    source_kind: str = "unknown"
    claim_scope: str = "unknown"
    conditions: str = ""
    temporal_scope: str = ""
    limitations: str = ""
    verification: str = "unknown"

    def render(self) -> str:
        fields = [
            ("subject", self.subject), ("source nature", self.source_kind),
            ("scope", self.claim_scope), ("conditions", self.conditions),
            ("time", self.temporal_scope), ("limits", self.limitations),
            ("source check", self.verification),
        ]
        return "; ".join(f"{label}: {value}" for label, value in fields if value)


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
    context: EvidenceContext | None = None
    source_references: list[dict[str, str]] = Field(default_factory=list)

    @property
    def licensing_text(self) -> str:
        # The compiler's paraphrase is not a second source of facts.
        return self.verbatim


def category_of(entry: Evidence) -> FactCategory:
    """The shelf for one fact, stored if the compiler set one, derived if not."""
    if entry.category is not None:
        return entry.category
    return classify(f"{entry.claim} {entry.verbatim}", str(entry.kind))


def context_of(entry: Evidence) -> EvidenceContext:
    """Read explicit scope, or label conservative legacy clues as inference.

    This never mutates a stored artifact, authenticates a source, or treats an
    extractor's paraphrase as proof. Derived scope is a caution for use, not
    a newly validated factual claim.
    """
    context = entry.context.model_copy(deep=True) if entry.context else EvidenceContext()
    derived = False
    path = urlsplit(entry.source).path.lower()
    comparison = bool(re.search(r"(?:^|/)(?:compare|comparison|comparisons|versus|vs|[^/]*-alternative)(?:/|$)", path))
    customer_page = bool(re.search(r"(?:^|/)(?:customers?|case-stud(?:y|ies)|testimonials?)(?:/|$)", path))
    outcome_figure = any(claim.kind in {ClaimKind.PERCENT, ClaimKind.MULTIPLIER, ClaimKind.DURATION}
                         for claim in extract_claims(entry.verbatim))
    if context.claim_scope in {"", "unknown"}:
        if comparison:
            context.claim_scope = "comparison"
            derived = True
        elif outcome_figure and (customer_page or entry.kind in {
            EvidenceKind.CUSTOMER, EvidenceKind.TESTIMONIAL,
        }):
            context.claim_scope = "customer_outcome"
            derived = True
    if comparison and context.source_kind in {"", "unknown"}:
        context.source_kind = "published_comparison"
        derived = True
    if not context.subject and context.claim_scope == "customer_outcome":
        names = _named_anchors(entry.verbatim)
        if names:
            people = [name for name in names if " " in name]
            context.subject = " / ".join(people or names[:1])
            derived = True
    if derived:
        context.limitations = "; ".join(filter(None, (
            context.limitations,
            "Scope inferred from source clues; review required for attribution, use case and conditions",
        )))
        context.verification = "; ".join(filter(None, (
            context.verification if context.verification != "unknown" else "",
            "scope inferred from source clues; interpretation requires review",
        )))
    return context


def _named_anchors(text: str) -> list[str]:
    names = re.findall(r"\b[A-Z][\w'-]*(?:\s+[A-Z][\w'-]*){0,3}\b", text)
    stop = {"the", "our", "we", "learn", "instead", "start", "free", "pro", "business",
            "unlike", "this", "that", "it", "get", "you", "in", "for"}
    return list(dict.fromkeys(name for name in names if fold(name) not in stop))[:6]


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
    rules = (
        "Use each fact only for its named subject, conditions and time. Documentation can "
        "support a capability, not a customer result. A customer's result belongs to that "
        "customer; a plan price is not a separate feature price. A vendor comparison is "
        "that vendor's claim about rivals, not independent verification. Unknown context "
        "stays unknown; do not claim novelty or current terms without dated support.\n"
    )
    return rules + "\n".join(
        f"- [{entry.id}] ({category_of(entry)}/{entry.kind}, {entry.strength}) {entry.claim}\n"
        f'      source says: "{entry.verbatim}"\n'
        f"      source: {entry.source or 'not recorded'}; "
        + (f"additional source references: {entry.source_references}; " if entry.source_references else "")
        +
        f"{context_of(entry).render() if entry.context else 'context not recorded (legacy or unknown); inferred clues: ' + context_of(entry).render()}"
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
    r"\b\d[\d,]*(?:\.\d+)?[\s\u2010\u2011-]?"
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
    unit = unit.strip().lstrip("-‐‑").strip()
    unit = _UNIT_CANON.get(unit, unit)
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
        self._contexts = {entry.id: context_of(entry) for entry in ledger.entries}
        self._source_text = source_text
        licensing = "\n".join(entry.licensing_text for entry in ledger.entries)
        self._licensed: set[str] = {
            claim.normalized for claim in extract_claims(f"{licensing}\n{source_text}")
        }
        # Quoted passages are checked against the full text rather than against
        # extracted claims: a testimonial is quoted in the copy but sits
        # unquoted in the source page it came from. Folded on both sides so
        # the match survives the typography a CMS applied to the page.
        self._corpus = fold(f"{licensing}\n{source_text}")
        self.numeric_support = numeric_support(f"{licensing}\n{source_text}")
        self._support_by_value: dict[tuple[ClaimKind, str], list[NumericSupport]] = {}
        for support in self.numeric_support:
            self._support_by_value.setdefault((support.kind, support.value), []).append(support)
        self._price_support: dict[str, list[PriceSupport]] = {}
        for support in [
            *_price_supports(source_text),
            *(support for entry in ledger.entries
              for support in _price_supports(entry.verbatim, entry.context)),
        ]:
            self._price_support.setdefault(support.value, []).append(support)
        # A model may qualify a plan as "Acme Starter" while the actual price
        # heading says "Starter". Only that quoted heading can license the
        # short name; dropping arbitrary prefixes would merge distinct plans.
        candidates: dict[tuple[str, str], set[str]] = {}
        for entry in ledger.entries:
            if (entry.kind != EvidenceKind.PRICE or entry.context is None
                    or entry.context.claim_scope != "offer"
                    or entry.context.source_kind in {"third_party", "vendor_comparison", "customer_statement"}):
                continue
            headings = re.findall(r"(?:^|\n)\s*#{1,6}\s+([^\n$€£]+?)\s+(?=[$€£]\s*\d)", entry.verbatim)
            supports = _price_supports(entry.verbatim, entry.context)
            if len(headings) != 1 or len(supports) != 1:
                continue
            alias, support = fold(headings[0]), supports[0]
            if support.subject.endswith(" " + alias):
                candidates.setdefault((support.value, alias), set()).add(support.subject)
        self._price_aliases: dict[str, dict[str, str]] = {}
        for (value, alias), names in candidates.items():
            if len(names) == 1 and not any(item.subject == alias for item in self._price_support[value]):
                self._price_aliases.setdefault(value, {})[alias] = next(iter(names))

    @property
    def licensed_values(self) -> set[str]:
        return set(self._licensed)

    def unsupported(self, text: str) -> list[UnsupportedClaim]:
        """Every claim in `text` with nothing behind it, phrased as the fix."""
        found: list[UnsupportedClaim] = []
        requested_support = numeric_support(text)
        for claim in extract_claims(text):
            if claim.kind is ClaimKind.QUOTE:
                # English house styles place a sentence's comma or full stop
                # inside quotation marks, even when it is not in a UI title or
                # the quoted source. Ignore only that terminal punctuation;
                # words and punctuation inside the passage still have to match.
                quoted = claim.normalized.rstrip(".,;:!?")
                if quoted not in self._corpus:
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
                requested = [support for support in requested_support
                             if support.value == claim.normalized and support.kind == claim.kind]
                available = self._support_by_value.get((claim.kind, claim.normalized), [])
                price_issue = self._price_issue(claim, text) if claim.kind is ClaimKind.MONEY else ""
                if price_issue:
                    found.append(UnsupportedClaim(claim=claim, reason=price_issue))
                elif any(item.metric and available and not any(
                    item.metric == source.metric or not source.metric for source in available
                ) for item in requested):
                    found.append(UnsupportedClaim(claim=claim, reason=(
                        "this figure is supported for a different metric; preserve its meaning "
                        "and attribution from the source citation"
                    )))
                elif any(item.subject and available and not any(
                    not source.subject or item.subject == source.subject for source in available
                ) for item in requested):
                    found.append(UnsupportedClaim(claim=claim, reason=(
                        "this figure belongs to a different named subject in the source citation"
                    )))
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

    def _price_issue(self, claim: Claim, text: str) -> str:
        sources = self._price_support.get(claim.normalized, [])
        subjects = tuple({item.subject for item in sources if item.subject})
        requests = [item for item in _price_supports(
            text, known_subjects=subjects, subject_aliases=self._price_aliases.get(claim.normalized),
        )
                    if item.value == claim.normalized]
        for requested in requests:
            eligible = list(sources)
            for field, description in (("period", "billing period"), ("unit", "per-unit basis"),
                                       ("subject", "plan or item being priced"),
                                       ("role", "financial meaning (price versus savings)")):
                wanted = getattr(requested, field)
                scoped = [item for item in eligible if getattr(item, field)]
                if wanted and scoped:
                    compatible = [item for item in scoped if getattr(item, field) == wanted]
                    if not compatible:
                        return f"this amount is documented for a different {description}; preserve the source terms"
                    eligible = compatible
            # Only explicit restrictions present on every compatible source
            # constrain a price. No semantic guess about arbitrary terms blocks.
            if eligible:
                required = set.intersection(*(set(item.conditions) for item in eligible))
                missing = required - set(requested.conditions)
                if missing:
                    return "this price omits documented conditions: " + ", ".join(sorted(missing))
        return ""

    def context_issues(self, text: str) -> list[str]:
        """Bounded semantic cautions; callers keep these advisory.

        Exact numeric scope conflicts block above. Inferring a launch or a
        general customer promise from prose still needs editorial judgment.
        """
        issues: list[str] = []
        if _NOVELTY_CLAIM.search(fold(text)):
            dated_launch = any(
                _launch_in_scope(text, entry, self._contexts[entry.id])
                for entry in self._ledger.entries
            )
            if not dated_launch:
                issues.append(
                    "A launch or novelty is asserted without dated launch evidence. Confirm the "
                    "release and its timing, or describe the documented capability without 'new'."
                )
        for support in numeric_support(text):
            customer_results = [entry for entry in self._ledger.entries
                                if self._contexts[entry.id].claim_scope == "customer_outcome"
                                and any(claim.normalized == support.value
                                        for claim in extract_claims(entry.verbatim))]
            unsafe_results = [entry for entry in customer_results
                              if not _preserves_customer_scope(support.citation, entry,
                                                               self._contexts[entry.id])]
            if unsafe_results:
                subjects = ", ".join(dict.fromkeys(self._contexts[entry.id].subject or entry.id
                                                  for entry in unsafe_results))
                issues.append(
                    f"The figure {support.value} is an attributed customer result ({subjects}); "
                    "keep its named subject, use case and conditions instead of promising that "
                    "result to every buyer or transferring it to another workflow."
                )
            comparisons = [entry for entry in self._ledger.entries
                           if self._contexts[entry.id].claim_scope == "comparison"
                           and any(claim.normalized == support.value
                                   for claim in extract_claims(entry.verbatim))
                           and _comparison_subject_present(support.citation, entry)
                           and not self._independent_comparison_support(support, entry)]
            if comparisons and not _ATTRIBUTED_COMPARISON.search(fold(support.citation)):
                issues.append(
                    f"The figure {support.value} is supported by a published comparison "
                    f"({comparisons[0].source or comparisons[0].id}). Attribute that source or "
                    "verify the named rival's current offer directly; quotation presence does "
                    "not independently validate a competitor claim."
                )
            if support.kind is ClaimKind.MONEY:
                issues.extend(_plan_feature_issues(support, self._source_text))
        return list(dict.fromkeys(issues))

    def _independent_comparison_support(self, support: "NumericSupport", comparison: Evidence) -> bool:
        subjects = [name for name in _named_anchors(comparison.claim)
                    if fold(name) in fold(support.citation)]
        return any(
            self._contexts[entry.id].claim_scope != "comparison"
            and entry.source and entry.source != comparison.source
            and any(fold(name) in fold(entry.claim) for name in subjects)
            and any(claim.normalized == support.value for claim in extract_claims(entry.verbatim))
            for entry in self._ledger.entries
        )


class PriceSupport(BaseModel):
    value: str
    period: str = ""
    unit: str = ""
    subject: str = ""
    role: str = ""
    conditions: list[str] = Field(default_factory=list)


_NOVELTY_CLAIM = re.compile(
    r"\b(?:(?:just|recently)\s+(?:launched|released|introduced)|"
    r"new\s+(?:feature|product|version|integration|offer)|"
    r"nouve(?:au|lle)\s+(?:produit|fonctionnalite|version|offre)|"
    r"(?:venons de|vient de)\s+(?:lancer|sortir)|"
    r"(?:is|are)\s+now\s+available|now\s+(?:available|launching)|"
    r"today[,\s]+we[’']re\s+introducing|product\s+launch|"
    r"(?:desormais|maintenant)\s+disponible)\b"
)
_DATED_LAUNCH = re.compile(
    r"\b(?:launch(?:ed)?|releas(?:e|ed)|introduc(?:ed|ing)|lance|sortie)\b"
    r"[^.\n]{0,90}\b(?:19|20)\d{2}\b"
)
_GENERAL_RESULT = re.compile(
    r"\b(?:you\s+(?:will|can)\s+(?:save|cut|reduce|increase|grow)|"
    r"(?:all|every)\s+(?:customers?|teams?|businesses?)|"
    r"(?:customers|teams|businesses)\s+(?:save|cut|reduce|increase)|"
    r"vous\s+(?:allez|pouvez)\s+(?:gagner|reduire|economiser)|"
    r"tous les clients|chaque client|gets?\s+you|gives?\s+you|"
    r"guarantee\w*|assure\w*)\b"
)
_ATTRIBUTED_COMPARISON = re.compile(
    r"\b(?:according to|published comparison|comparison (?:by|from|page)|"
    r"says|reports|reported|selon|d'apres|comparaison publiee)\b"
)


def _launch_in_scope(text: str, entry: Evidence, context: EvidenceContext) -> bool:
    if context.claim_scope != "launch" or not context.temporal_scope.strip():
        return False
    years = re.findall(r"\b(?:19|20)\d{2}\b", context.temporal_scope)
    dates = re.findall(r"\b\d{4}-\d{2}-\d{2}\b", context.temporal_scope)
    subject = set(re.findall(r"[a-z0-9]{3,}", fold(context.subject))) - {
        "the", "new", "product", "feature", "launch",
    }
    return bool(subject and subject <= set(re.findall(r"[a-z0-9]{3,}", fold(text)))
                and years and all(year in entry.verbatim for year in years)
                and (any(value in text for value in dates)
                     or datetime.now(UTC).date().isoformat() in dates))


def _preserves_customer_scope(text: str, entry: Evidence, context: EvidenceContext) -> bool:
    proposed = fold(text).strip(' ."“”')
    source = fold(entry.verbatim)
    if proposed and proposed in source:
        return True
    if _GENERAL_RESULT.search(proposed):
        return False
    names = [part.strip() for part in context.subject.split(" / ") if part.strip()]
    if not names or not any(fold(name) in proposed for name in names):
        return False
    # An explicit condition remains required. This is only an advisory and
    # deliberately asks for review when a paraphrase cannot be matched.
    if context.conditions and fold(context.conditions) not in proposed:
        return False
    source_names = {fold(name) for name in _named_anchors(entry.verbatim)}
    if any(fold(name) not in source_names for name in _named_anchors(text)):
        return False
    source_words = set(re.findall(r"[a-z]{4,}", source))
    proposed_words = set(re.findall(r"[a-z]{4,}", proposed))
    return len(source_words & proposed_words) >= min(3, len(source_words))


def _comparison_subject_present(text: str, entry: Evidence) -> bool:
    # Names come from the claim only as a retrieval clue. The source stays a
    # comparison and the result stays advisory, never independently verified.
    names = _named_anchors(entry.claim)
    return bool(names and any(fold(name) in fold(text) for name in names))


def _plan_feature_issues(support: "NumericSupport", source_text: str) -> list[str]:
    """Notice an included feature priced as an item using raw offer sections.

    A priced heading containing several subfeatures is a plan clue, not a
    validated pricing ontology. Ambiguity reaches the reviewer as a caution.
    """
    requested = _PRICE_SUBJECT.search(support.citation)
    if requested is None:
        return []
    item = fold(requested.group(1))
    for section in re.finditer(r"(?m)^(#{1,3})\s+(.+)\n", source_text):
        level = len(section.group(1))
        remainder = source_text[section.end():]
        boundary = re.search(rf"(?m)^#{{1,{level}}}\s+", remainder)
        body = remainder[:boundary.start()] if boundary else remainder
        if not any(claim.normalized == support.value for claim in extract_claims(body[:900])):
            continue
        features = [*re.findall(rf"(?m)^#{{{level + 1},6}}\s+(.+)$", body),
                    *re.findall(r"(?m)^\*\*([^*\n]+)\*\*\s*$", body)]
        if len(features) < 2 or not any(item in fold(feature) for feature in features):
            continue
        plan = section.group(2).strip()
        if item in fold(plan):
            continue
        return [(f"The source lists this feature inside the priced '{plan}' offer. "
                 "State that it is included in the plan and preserve the plan's terms; "
                 "the subscription amount does not establish a separate feature price.")]
    return []


_PRICE_PERIOD = re.compile(
    r"(?:/\s*|\bper\s+|\bpar\s+)(months?|mois|mo|years?|ans?|yr|weeks?|semaines?)\b",
    re.IGNORECASE,
)
_PRICE_UNIT = re.compile(
    r"(?:/\s*|\bper\s+|\bpar\s+)(seats?|users?|utilisateurs?|workspaces?|accounts?|"
    r"credits?|emails?|requests?|requetes?)\b", re.IGNORECASE,
)
_PRICE_SUBJECT = re.compile(
    r"\b([\w-]+)(?:\s+(?:plan|tier|subscription|abonnement|offre))?\s+"
    r"(?:is|costs?|co[uû]te(?:nt)?|est)\s+(?:from\s+|a partir de\s+)?"
    r"(?:[$€£]|\d+\s*(?:usd|eur|gbp))", re.IGNORECASE,
)
_PRICE_GENERIC_SUBJECTS = frozenset({
    "it", "this", "that", "price", "pricing", "plan", "subscription", "product", "app",
    "cela", "ceci", "prix", "abonnement", "produit",
})
_PRICE_CONDITIONS = {
    "annual payment": r"\b(?:billed|paid|payable|facture|paye)\s+(?:annually|yearly|annuellement)|\bannual (?:billing|payment|commitment|contract)\b",
    "tax excluded": r"\b(?:excluding|excludes|before|hors)\s+(?:vat|tax|taxes|tva)\b",
    "introductory price": r"\b(?:introductory|introductoire|first (?:month|year)|premier(?:e)? (?:mois|annee))\b",
    "new customers only": r"\b(?:new customers only|nouveaux clients uniquement)\b",
}


def _price_supports(
    text: str, context: EvidenceContext | None = None, *, known_subjects: tuple[str, ...] = (),
    subject_aliases: dict[str, str] | None = None,
) -> list[PriceSupport]:
    supports: list[PriceSupport] = []
    for sentence in re.split(r"(?<=[.!?])\s+|\n+", text):
        amounts = [claim for claim in extract_claims(sentence) if claim.kind is ClaimKind.MONEY]
        # Multiple prices in one sentence cannot be bound to separate terms
        # safely by a regex. Explicit per-entry context can still disambiguate.
        if len(amounts) != 1:
            continue
        terms = f"{sentence} {context.conditions if context else ''}"
        period_match = _PRICE_PERIOD.search(terms)
        period = period_match.group(1).lower() if period_match else ""
        period = {"mo": "month", "mois": "month", "months": "month", "yr": "year",
                  "years": "year", "an": "year", "ans": "year", "weeks": "week",
                  "semaine": "week", "semaines": "week"}.get(period, period)
        unit_match = _PRICE_UNIT.search(terms)
        unit = unit_match.group(1).lower().rstrip("s") if unit_match else ""
        unit = {"utilisateur": "user", "requete": "request"}.get(unit, unit)
        pricing_sentence = fold(sentence).replace("**", "").replace("__", "").replace("`", "")
        subject_match = _PRICE_SUBJECT.search(pricing_sentence)
        subject = fold(subject_match.group(1)) if subject_match else ""
        # A single-word fallback must not turn the explicitly named "Pro
        # Standard" into "Standard" and conflict with its own provenance.
        # Match the complete known name only where the sentence prices it;
        # mentioning it elsewhere cannot license another plan's amount.
        for name in sorted(known_subjects, key=lambda value: (-len(value), value)):
            if re.search(
                rf"(?<!\w){re.escape(name)}(?:\s+(?:plan|tier|subscription|abonnement|offre))?\s+"
                r"(?:is|costs?|co[uû]te(?:nt)?|est)\s+(?:from\s+|a partir de\s+)?"
                r"(?:[$€£]|\d+\s*(?:usd|eur|gbp))", pricing_sentence,
            ):
                subject = name
                break
        for alias, canonical in (subject_aliases or {}).items():
            # An exact clause boundary prevents "Basic Starter" inheriting the
            # alias Starter merely because the old fallback sees its last word.
            if re.search(
                rf"(?:^|[,;:]\s*|\s-\s+)\s*(?:(?:and|et)\s+)?"
                rf"(?:(?:the|our|le|notre)\s+)?{re.escape(alias)}"
                r"(?:\s+(?:plan|tier|subscription|abonnement|offre))?\s+"
                r"(?:is|costs?|co[uû]te(?:nt)?|est)\s+(?:from\s+|a partir de\s+)?"
                r"(?:[$€£]|\d+\s*(?:usd|eur|gbp))", pricing_sentence,
            ):
                subject = canonical
                break
        if context and context.claim_scope == "offer" and context.subject:
            subject = re.sub(r"\s+(?:plan|tier|subscription|abonnement|offre)$", "",
                             fold(context.subject))
        if subject in _PRICE_GENERIC_SUBJECTS:
            subject = ""
        conditions = [name for name, pattern in _PRICE_CONDITIONS.items()
                      if re.search(pattern, fold(terms))]
        role = "savings" if re.search(
            r"\b(?:save|saves|saving|savings|economis(?:ez|er|e|ent))\b", fold(sentence)
        ) else "price" if period or unit or subject or (
            context is not None and context.claim_scope == "offer"
        ) else ""
        supports.append(PriceSupport(value=amounts[0].normalized, period=period, unit=unit,
                                     subject=subject, role=role, conditions=conditions))
    return supports


class NumericSupport(BaseModel):
    value: str
    kind: ClaimKind
    metric: str
    citation: str
    subject: str = ""


# Deliberately conservative: only identifiable metric switches block. These
# categories do not claim to solve semantic entailment or arbitrary paraphrases.
_METRICS = {
    "discount": r"\b(discount|remise|reduction|off)\b",
    "revenue": r"\b(revenue|revenus|chiffre d'affaires|sales|ventes)\b",
    "conversion": r"\b(conversion|conversions)\b",
    "retention": r"\b(retention|retaining|churn|attrition)\b",
    "time": r"\b(minutes?|hours?|heures?|days?|jours?|time|temps)\b",
    "customers": r"\b(customers?|clients?|users?|utilisateurs?|teams?|equipes?)\b",
}


def numeric_support(text: str) -> list[NumericSupport]:
    result = []
    for sentence in re.split(r"(?<=[.!?])\s+|\n+", text):
        # Only explicit possessives around known metrics identify a subject.
        # Pronouns and unspecified attribution remain the existing critic's job.
        named = re.search(r"\b([A-Z][\w.-]*(?: [A-Z][\w.-]*){0,2})[’']s\s+"
                          r"(?:revenue|sales|conversion|retention|discount)", sentence)
        subject = fold(named.group(1)) if named else ""
        metrics = [name for name, pattern in _METRICS.items() if re.search(pattern, fold(sentence))]
        # Revenue per customer remains revenue, not a customer count.
        specific = [name for name in metrics if name != "customers"]
        metrics = specific or metrics
        metric = metrics[0] if len(metrics) == 1 else ""
        for claim in extract_claims(sentence):
            if claim.kind not in (ClaimKind.QUOTE, ClaimKind.URL):
                # A duration elsewhere in a sentence does not turn its price
                # into a time-saving claim. Typed measures retain their unit.
                claim_metric = "time" if claim.kind == ClaimKind.DURATION else metric
                if claim.kind == ClaimKind.MONEY and claim_metric == "time":
                    claim_metric = ""
                result.append(NumericSupport(value=claim.normalized, kind=claim.kind,
                                             metric=claim_metric, citation=sentence.strip(),
                                             subject=subject))
    return result
