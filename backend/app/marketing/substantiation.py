"""Whether the proof this email was built on actually reached the page.

The evidence gate points one way: nothing in the copy may claim more than the
material supports. That is the honesty half, and it is airtight - a number the
source never stated is blocked before any model sees the draft.

Nothing pointed the other way. An email could pass every check, spend none of
the facts the Strategist assigned it, and ship - and the architecture is built
almost entirely around getting those facts onto the page. Quote verification,
the ledger, the per-email evidence assignment, the preflight posture: all of
it gathers proof, and the last instrument in the chain never looked to see
whether any of it survived the writing.

That gap was measured rather than assumed. On the judge bench, an email with
its entire proof paragraph deleted - every remaining claim now unbacked, no
gate firing, nothing invented - was preferred over the original by half the
votes. The instrument that decides which draft ships could not see the one
thing the system exists to put there. Every rewrite that quietly sanded off a
testimonial was free.

This module answers that question the way the rest of the system answers
questions with correct answers: in code, for nothing, on every draft. It does
not ask whether the copy is persuasive. It asks whether the figure, the name
or the quotation that licenses the argument is on the page, which is a
matter of string matching.

Three counts, and they are deliberately different questions:

- **carried** - which of the facts this email was *assigned* are visible in it.
  The brief said what the email is built on; this says whether it was built on
  it.
- **attributions** - how many third-party entries (a customer, a quotation, a
  certification) the copy names or quotes. A cold reader discounts a company's
  claims about itself to roughly nothing, so this is the only kind of support
  that survives first contact.
- **specifics** - how many distinct checkable values from anywhere in the
  material the copy carries. Not proof, but the difference between an email
  written by someone who knows the product and one written about it.

Only the first two are ever allowed to veto anything. `specifics` moves for
honest reasons all the time - a rewrite that cuts one redundant figure is
usually a better email - and a rule that punished that would be a rule against
editing.
"""

import re
from dataclasses import dataclass

from app.knowledge.ledger import (
    ClaimKind,
    Evidence,
    EvidenceKind,
    extract_claims,
)
from app.marketing.email_copy import Email, render_email

#: Entries somebody other than the company stands behind. The same list the
#: preflight uses to decide what a campaign may argue from - see
#: app.marketing.preflight.PROOF_KINDS - because "what counts as proof" must
#: not be two different answers in two places.
ATTRIBUTABLE_KINDS = (
    EvidenceKind.TESTIMONIAL,
    EvidenceKind.CUSTOMER,
    EvidenceKind.AWARD,
    EvidenceKind.CERTIFICATION,
)

#: Words that start a sentence in ordinary prose and are capitalised for that
#: reason alone. Without this every "The", "We" and "Our" in a verbatim would
#: read as a name the copy could be checked against.
_SENTENCE_SPLIT = re.compile(r"[.!?]+\s+|\n+")
#: A name, a product, a company: capitalised, three characters or more, and
#: allowed the punctuation real names carry ("Acme's", "H&M", "St. Ives").
_CAPITALISED = re.compile(r"\b[A-Z][A-Za-z0-9&'’.-]{2,}\b")
#: An acronym is distinctive wherever it appears, including at the start of a
#: sentence - "SOC 2" is not capitalised because a full stop preceded it.
_ACRONYM = re.compile(r"\b[A-Z]{2,}\d?\b")

#: Capitalised words that are almost never the name of anything, so a copy
#: that happens to contain one has not thereby cited a customer.
_NOT_A_NAME = frozenset(
    {
        "the", "this", "that", "these", "those", "there", "their", "they", "them",
        "we", "our", "ours", "you", "your", "yours", "it", "its", "his", "her",
        "and", "but", "for", "with", "from", "when", "what", "who", "why", "how",
        "every", "each", "most", "more", "some", "any", "all", "one", "two",
        "after", "before", "since", "until", "while", "because", "about",
        "not", "now", "then", "here", "just", "only", "also", "still",
        "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
        "january", "february", "march", "april", "may", "june", "july",
        "august", "september", "october", "november", "december",
    }
)

