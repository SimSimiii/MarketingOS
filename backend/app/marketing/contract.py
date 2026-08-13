"""What the user actually asked for, parsed rather than interpreted.

"Create a five-email onboarding campaign" contains one fact that is not a
matter of judgment: five. The old system sent that sentence to a model and
hoped the number survived the round trip, then validated the result by asking
another model whether the deliverable matched. Both of those are stochastic
answers to an arithmetic question.

So the count is parsed here, in code, and becomes the contract every later
phase is checked against. What the emails should say is judgment and belongs
to the Strategist; how many there are is not.
"""

import re
from enum import StrEnum

from pydantic import BaseModel

#: Above this the request has stopped describing a campaign. Twelve emails is
#: already a long onboarding sequence; a request that parses to forty is a
#: misparse or a misunderstanding, and either way running it would burn the
#: user's budget on something they did not want.
MAX_EMAILS = 12
#: What "write me an email campaign" means when no number is given. Long
#: enough to have an arc, short enough that a user who wanted one email is not
#: handed a week of homework.
DEFAULT_SEQUENCE_LENGTH = 3

_NUMBER_WORDS: dict[str, int] = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "a": 1, "an": 1, "single": 1,
}

_COUNT_PATTERN = "|".join([r"\d{1,2}", *_NUMBER_WORDS])

#: Words that pivot the number onto something other than the emails. "3 ideas
#: for an email" is one email and three ideas; "2 versions of an email" is one
#: email. Any of these between the number and the noun means the number is
#: counting something else.
_PIVOTS = (
    "for", "about", "of", "to", "in", "on", "per", "that", "which", "from",
    "with", "before", "after", "via", "using", "into", "and", "or",
)

#: At most two describing words may sit between the number and what it counts:
#: "3 onboarding emails", "5 short sales emails", "a 3 part email series".
#: Bounded and pivot-free rather than unlimited, because the whole job of this
#: pattern is to tell "three emails" from "three reasons to send an email".
#:
#: A number word can never be filler, or the leftmost match wins with the
#: wrong number: "a five-email campaign" would match at "a", read the article
#: as one and swallow "five-" as a describing word.
_NOT_FILLER = "|".join((*_PIVOTS, *_NUMBER_WORDS))
_FILLER = rf"(?:(?!(?:{_NOT_FILLER})\b)[a-z]+(?:-[a-z]+)?[\s-]+){{0,2}}"

#: "5 emails", "five-email sequence", "3 onboarding emails", "a 3 part email
#: series".
_COUNT_BEFORE_RE = re.compile(
    rf"\b({_COUNT_PATTERN})[\s-]*{_FILLER}e-?mails?\b",
    re.IGNORECASE,
)
#: "sequence of 5 emails", "series of three e-mails"
_COUNT_AFTER_RE = re.compile(
    rf"\b(?:sequence|series|campaign|flow|set)\s+of\s+({_COUNT_PATTERN})\b",
    re.IGNORECASE,
)

_SEQUENCE_HINTS = ("sequence", "series", "campaign", "flow", "drip", "nurture", "onboarding")

#: "an email campaign" is a campaign, not one email. An article only counts as
#: a quantity when nothing after it says otherwise - a digit still does
#: ("a 5 email campaign" is five).
_ARTICLES = frozenset({"a", "an", "single"})
_SEQUENCE_TAIL_RE = re.compile(
    r"^\s*(?:marketing\s+)?(sequence|series|campaign|flow|drip|blast|program|programme)",
    re.IGNORECASE,
)


class DeliverableKind(StrEnum):
    """The shapes of work this system knows how to do.

    A closed set on purpose. The alternative - an open-ended router deciding
    what kind of thing to make - is what the old director was, and it spent a
    model call per step to rediscover a branch that fits in an if-statement.
    """

    EMAIL_SEQUENCE = "email_sequence"
    SINGLE_EMAIL = "single_email"


class DeliverableContract(BaseModel):
    """The promise the run is measured against, fixed before anything runs."""

    kind: DeliverableKind = DeliverableKind.EMAIL_SEQUENCE
    count: int = DEFAULT_SEQUENCE_LENGTH
    #: True when the user named a number. When false the Strategist may choose
    #: the length, and `count` is only the starting assumption.
    count_is_explicit: bool = False
    #: The words the count was read out of, for the run's own explanation.
    evidence: str = ""

    def render(self) -> str:
        if self.count_is_explicit:
            return (
                f"Exactly {self.count} email(s). The user asked for this in so many words "
                f'("{self.evidence}") - it is not negotiable.'
            )
        return (
            f"The user did not name a number. {self.count} emails is the working assumption; "
            "choose the length the campaign actually needs and say why."
        )


class ContractViolation(BaseModel):
    """A way the produced work does not match what was promised."""

    detail: str


def parse_contract(request: str) -> DeliverableContract:
    """Read the deliverable out of the user's own sentence."""
    match = _COUNT_BEFORE_RE.search(request) or _COUNT_AFTER_RE.search(request)
    if match is not None and not _is_article_before_a_sequence(request, match):
        count = _to_int(match.group(1))
        if count is not None and 1 <= count <= MAX_EMAILS:
            return DeliverableContract(
                kind=DeliverableKind.SINGLE_EMAIL if count == 1 else DeliverableKind.EMAIL_SEQUENCE,
                count=count,
                count_is_explicit=True,
                evidence=match.group(0).strip(),
            )

    lowered = request.lower()
    if any(hint in lowered for hint in _SEQUENCE_HINTS):
        return DeliverableContract(count=DEFAULT_SEQUENCE_LENGTH)
    if re.search(r"\be-?mails\b", lowered):
        return DeliverableContract(count=DEFAULT_SEQUENCE_LENGTH)
    if re.search(r"\be-?mail\b", lowered):
        return DeliverableContract(kind=DeliverableKind.SINGLE_EMAIL, count=1)
    return DeliverableContract(count=DEFAULT_SEQUENCE_LENGTH)


def check_contract(contract: DeliverableContract, delivered: int) -> list[ContractViolation]:
    """Did the run produce what it promised? Asked of the finished work, in
    code, because "did you write five emails" has a correct answer."""
    if delivered == contract.count:
        return []
    if not contract.count_is_explicit and delivered >= 1:
        return []
    return [
        ContractViolation(
            detail=(
                f"the user asked for {contract.count} email(s) and the run produced "
                f"{delivered}"
            )
        )
    ]


def _is_article_before_a_sequence(request: str, match: re.Match[str]) -> bool:
    return (
        match.group(1).strip().lower() in _ARTICLES
        and _SEQUENCE_TAIL_RE.match(request[match.end() :]) is not None
    )


def _to_int(token: str) -> int | None:
    token = token.strip().lower()
    if token.isdigit():
        return int(token)
    return _NUMBER_WORDS.get(token)
