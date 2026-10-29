"""What a company asserts on its own pages, and how two assertions are compared.

The comparison is the load-bearing part, and it is deterministic on purpose.
Asking a model "is our claim different from theirs?" gets an answer shaped by
whichever claim was written more confidently; asking it "what axis is this
claim on?" gets an answer it is reliably good at, and leaves the comparison to
code that always returns the same verdict for the same inputs.

The broad axis is a browsing aid, never evidence of equivalence. Price claims
can concern a subscription, a usage fee or a trial; two testimonials can be
about different customers and different outcomes. Comparisons therefore need
a shared proposition and compatible scope. When the captured words do not
establish those, the comparison remains a question to investigate.
"""

import re
from enum import StrEnum
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, Field

from app.knowledge.ledger import EvidenceContext
from app.knowledge.product_scope import is_product_subject


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
    context: EvidenceContext = Field(default_factory=EvidenceContext)

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
        attribution = (
            " (attributed comparison; not independently established)"
            if self.context.source_kind == "vendor_comparison"
            or self.context.claim_scope == "comparison" else ""
        )
        return f"[{self.axis}] {self.text}{mark}{attribution}{where}"


_FIGURE_RE = re.compile(
    r"\d|\bzero\b|\bno\s+(?:card|code|setup|contract|commitment)\b", re.IGNORECASE
)

_WORD_RE = re.compile(r"[^\W_][\w'+-]*", re.UNICODE)

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


ComparisonStatus = Literal["equivalent", "documented_difference", "potential_difference"]


# A few literal paraphrases, independent of product category. This is not a
# second taxonomy: unrecognised propositions are compared through their own
# words and otherwise stay unknown. In particular, "speed" alone never makes
# setup time comparable to delivery time or latency.
_PARAPHRASES: tuple[tuple[str, str], ...] = (
    (r"\breal[- ]?time\b", "realtime"),
    (r"\blive\s+(?=(?:visitors?|traffic)\b)", "realtime "),
    (r"\b(?:(?:single|one)[- ]page dashboard|(?:single|one) dashboard)\b", "singlepage dashboard"),
    ((r"\b(?:self[- ]host(?:ed|ing)?|(?:run|runs|running) it yourself|"
      r"(?:your|own) (?:own )?(?:cloud|vpc))\b"), "selfhosting"),
    ((r"\b(?:set[- ]?up|deploy(?:ment)?|get started|up and running|"
      r"get going|live in|way to start|start in no time)\b"), "initialsetup"),
    (r"\bfirst api call\b", "initialsetup apicall"),
    (r"\b(?:exports?|exporting|copy(?:ing)?['\"]? (?:the )?text for use elsewhere)\b", "export"),
    (r"\bsoc\s*2\b", "soc2"),
    (r"\bcustom\s+(?:\(sub\)|sub)?domains?\b|\b(?:your\s+)?own\s+domains?\b", "customdomain"),
    ((r"\bwhite[- ]label(?:ed|led|ing)?\b|\b(?:remove|removes|removing|hide|hides)\s+"
      r"(?:[\w'-]+\s+){0,3}branding\b"), "brandcontrol"),
)
_COMPARISON_FILLER = frozenset({
    "minute", "minutes", "second", "seconds", "hour", "hours", "day", "days",
    "month", "months", "year", "years", "per", "flat", "blazing", "quickest",
    "fastest", "time", "way", "ten", "five", "three", "two", "four", "six",
    "seven", "eight", "nine", "twenty", "hundred", "thousand", "no",
})


def proposition_words(text: str) -> set[str]:
    """The subject of a proposition, with quantities kept for the scope check."""
    normalized = text.lower()
    for pattern, replacement in _PARAPHRASES:
        normalized = re.sub(pattern, replacement, normalized)
    return {
        word.rstrip("s") if len(word) > 4 and word.endswith("s") else word
        for word in significant_words(normalized)
        if word not in _COMPARISON_FILLER and not word.isdigit()
    }


