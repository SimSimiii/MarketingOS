"""Everything about a draft that has a correct answer, checked in code.

These run on every draft before any judgment model sees it, and they cost
nothing. That combination is the point: a model asked to notice its own
placeholder is the reader least likely to notice it, and paying an expensive
reviewer to catch a `[Product Name]` is paying for the one job a regular
expression does perfectly.

Each gate returns issues phrased as the fix, because they are handed straight
back to the writer as its correction turn. "Block 2 is 71 words in one
paragraph - split it" is actionable; "readability could be improved" is not.

Blocking vs advisory matters. A blocking issue means the draft cannot be sent
as it stands and the run must not finish while it is unresolved. An advisory
issue is a judgment call the Conversion Critic should weigh - a gate that
blocks on taste would spend the user's budget arguing with a model about
whether a sentence is too long.
"""

import re
from enum import StrEnum

from pydantic import BaseModel, Field

from app.knowledge.artifacts import OfferSheet
from app.knowledge.ledger import EvidenceIndex
from app.marketing.email_copy import Email, render_email, structural_issues


class GateSeverity(StrEnum):
    BLOCKING = "blocking"
    ADVISORY = "advisory"


class GateIssue(BaseModel):
    gate: str
    detail: str
    severity: GateSeverity = GateSeverity.BLOCKING

    def render(self) -> str:
        return f"[{self.gate}] {self.detail}"


class GateReport(BaseModel):
    issues: list[GateIssue] = Field(default_factory=list)

    @property
    def blocking(self) -> list[GateIssue]:
        return [issue for issue in self.issues if issue.severity is GateSeverity.BLOCKING]

    @property
    def advisory(self) -> list[GateIssue]:
        return [issue for issue in self.issues if issue.severity is GateSeverity.ADVISORY]

    @property
    def passed(self) -> bool:
        return not self.blocking

    def render(self) -> str:
        if not self.issues:
            return "Every automatic check passed."
        return "\n".join(f"- {issue.render()}" for issue in self.issues)

    def render_blocking(self) -> str:
        return "\n".join(f"- {issue.render()}" for issue in self.blocking)

    def extend(self, other: "GateReport") -> "GateReport":
        return GateReport(issues=[*self.issues, *other.issues])


def _report(gate: str, details: list[str], severity: GateSeverity) -> GateReport:
    return GateReport(
        issues=[GateIssue(gate=gate, detail=detail, severity=severity) for detail in details]
    )


# ------------------------------------------------------------- placeholders

#: Anything the user cannot paste as-is. Merge tags are handled separately -
#: see `placeholder_gate` - because `{{first_name}}` is the one bracketed
#: token that is correct rather than unfinished.
_PLACEHOLDER_PATTERNS = [
    re.compile(r"\[[^\]\n]{1,60}\]"),
    re.compile(r"\binsert\s+[\w\s]{1,30}\bhere\b", re.IGNORECASE),
    re.compile(r"\btodo\b:?", re.IGNORECASE),
    re.compile(r"lorem ipsum", re.IGNORECASE),
    re.compile(r"\bxxx+\b", re.IGNORECASE),
    re.compile(r"\byour (?:company|product|brand) name\b", re.IGNORECASE),
]
_MERGE_TAG_RE = re.compile(r"\{\{\s*([\w.]+)\s*\}\}|\*\|\s*([\w.]+)\s*\|\*")

#: The merge fields most email tools populate. A campaign can extend this from
#: policy; the point is that personalization is configured, not banned. The
#: old system banned every bracketed token, which also banned real ESP
#: personalization and made "Hi {{first_name}}" impossible to produce.
DEFAULT_MERGE_FIELDS = ("first_name", "last_name", "company", "email")


def placeholder_gate(text: str, merge_fields: tuple[str, ...] | list[str] | None = None) -> GateReport:
    allowed = {field.lower() for field in (merge_fields or DEFAULT_MERGE_FIELDS)}
    details: list[str] = []

    for pattern in _PLACEHOLDER_PATTERNS:
        for match in pattern.finditer(text):
            details.append(
                f"'{match.group(0)}' is an unfilled placeholder - the user sends this as it is, "
                "so write the real words or cut the line"
            )
    for match in _MERGE_TAG_RE.finditer(text):
        name = (match.group(1) or match.group(2) or "").lower()
        if name not in allowed:
            details.append(
                f"'{match.group(0)}' is not a merge field this campaign can fill "
                f"(allowed: {', '.join(sorted(allowed)) or 'none'}) - write the real words instead"
            )
    return _report("placeholder", _dedupe(details), GateSeverity.BLOCKING)


