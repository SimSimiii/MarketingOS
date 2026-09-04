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

from app.knowledge.artifacts import BusinessProfile, OfferSheet
from app.knowledge.ledger import Evidence, EvidenceIndex
from app.market.positioning import PositioningMap
from app.market.sameness import check as sameness_check
from app.marketing.email_copy import Email, render_email, strip_markup, structural_issues
from app.marketing.substantiation import Substantiation, unspent_issues
from app.marketing.substantiation import assess as assess_substantiation


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


# Product-scope claims whose truth can be checked from the V2 capability
# profile without asking a judge. The phrases are intentionally narrow: this
# gate blocks "we support voice calls", not an audience-level line such as
# "your receptionist answers calls".
_CAPABILITY_TERMS: dict[str, tuple[str, ...]] = {
    "voice_telephony": ("voice", "telephony", "phone calls", "sip"),
    "full_saas_backend": ("full backend", "entire backend", "whole backend"),
    "hipaa_compliance": ("hipaa",),
    "deep_vertical_integrations": (
        "deep vertical integration",
        "domain-specific integration",
    ),
}
_PRODUCT_SUBJECT = re.compile(
    r"\b(?:orqagent|we|our (?:product|platform|agent|api)|"
    r"this (?:product|platform|agent)|the (?:product|platform|agent))\b",
    re.IGNORECASE,
)
_CAPABILITY_PREDICATE = re.compile(
    r"\b(?:support(?:s|ed)?|handle(?:s|d)?|include(?:s|d)?|provide(?:s|d)?|"
    r"built[ -]in|available|compliant|certified|replace(?:s|d|ment|ing)?)\b",
    re.IGNORECASE,
)


def capability_scope_gate(
    text: str, forbidden_capability_ids: tuple[str, ...] | list[str]
) -> GateReport:
    """Block a narrow, explicit product claim for a non-verified capability."""
    details: list[str] = []
    sentences = re.split(r"(?<=[.!?])\s+|\n+", strip_markup(text))
    for capability_id in dict.fromkeys(forbidden_capability_ids):
        terms = _CAPABILITY_TERMS.get(capability_id, ())
        for sentence in sentences:
            lowered = sentence.casefold()
            if not any(term in lowered for term in terms):
                continue
            if not (
                _PRODUCT_SUBJECT.search(sentence)
                and _CAPABILITY_PREDICATE.search(sentence)
            ):
                continue
            details.append(
                f"'{sentence.strip()}' claims non-verified product capability "
                f"{capability_id} - remove the claim or supply licensed product evidence"
            )
            break
    return _report("capability-scope", details, GateSeverity.BLOCKING)


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
#: Acronyms that are vocabulary rather than volume. "REST API" is how a
#: technical product describes itself and "ACT NOW" is shouting; a gate that
#: cannot tell them apart blocks the copy on the words it needs most - in a
#: measured run it failed two of three drafts of an email about an HTTP
#: endpoint, and each failure cost a full rewrite pass to fix nothing.
#:
#: Compared case-folded. Entries shorter than four characters never reach this
#: rule (the pattern needs four capitals in a row) and are kept out of it.
_SHOUTING_ALLOWED = frozenset(
    {
        # what a product built on someone else's API has to say out loud
        "HTTP", "HTTPS", "REST", "JSON", "YAML", "HTML", "GRPC", "CRUD", "WEBHOOK",
        "OAUTH", "SAML", "OIDC", "JWT", "CORS", "UUID", "CDN", "DNS", "TLS",
        # compliance and commerce, which a reader wants to see stated plainly
        "SOC2", "GDPR", "HIPAA", "CCPA", "ISO", "SLA", "SLAS", "VAT", "SAAS",
        # the ones that carry a number the reader is meant to check
        "MRR", "ARR", "ROI", "CPU", "GPU", "RAM",
    }
)


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
        word for word in _SHOUTING_RE.findall(text) if word.upper() not in _SHOUTING_ALLOWED
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


# -------------------------------------------------------------- the proof