def comparable_claim(left: Claim, right: Claim) -> bool:
    """Whether captured wording establishes a common proposition to inspect.

    This deliberately misses some paraphrases. A missed match is a research
    question; a false match invents competitive parity or differentiation.
    """
    if left.axis is not right.axis:
        return False
    if left.axis is ClaimAxis.PRICE and not all(_price_proposition(c) for c in (left, right)):
        return False
    if left.axis is ClaimAxis.PRICE and _priced_addon(left) != _priced_addon(right):
        return False
    if left.axis is ClaimAxis.PROOF and (left.context.subject != right.context.subject
                                       or left.context.conditions != right.context.conditions):
        return False
    if left.text.strip() and _normalized(left.text) == _normalized(right.text):
        return True
    first, second = proposition_words(left.text), proposition_words(right.text)
    if not first or not second:
        return False
    shared = first & second
    if left.axis is ClaimAxis.SPEED and {"realtime", "dashboard"} <= shared:
        # Related live-display claims deserve inspection even when one adds
        # a refresh interval. Scope and measurements still govern equivalence.
        return True
    # A literal, unambiguous paraphrase may be the only content word.
    anchors = {"selfhosting", "initialsetup", "customdomain", "brandcontrol"}
    if shared & anchors or any(re.fullmatch(r"(?:soc|iso)\d+", word) for word in shared):
        return True
    if "export" in shared and shared - {"export"}:
        return True
    if left.axis is ClaimAxis.PRICE:
        # Different billing amounts still concern one subscription proposition;
        # currency, unit, period and conditions are checked separately below.
        left_scope, right_scope = _price_scope(left), _price_scope(right)
        if left_scope["amount"] and right_scope["amount"]:
            # A shared billing period is not a shared product: replay minutes,
            # feature flags and a site-analytics subscription can all be monthly.
            # Require a common proposition beyond generic commercial wording.
            commercial = {"pro", "plan", "tier", "price", "cost", "pricing", "month",
                          "year", "monthly", "annual", "subscription", "start", "per"}
            return bool(shared - commercial) or (
                bool(left_scope["plan"]) and bool(right_scope["plan"])
                and bool(left_scope["unit"]) and bool(right_scope["unit"])
            )
    return len(shared) >= 2 and len(shared) / len(first | second) >= SAME_CLAIM_OVERLAP


def monetary_outcome(claim: Claim) -> bool:
    """A customer's revenue is evidence of an outcome, never a software fee."""
    return claim.context.claim_scope == "customer_outcome" or bool(re.search(
        r"\b(?:recurring revenue|in (?:revenue|sales|profit)|turnover|valuation)\b"
        r"|\b(?:generated|earned|grew to|reached)\b.{0,65}\b(?:revenue|sales|profit)\b",
        f"{claim.text} {claim.verbatim}", re.IGNORECASE,
    ))


def _price_proposition(claim: Claim) -> bool:
    return not monetary_outcome(claim) and claim.context.claim_scope not in {
        "customer_outcome", "launch",
    }


def _priced_addon(claim: Claim) -> str:
    """Extra capacity is a separate purchase from the base subscription."""
    match = re.search(
        r"\b(?:extra|additional)\s+(users?|seats?|sites?|domains?|workspaces?)\b",
        f"{claim.text} {claim.verbatim}", re.IGNORECASE,
    )
    return match.group(1).lower().rstrip("s") if match else ""