# ------------------------------------------------------------ stock phrasing

_BANNED_PHRASES = (
    "in today's fast-paced world", "in today's digital age", "in this day and age",
    "unlock the power of", "unlock your", "game-changer", "game changer",
    "take your business to the next level", "to the next level", "look no further",
    "in conclusion", "at the end of the day", "revolutionize the way",
    "seamlessly integrate", "whether you're", "dive into", "delve into",
    "elevate your", "supercharge your", "in a world where", "we're excited to announce",
    "i hope this email finds you well", "hope this finds you well",
)


def stock_phrase_gate(text: str, extra: tuple[str, ...] = ()) -> GateReport:
    """Phrasing that is not wrong, only interchangeable.

    Caught mechanically so the writer can be told exactly which words to cut,
    rather than a model being asked to recognize its own tics - which is the
    thing it is worst at.
    """
    lowered = text.lower()
    hits = [phrase for phrase in (*_BANNED_PHRASES, *extra) if phrase in lowered]
    return _report(
        "stock-phrasing",
        [
            f"\"{phrase}\" could open any company's email - cut it and say the specific thing"
            for phrase in hits
        ],
        GateSeverity.BLOCKING,
    )


# ----------------------------------------------------------------- evidence


def evidence_gate(text: str, index: EvidenceIndex) -> GateReport:
    """The gate this architecture exists around.

    Every number, price, quotation and URL in the copy must be licensed by the
    evidence ledger or by the user's own material. "Never invent a statistic"
    was previously an instruction in a prompt; here it is a property of the
    output, verified on every draft for free.
    """
    return _report(
        "evidence",
        [unsupported.as_issue() for unsupported in index.unsupported(text)],
        GateSeverity.BLOCKING,
    )


# --------------------------------------------------------------------- spam

#: Vocabulary that moves an email toward the promotions tab or the spam folder.
#: Deliberately short and uncontroversial - a long list would flag ordinary
#: sales copy and train everyone to ignore this gate.
_SPAM_TERMS = (
    "act now", "buy now", "click here", "limited time only", "risk free", "100% free",
    "money back guarantee", "no obligation", "order now", "special promotion",
    "this is not spam", "winner", "congratulations you", "cash bonus", "earn extra cash",
    "double your", "guaranteed income", "urgent action required",
)
_SHOUTING_RE = re.compile(r"\b[A-Z]{4,}\b")
_EXCESS_PUNCT_RE = re.compile(r"[!?]{2,}|!\s*!")
_EXCLAMATION_LIMIT = 2
#: Words that are legitimately capitalized in normal copy.
_SHOUTING_ALLOWED = frozenset({"SOC2", "GDPR", "HIPAA", "SaaS", "API", "SDK", "CSV", "JSON", "PDF"})


def spam_gate(email: Email) -> GateReport:
    """Deliverability, not taste. An email nobody receives converts at zero
    however good it is, and none of these checks require judgment."""
    text = render_email(email)
    lowered = text.lower()
    details: list[str] = []

    for term in _SPAM_TERMS:
        if term in lowered:
            details.append(
                f"\"{term}\" is spam-filter vocabulary - say the same thing in your own words"
            )
    shouting = [
        word for word in _SHOUTING_RE.findall(text) if word not in _SHOUTING_ALLOWED
    ]
    if shouting:
        details.append(
            f"{', '.join(sorted(set(shouting))[:3])} is set in capitals - inbox filters read "
            "shouting as promotion, and so do people"
        )
    if _EXCESS_PUNCT_RE.search(text):
        details.append("repeated exclamation or question marks - one is enough, none is better")
    if text.count("!") > _EXCLAMATION_LIMIT:
        details.append(
            f"{text.count('!')} exclamation marks in one email - keep at most {_EXCLAMATION_LIMIT}"
        )
    if email.call_to_action.strip().lower().rstrip(" .") in {"click here", "here", "read more"}:
        details.append(
            f"'{email.call_to_action}' as link text tells the reader nothing and reads as bait - "
            "say what happens when they click"
        )
    return _report("spam", _dedupe(details), GateSeverity.BLOCKING)