_WHITESPACE = re.compile(r"\s+")

#: Numbers a marketer writes out in words. Good copy does this constantly -
#: "in about nine seconds" reads better than "in about 9 seconds" - and the
#: claim extractor is deliberately blind to it, because *that* extractor's job
#: is to catch invented figures and a bare "three" is rhetoric far more often
#: than a claim.
#:
#: Here the question is the opposite one: not "is this number licensed" but
#: "is the licensed number on the page". Nine seconds in the source and nine
#: seconds in the copy are the same fact whichever way each is spelled, and
#: without this the mechanism figure - the single most common thing a brief
#: assigns - is invisible, and every email that spends it is reported as
#: having spent nothing.
_NUMBER_WORDS = {
    "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
    "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10",
    "eleven": "11", "twelve": "12", "fifteen": "15", "twenty": "20",
    "thirty": "30", "forty": "40", "fifty": "50", "sixty": "60",
    "seventy": "70", "eighty": "80", "ninety": "90", "hundred": "100",
    "thousand": "1000",
}
_NUMBER_WORD_RE = re.compile(
    r"\b(" + "|".join(_NUMBER_WORDS) + r")\b", re.IGNORECASE
)


def _flat(text: str) -> str:
    return _WHITESPACE.sub(" ", text).strip().lower()


def _in_digits(text: str) -> str:
    return _NUMBER_WORD_RE.sub(lambda m: _NUMBER_WORDS[m.group(0).lower()], text)


def _values(text: str) -> set[str]:
    """Every checkable figure in a piece of text, normalised.

    Reuses the claim extractor the evidence gate runs on the other side of the
    same question, so "10 mins" here and "10 minutes" there are one value.
    Quotations are excluded - they are matched as spans, not as values.

    Number words are turned into digits first. The extractor's own rules still
    decide what counts, so a lone "three" is still not a claim - it becomes
    "3", which no pattern here matches without a unit beside it.
    """
    return {
        claim.normalized
        for claim in extract_claims(_in_digits(text))
        if claim.kind is not ClaimKind.QUOTE
    }


def _quotations(text: str) -> list[str]:
    return [
        claim.normalized for claim in extract_claims(text) if claim.kind is ClaimKind.QUOTE
    ]


def _bare(word: str) -> str:
    """One capitalised token reduced to the name inside it.

    A possessive is dropped whole - "Halcyon's" and "Halcyon" are one company -
    with `removesuffix` rather than `rstrip`, because `rstrip("'s")` strips
    every trailing character in that set and turns "Ross" into "Ro".
    """
    bare = word.lower()
    for possessive in ("'s", "’s"):
        bare = bare.removesuffix(possessive)
    return bare.rstrip("'’")


def names_in(text: str) -> set[str]:
    """The proper nouns and acronyms in a piece of text, lower-cased.

    Sentence-initial words are dropped, because they are capitalised by
    grammar rather than by being names. Acronyms are kept wherever they fall:
    "SOC 2" at the start of a sentence is still SOC 2.
    """
    found: set[str] = {match.group(0).lower() for match in _ACRONYM.finditer(text)}
    for sentence in _SENTENCE_SPLIT.split(text):
        words = sentence.strip().split()
        for word in words[1:]:
            match = _CAPITALISED.fullmatch(word.strip(",;:()[]\"'"))
            if match is not None:
                found.add(_bare(match.group(0)))
    return {name for name in found if name and name not in _NOT_A_NAME}