def substantiation_gate(substantiation: Substantiation) -> GateReport:
    """Did the email use the facts it was built on?

    The evidence gate's mirror image. That one blocks a claim the material
    does not support; this one notices copy that supports nothing - an email
    assigned three facts and carrying none of them, which every check in the
    system passed happily because inventing nothing is not the same as saying
    something.

    Advisory, and it has to be. A campaign for a business with no proof is
    written from mechanism and specifics on purpose (see
    app.marketing.preflight), and blocking would fail exactly the emails that
    were right to be written that way. What it does instead is reach the
    writer's correction turn in the same breath as the reader's report, which
    is where an unspent fact is actually fixable.
    """
    return _report("substantiation", unspent_issues(substantiation), GateSeverity.ADVISORY)


# -------------------------------------------------------------- composition


def structure_gate(email: Email) -> GateReport:
    """Deliverability and scannability rules an email cannot be sent breaking -
    subject length, paragraph width, body length. See email_copy."""
    return _report("structure", structural_issues(email), GateSeverity.BLOCKING)


# ----------------------------------------------------------------- sameness


def sameness_gate(email: Email, positioning: PositioningMap | None = None) -> GateReport:
    """Could somebody else have sent this?

    The gate that was missing. Everything above asks whether the copy is
    well-formed, honest and grounded; a draft can be all three and still be
    the email this reader received from four other companies this quarter.
    The one that prompted this scored 4/10 with a clean report and the
    subject line "Your competitor isn't waiting on you".

    Two severities, from two different sources - see `app.market.sameness`.
    The closed list of interchangeable openings blocks, because it is a
    pattern match on a frame with a named replacement, which is exactly the
    kind of thing a gate should decide. The swap test against the competitor
    corpus is advisory, because that corpus is a handful of crawled sites
    rather than the category, and a check whose evidence is thin must reach
    the writer as an argument rather than as a verdict.
    """
    report = sameness_check(
        subject=email.subject,
        preview=email.preview_text,
        body=email.body,
        positioning=positioning,
    )
    return GateReport(
        issues=[
            GateIssue(
                gate="sameness",
                detail=(
                    f"the {finding.where} - {finding.as_issue()}"
                    if finding.where != "body"
                    else finding.as_issue()
                ),
                severity=(
                    GateSeverity.BLOCKING if finding.blocking else GateSeverity.ADVISORY
                ),
            )
            for finding in report.findings
        ]
    )


# ----------------------------------------------------------------- clarity


#: Words in a company name that identify nothing. "Acme Labs" and "Acme" are
#: the same company to a reader; "Labs" on its own in a sentence is not the
#: company being named. Without this the check passes on any email containing
#: the word "group".
_NAME_NOISE = frozenset(
    {
        "inc", "ltd", "llc", "plc", "gmbh", "co", "corp", "corporation",
        "company", "group", "labs", "lab", "studio", "studios", "technologies",
        "technology", "software", "systems", "solutions", "digital", "team",
        "the", "and", "app", "ai", "io", "hq",
    }
)

#: Words that appear in every category description and so cannot tell a reader
#: what kind of thing they are being offered.
_CATEGORY_NOISE = frozenset(
    {
        "platform", "tool", "tools", "solution", "solutions", "software",
        "service", "services", "product", "products", "system", "systems",
        "app", "application", "company", "business", "based", "cloud", "saas",
        "management", "modern", "with", "that", "your", "their", "and", "for",
        "the",
    }
)


def _identifying_words(name: str) -> list[str]:
    words = [word for word in re.findall(r"[a-z0-9]{2,}", name.lower())]
    distinctive = [word for word in words if word not in _NAME_NOISE]
    # A company genuinely called "The Software Group" has no distinctive word,
    # and refusing to check is better than checking against "group".
    return distinctive or ([] if len(words) > 1 else words)