# ------------------------------------------------------------------ overlap

_WORD_RE = re.compile(r"[a-z0-9']+")
#: Long enough that a match is a reused phrase rather than a common idiom.
_NGRAM = 6
#: How many words of the opening count as the "opening move". Two emails that
#: start the same way read as one email sent twice, however different their
#: bodies are.
_OPENING_WORDS = 7


def _words(text: str) -> list[str]:
    return _WORD_RE.findall(text.lower())


def _ngrams(words: list[str], size: int) -> set[tuple[str, ...]]:
    return {tuple(words[index : index + size]) for index in range(len(words) - size + 1)}


def overlap_gate(email: Email, previous: list[Email]) -> GateReport:
    """Cross-email repetition, verified rather than requested.

    Every writing prompt in the old system told the writer not to reuse an
    angle, a phrase or an opening move across a sequence, and nothing ever
    checked. This is that instruction turned into a test.
    """
    if not previous:
        return GateReport()

    details: list[str] = []
    body_words = _words(email.body)
    current = _ngrams(body_words, _NGRAM)
    opening = tuple(body_words[:_OPENING_WORDS])

    for earlier in previous:
        earlier_words = _words(earlier.body)
        shared = current & _ngrams(earlier_words, _NGRAM)
        if shared:
            phrase = " ".join(min(shared))
            details.append(
                f'"{phrase}" already appears in email {earlier.position} - the reader may have '
                "read that one, and a repeated phrase is what makes a sequence feel automated"
            )
        if opening and opening == tuple(earlier_words[:_OPENING_WORDS]):
            details.append(
                f"this opens exactly like email {earlier.position} - the opening move is the "
                "one thing that must never repeat across a sequence"
            )
        if _normalized(email.subject) == _normalized(earlier.subject):
            details.append(
                f"the subject repeats email {earlier.position}'s subject line word for word"
            )
    return _report("overlap", _dedupe(details), GateSeverity.BLOCKING)


# ---------------------------------------------------------------------- ask


def call_to_action_gate(email: Email, offer: OfferSheet) -> GateReport:
    """Is the email asking for something the reader can actually do?

    Advisory, not blocking: the writer legitimately rephrases an action to fit
    a sentence, and blocking on wording would make every draft fail. The
    Critic is the right judge of whether the rephrasing still points somewhere
    real.
    """
    if not offer.calls_to_action:
        return GateReport()
    asked = _normalized(email.call_to_action)
    if not asked:
        return GateReport()
    known = [_normalized(cta.label) for cta in offer.calls_to_action]
    if any(asked in label or label in asked for label in known):
        return GateReport()
    supported = ", ".join(cta.label for cta in offer.calls_to_action)
    return _report(
        "call-to-action",
        [
            (
                f"the email asks the reader to '{email.call_to_action}', which is not one of "
                f"the actions this product supports ({supported})"
            )
        ],
        GateSeverity.ADVISORY,
    )


# -------------------------------------------------------------- composition


def structure_gate(email: Email) -> GateReport:
    """Deliverability and scannability rules an email cannot be sent breaking -
    subject length, paragraph width, body length. See email_copy."""
    return _report("structure", structural_issues(email), GateSeverity.BLOCKING)


def run_all(
    email: Email,
    *,
    evidence: EvidenceIndex,
    offer: OfferSheet,
    previous: list[Email] | None = None,
    merge_fields: tuple[str, ...] | list[str] | None = None,
    extra_banned: tuple[str, ...] = (),
) -> GateReport:
    """Every deterministic check, in one report.

    Order matters only for readability of the feedback: structure first
    (the draft is malformed), then honesty, then deliverability, then variety.
    """
    text = render_email(email)
    report = GateReport()
    for part in (
        structure_gate(email),
        placeholder_gate(text, merge_fields),
        stock_phrase_gate(text, extra_banned),
        evidence_gate(text, evidence),
        spam_gate(email),
        overlap_gate(email, previous or []),
        call_to_action_gate(email, offer),
    ):
        report = report.extend(part)
    return report


def _dedupe(details: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for detail in details:
        if detail not in seen:
            seen.add(detail)
            unique.append(detail)
    return unique


def _normalized(text: str) -> str:
    return " ".join(text.lower().split()).strip(" .!?")