@dataclass(frozen=True)
class Substantiation:
    """What of the material behind this email is visible in the email."""

    #: Ids of the assigned entries whose support reached the page.
    carried: tuple[str, ...] = ()
    #: Ids the brief assigned that did not.
    unspent: tuple[Evidence, ...] = ()
    #: Third-party entries the copy names or quotes.
    attributions: int = 0
    #: Distinct checkable values from the material that appear in the copy.
    specifics: int = 0

    @property
    def assigned(self) -> int:
        return len(self.carried) + len(self.unspent)

    @property
    def spends_nothing(self) -> bool:
        """Assigned facts, none of them on the page. The failure the critic
        was asked about in prose and nothing ever checked."""
        return self.assigned > 0 and not self.carried

    def weaker_than(self, other: "Substantiation") -> bool:
        """Strictly less of what the campaign was built on than `other`.

        A Pareto regression on the two counts that may never quietly go
        backwards: worse on one of them and no better on the other. Both
        conditions matter - a rewrite that trades a second assigned fact for a
        named customer has not weakened the email, and a rule that said so
        would be a rule against editing.

        `specifics` is deliberately not here. It moves for honest reasons on
        almost every rewrite.
        """
        mine = (len(self.carried), self.attributions)
        theirs = (len(other.carried), other.attributions)
        return any(a < b for a, b in zip(mine, theirs, strict=True)) and not any(
            a > b for a, b in zip(mine, theirs, strict=True)
        )

    def describe(self) -> str:
        if not self.assigned:
            return f"{self.specifics} checkable specific(s), {self.attributions} attributed"
        return (
            f"{len(self.carried)}/{self.assigned} assigned fact(s) on the page, "
            f"{self.attributions} attributed, {self.specifics} checkable specific(s)"
        )


def _carries(entry: Evidence, values: set[str], names: set[str], flat: str) -> bool:
    """Is this entry's support visible in the copy?

    Three ways, and an entry only needs one:

    - a figure it licenses appears in the copy (a price, a duration, a count);
    - a name it introduces appears in the copy (the customer, the auditor, the
      standard) - which is how a testimonial or a certification is spent, since
      neither has a number in it;
    - the copy quotes a passage that is in the entry's own verbatim.

    Deliberately generous. The question is whether the writer built on the
    fact, not whether it reproduced it word for word, and a measure strict
    enough to demand the latter would report unspent evidence on every
    well-written email.
    """
    licensing = entry.licensing_text
    if _values(licensing) & values:
        return True
    if names_in(licensing) & names:
        return True
    return any(quote in flat for quote in _quotations(licensing))


def assess(email: Email, assigned: list[Evidence], ledger: list[Evidence]) -> Substantiation:
    """Read one draft against the facts behind it. Costs no model call.

    `assigned` is what the brief said this email is built on; `ledger` is
    everything true about the business, which is what `specifics` and
    `attributions` are counted against - a writer that reached past its
    assignment for a stronger fact has not failed, it has edited.
    """
    text = render_email(email)
    values = _values(text)
    names = names_in(text)
    flat = _flat(text)

    # Ids for what was carried and whole entries for what was not: the first
    # is a key the loop compares versions on, the second is what a correction
    # turn has to be able to quote back at the writer.
    carried: list[str] = []
    unspent: list[Evidence] = []
    for entry in assigned:
        if _carries(entry, values, names, flat):
            carried.append(entry.id)
        else:
            unspent.append(entry)

    licensed_values: set[str] = set()
    attributions = 0
    for entry in ledger:
        licensing = entry.licensing_text
        licensed_values |= _values(licensing)
        if entry.kind in ATTRIBUTABLE_KINDS and _carries(entry, values, names, flat):
            attributions += 1

    return Substantiation(
        carried=tuple(carried),
        unspent=tuple(unspent),
        attributions=attributions,
        specifics=len(licensed_values & values),
    )


def unspent_issues(substantiation: Substantiation) -> list[str]:
    """The unspent assignments, phrased as the fix, for the writer's own
    correction turn.

    Only when *nothing* was spent. An email that used two of its three facts
    made an editorial choice, and a gate that argued with it would be a gate
    that turns every email into a product page - which is the exact pressure
    `EmailBrief.must_not_say` exists to resist.
    """
    if not substantiation.spends_nothing:
        return []
    return [
        (
            f"this email was built on [{entry.id}] \"{entry.claim}\" and none of it reached "
            "the page - put the figure, the name or the quotation in the copy, or the reader "
            "is being asked to take your word for the whole email"
        )
        for entry in substantiation.unspent
    ]