def compare_claims(left: Claim, right: Claim) -> tuple[ComparisonStatus, str]:
    """Compare related propositions without turning specificity into superiority."""
    if not comparable_claim(left, right):
        return "potential_difference", "Captured wording does not establish an equivalent proposition."
    if any(claim.context.source_kind == "vendor_comparison"
           or claim.context.claim_scope == "comparison" for claim in (left, right)):
        return "potential_difference", "Vendor comparison remains attributed; independent verification is needed."
    for key in ("temporal_scope", "limitations", "claim_scope"):
        if getattr(left.context, key) != getattr(right.context, key):
            return "potential_difference", f"Captured {key.replace('_', ' ')} differs or is unknown."
    if _negative(left) != _negative(right):
        return "potential_difference", "Captured propositions have different polarity; do not treat them as equivalent."
    if left.axis is ClaimAxis.PRICE:
        first, second = _price_scope(left), _price_scope(right)
        for key in ("currency", "period", "unit", "plan", "conditions"):
            if first[key] != second[key]:
                return "potential_difference", f"Price {key} differs or is missing; verify comparable terms."
        if proposition_words(left.text) != proposition_words(right.text):
            return "potential_difference", "Related price wording has a different subject or included scope."
        if not all(first[key] for key in ("amount", "currency", "period", "unit", "plan")):
            return "potential_difference", "Price scope is incomplete; verify currency, billing, unit and plan."
        if _price_detail(left) != _price_detail(right):
            return "potential_difference", "Price quotations carry different or unparsed terms; inspect the full conditions."
        if first["amount"] != second["amount"]:
            return "documented_difference", "Captured prices differ on matching stated terms; no value ranking is implied."
        return "equivalent", "Same captured price and stated terms."
    quantities_left, quantities_right = _quantities(left), _quantities(right)
    if quantities_left != quantities_right:
        return "potential_difference", "Figures or measurement scope differ; verify the same task and conditions."
    if _conditions(left) != _conditions(right):
        return "potential_difference", "Captured conditions differ or are missing."
    if proposition_words(left.text) != proposition_words(right.text):
        return "potential_difference", "Related propositions differ in the task, object, format or captured scope."
    if left.axis is ClaimAxis.PROOF and _normalized(left.text) != _normalized(right.text):
        return "potential_difference", "Customer evidence is specific to its customer, setting and outcome."
    if left.is_specific != right.is_specific:
        return "potential_difference", "One proposition is more specific; this does not establish better performance."
    return "equivalent", "Equivalent captured proposition; no product superiority is implied."


def same_claim(left: Claim, right: Claim) -> bool:
    """Only equivalent propositions on compatible terms count as shared promises."""
    return comparable_claim(left, right) and compare_claims(left, right)[0] == "equivalent"


def is_own_assertion(
    claim: Claim, *, company_name: str = "", rival_names: tuple[str, ...] = (),
) -> bool:
    """Whether a captured statement can represent this company's own offer.

    A fact about a rival remains useful research, but never becomes one of
    our product promises. Legacy ledgers lack structured context: comparison
    source paths and explicit rival subjects remain usable conservative cues.
    An unresolved source is not upgraded into independently established truth.
    """
    if claim.context.source_kind == "vendor_comparison" or claim.context.claim_scope == "comparison":
        return False
    source_path = urlsplit(claim.source).path.casefold()
    if re.search(r"(?:^|/)(?:compare|comparisons?|alternatives?|versus|vs)(?:/|$|[-_])|"
                 r"/[^/]*[-_]vs[-_][^/]*", source_path):
        return False

    own_name = _normalized(company_name)
    for name in rival_names:
        normalized = _normalized(name)
        if not normalized or normalized == own_name:
            continue
        for subject in (claim.text, claim.context.subject):
            value = _normalized(subject)
            if value == normalized or value.startswith(normalized + " "):
                return False

    if not own_name:
        return True
    if (claim.axis is not ClaimAxis.PROOF and claim.context.subject
            and claim.context.claim_scope in {"capability", "unknown"}
            and not is_product_subject(claim.context.subject, company_name)):
        return False
    # Explicit commercial subjects are recognizable without knowing every
    # competitor name. Avoid treating a named plan or a common object as a
    # company merely because it begins a sentence with a capital letter.
    match = re.match(
        r"^([A-ZÀ-Ý][\wÀ-ÿ&.'-]*(?:\s+[\wÀ-ÿ&.'-]+){0,4}?)\s+"
        r"(?:charges?|costs?|requires?|offers?|provides?|supports?|includes?)\b",
        claim.text,
    )
    if match:
        subject = _normalized(match.group(1))
        generic = {"the", "this", "our", "your", "a", "an", "pro", "business", "team",
                   "free", "paid", "plan", "tier", "subscription", "feature", "api",
                   "integration", "file", "form", "export", "custom", "monthly", "annual"}
        subject_words = subject.split()
        generic_subject = (subject_words[0] in generic
                           or bool(set(subject_words).intersection({"plan", "tier", "subscription"})))
        if (f" {own_name} " not in f" {subject} " and not generic_subject
                and not subject.startswith("customer")):
            return False
    return True