def clarity_gate(email: Email, business: BusinessProfile) -> GateReport:
    """Would a stranger finish this email knowing what is being sold?

    The check that was missing, and the cheapest one in the file. Every other
    gate here asks whether the copy is well-formed, honest, grounded and not
    interchangeable - and a draft can pass all of them while never once saying
    what the thing is. That is not a rare failure: it is what the rest of the
    system's own advice produces when followed too well. The writer is told to
    open on the reader rather than the product, to argue one idea, to prefer
    specifics over adjectives and to stay under two hundred words, and the
    email that results describes a Tuesday with great precision and leaves the
    product an unnamed "it".

    Two findings, and only the first blocks.

    **The offering is never named.** Searched everywhere a reader looks for it
    and deliberately *not* in the sign-off: a name that appears only under
    "- the Notewright team" has answered who sent this, which is a different
    question from what this is. A reader who reaches the link without ever
    meeting the name has nothing to attach the click to, and no amount of
    rewriting the argument fixes it. Blocking, because it is a fact about the
    text rather than a matter of taste - and because the cold reader, who is
    the only other thing in the system that would notice, costs a model call
    and reports it as one line among nine.

    **The email never says what kind of thing it is.** Named, but named the
    way a stranger's surname is: the reader now has a proper noun and still
    could not say whether it is software, an agency or a newsletter. Advisory,
    because a company whose category is "developer tooling" can legitimately
    establish that through a mechanism rather than by using either word, and a
    gate that blocked on vocabulary would fail exactly the concrete drafts it
    is supposed to protect.
    """
    wanted = _identifying_words(business.company_name)
    if not wanted:
        return GateReport()

    # Everywhere the reader is actually looking, and nowhere else. The
    # greeting and the sign-off are the envelope: they say who this is from.
    visible = _normalized(
        " ".join(
            (
                email.subject,
                email.preview_text,
                email.eyebrow,
                email.headline,
                strip_markup(email.body),
                email.call_to_action,
                email.postscript,
            )
        )
    )
    named = any(re.search(rf"\b{re.escape(word)}\b", visible) for word in wanted)
    if not named:
        return _report(
            "clarity",
            [
                (
                    f"the email never names {business.company_name} anywhere the reader is "
                    "reading - not in the subject, not in the body, not on the link. It is "
                    "under the sign-off, which tells them who sent this and not what it is. "
                    "A stranger finishes this with nothing to attach the click to: name the "
                    "thing once, plainly, before the ask"
                )
            ],
            GateSeverity.BLOCKING,
        )

    category = [
        word
        for word in re.findall(r"[a-z]{3,}", business.category.lower())
        if word not in _CATEGORY_NOISE
    ]
    if category and not any(
        re.search(rf"\b{re.escape(word)}", visible) for word in category
    ):
        return _report(
            "clarity",
            [
                (
                    f"{business.company_name} is named, but nothing on the page says what kind "
                    f"of thing it is - the reader gets a proper noun and never learns this is "
                    f"{business.category}. If the mechanism you describe does not make that "
                    "obvious on one reading, say it in the sentence that introduces the name"
                )
            ],
            GateSeverity.ADVISORY,
        )
    return GateReport()


def run_all(
    email: Email,
    *,
    evidence: EvidenceIndex,
    offer: OfferSheet,
    business: BusinessProfile | None = None,
    previous: list[Email] | None = None,
    merge_fields: tuple[str, ...] | list[str] | None = None,
    extra_banned: tuple[str, ...] = (),
    assigned: list[Evidence] | None = None,
    ledger: list[Evidence] | None = None,
    positioning: PositioningMap | None = None,
    forbidden_capability_ids: tuple[str, ...] | list[str] = (),
) -> tuple[GateReport, Substantiation]:
    """Every deterministic check, in one report - plus what the copy is
    actually standing on.

    Order matters only for readability of the feedback: structure first
    (the draft is malformed), then honesty, then deliverability, then whether
    a stranger can tell what it is, then variety.

    The substantiation is returned beside the report rather than folded into
    it because it is not only a finding. Two of its three counts decide which
    version of an email is kept - see `app.marketing.craft` - and a caller
    that has already paid to compute them should not have to compute them
    twice.
    """
    text = render_email(email)
    substantiation = assess_substantiation(email, assigned or [], ledger or [])
    report = GateReport()
    for part in (
        structure_gate(email),
        placeholder_gate(text, merge_fields),
        stock_phrase_gate(text, extra_banned),
        evidence_gate(text, evidence),
        capability_scope_gate(text, forbidden_capability_ids),
        spam_gate(email),
        overlap_gate(email, previous or []),
        call_to_action_gate(email, offer),
        clarity_gate(email, business or BusinessProfile()),
        substantiation_gate(substantiation),
        sameness_gate(email, positioning),
    ):
        report = report.extend(part)
    return report, substantiation


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