def _normalized(text: str) -> str:
    return " ".join(re.findall(r"[\w]+", text.lower()))


def _quantities(claim: Claim) -> tuple[str, ...]:
    return tuple(re.findall(r"\b\d+(?:[.,]\d+)?\s*(?:%|ms\b|seconds?\b|minutes?\b|hours?\b|days?\b)?",
                            f"{claim.text} {claim.verbatim}".lower()))


def _negative(claim: Claim) -> bool:
    return bool(re.search(r"\b(?:not|no|never|without|cannot|can't|doesn't|don't)\b",
                          claim.text.lower()))


def _conditions(claim: Claim) -> tuple[str, ...]:
    text = f"{claim.text} {claim.verbatim}".lower()
    captured = set(re.findall(
        r"\b(?:(?:billed|charged|paid|invoiced|payable)\s+(?:annually|yearly|monthly|quarterly)|"
        r"(?:annual|yearly|monthly|quarterly)\s+(?:commitment|contract|payment)(?:\s+required)?|"
        r"factur[ée]s?\s+(?:annuellement|mensuellement|trimestriellement)|"
        r"(?:paiement|engagement)\s+(?:annuel|mensuel|trimestriel)|"
        r"excluding tax|including tax|plus tax|new customers only|introductory|"
        r"first year|first month|subject to[^.;\n]+|when[^.;\n]+|if[^.;\n]+)", text,
    ))
    if claim.context.conditions:
        captured.add(_normalized(claim.context.conditions))
    return tuple(sorted(captured))


_MONEY = re.compile(
    r"(?:[$€£]\s*|\b(?:usd|eur|gbp|cad|aud)\s+)\d+(?:[.,]\d+)?|"
    r"\d+(?:[.,]\d+)?\s*(?:usd|eur|gbp|cad|aud)\b", re.IGNORECASE,
)


def _price_detail(claim: Claim) -> str:
    """Unparsed quotation detail stays a comparison limit, never disappears.

    The small scope parser cannot recognise every contractual phrase or
    language. Mask only monetary amounts: any remaining difference in the
    actual quotations must be inspected before declaring equal price terms.
    """
    return _normalized(_MONEY.sub(" amount ", claim.verbatim or claim.text))


def _price_scope(claim: Claim) -> dict[str, str | tuple[str, ...]]:
    text = f"{claim.text} {claim.verbatim}".lower()
    currencies = set(re.findall(r"\b(?:usd|eur|gbp|cad|aud)\b|[$€£]", text))
    amounts = {first or second for first, second in re.findall(
        r"(?:[$€£]\s*|\b(?:usd|eur|gbp|cad|aud)\s+)(\d+(?:[.,]\d+)?)|"
        r"(\d+(?:[.,]\d+)?)\s*(?:usd|eur|gbp|cad|aud)\b", text,
    )}
    periods = set(re.findall(r"(?:per\s+|/\s*)(month|year|week|day|mo|yr)\b", text))
    periods = {{"mo": "month", "yr": "year"}.get(p, p) for p in periods}
    units = set(re.findall(r"(?:per\s+|/\s*)(seat|user|workspace|account|company|credit|email|request)\b", text))
    # Missing unit is unknown. Never silently assume a whole-account price.
    plans = set(re.findall(r"\b([\w-]+)\s+(?:plan|tier|subscription)\b", text)) - {
        "a", "the", "our", "your", "this", "annual", "monthly", "paid",
    }
    # More than one price in the quotation needs a targeted reading, not a
    # comparison against whichever amount happened to come first.
    def single(values: set[str]) -> str:
        return next(iter(values)) if len(values) == 1 else ""

    return {
        "currency": single(currencies),
        "amount": single(amounts),
        "period": single(periods),
        "unit": single(units),
        "plan": single(plans),
        "conditions": _conditions(claim),
    }


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
