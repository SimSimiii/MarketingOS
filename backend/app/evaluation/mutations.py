"""Degradations whose direction is not a matter of opinion.

The craft loop is decided end to end by judgment. A cold reader scores every
draft, a preference judge decides which version ships, an inbox scanner picks
the subject line - and nothing anywhere notes those judges. A run whose reader
cannot tell a specific email from a vague one still produces a receipt, a pull
score and a delivered campaign. It just optimises toward whatever the
instrument happens to reward, and no artifact in the system would look any
different.

Grading a judge normally needs labelled data, which needs users. It does not
have to. Take an email that is known to be good, break it in a way whose
direction nobody would dispute - replace the number with an adjective, bury the
ask, hedge the claim - and the pair is labelled by construction: the original
must win. A judge that cannot see it is measurably broken, and no recipient was
involved.

Two rules keep the labels honest, and both are the difference between this
measuring something and measuring nothing.

**A mutant has to be a plausible worse email, never a corrupted one.** Garbled
copy is caught by any judge trivially, so a bench built on it reports a
reliability the judges do not have. Every rule here is written to leave
grammatical, sendable prose - the email a mediocre copywriter would genuinely
have sent, not a broken one.

**A mutation that changes nothing is not a failure to detect.** Applied to an
email with no number in it, `specifics_to_adjectives` returns what it was
given, and a duel between two identical emails is a coin toss. The bench
identifies those pairs and drops them rather than scoring them as misses.

Which instrument is supposed to catch what is worth separating too. A few of
these are already caught by the free gates, and those cases bench the gates -
cheaply, and without a model. The interesting ones are judgment-only: no
regular expression can see that an email opened on the company instead of the
reader, so if the panel cannot either, then nothing in the system can.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass

from app.marketing.email_copy import Email

_BLOCK_SPLIT = re.compile(r"\n\s*\n")


def _blocks(body: str) -> list[str]:
    return [block.strip() for block in _BLOCK_SPLIT.split(body) if block.strip()]


@dataclass(frozen=True)
class Mutation:
    """One way to make a good email worse, and what it proves when it lands."""

    name: str
    #: The principle it violates, in the words the writer's own prompt uses.
    #: Rendered in the report, because a missed detection is only actionable if
    #: the person reading it can see what the judge was supposed to notice.
    breaks: str
    apply: Callable[[Email], Email]
    #: True when a deterministic gate already catches this. Those pairs bench
    #: the gates; the rest bench the judges, and only the judges can catch them.
    gate_visible: bool = False
    #: True when the verdict is supposed to stay put. These are the control
    #: arm: a bench that only ever asks "did you spot the worse one" cannot
    #: tell a discriminating judge from one that always picks the first email.
    invariant: bool = False


# ------------------------------------------------------- judgment-only damage

_NUMERAL = (
    r"(?:\d[\d,.]*|one|two|three|four|five|six|seven|eight|nine|ten|"
    r"eleven|twelve|fifteen|twenty|thirty|forty|fifty|hundred|thousand)"
)

#: Ordered, and the order is load-bearing: the duration rule has to consume
#: "nine seconds" before the count rule can turn it into "several seconds".
_VAGUE_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    # A length of time the reader could hold a stopwatch to.
    (
        re.compile(
            rf"\b(?:in\s+)?(?:about\s+|under\s+|less\s+than\s+|over\s+)?{_NUMERAL}"
            r"\s+(?:seconds?|minutes?|hours?|days?|weeks?|months?|years?)\b",
            re.IGNORECASE,
        ),
        "quickly",
    ),
    # A price, with whatever per-unit tail it carries.
    (re.compile(r"[$€£]\s?\d[\d,.]*(?:\s+per\s+\w+)*"), "a competitive rate"),
    (re.compile(r"\b\d[\d,.]*\s?%"), "most"),
    # A count of things. Deliberately restricted to plural nouns so the
    # replacement stays grammatical: "twenty entries" becomes "several
    # entries", and "one week" is left alone because "several week" is not
    # English and a mutant that reads as broken is detected as broken.
    (re.compile(rf"\b{_NUMERAL}\s+((?:free\s+)?\w+s)\b", re.IGNORECASE), r"several \1"),
)


def _vaguer(text: str) -> str:
    mutated = text
    for pattern, replacement in _VAGUE_RULES:
        mutated = pattern.sub(replacement, mutated)
    return _preserve_opening_case(text, mutated)


def _preserve_opening_case(original: str, mutated: str) -> str:
    """Re-capitalise a substitution that landed at the start of a line.

    "Nine seconds versus Friday afternoon" becomes "quickly versus Friday
    afternoon" without this, and a subject line starting in lower case is
    detected as a typo rather than as vagueness - the bench would score a
    catch it never earned. Only fires when the first character actually
    changed, so a control whose preview is deliberately lower case keeps it.
    """
    if not original or not mutated or original[0] == mutated[0]:
        return mutated
    if (original[0].isupper() or original[0].isdigit()) and mutated[0].islower():
        return f"{mutated[0].upper()}{mutated[1:]}"
    return mutated


def _specifics_to_adjectives(email: Email) -> Email:
    """Every checkable figure traded for a word that cannot be checked.

    The email still says the same thing and still reads as English. What it no
    longer does is give the reader anything to verify, which is the single
    instruction the writer's prompt repeats most often.
    """
    return email.model_copy(
        update={
            "subject": _vaguer(email.subject),
            "preview_text": _vaguer(email.preview_text),
            "body": _vaguer(email.body),
            "postscript": _vaguer(email.postscript),
        }
    )


_HEDGES = (
    "That is generally true, though every team is a little different.",
    "Results can vary quite a bit depending on how your setup is arranged.",
)
_SOFTENED_ASK = "If this sounds like it might be a fit, you could "


def _hedge_the_claims(email: Email) -> Email:
    """The same claims, made by somebody unwilling to stand behind them.

    Appended as whole sentences rather than woven into the existing ones: a
    hedge spliced mid-clause changes the grammar, and this pair is supposed to
    isolate confidence, not fluency.
    """
    blocks = _blocks(email.body)
    if len(blocks) < 2:
        return email
    hedged = list(blocks)
    for index, hedge in zip(range(1, len(hedged) - 1), _HEDGES, strict=False):
        hedged[index] = f"{hedged[index].rstrip()} {hedge}"
    # The last block is the ask - the line the whole email exists for - so it
    # is softened rather than padded.
    last = hedged[-1]
    if last:
        hedged[-1] = f"{_SOFTENED_ASK}{last[0].lower()}{last[1:]}"
    return email.model_copy(update={"body": "\n\n".join(hedged)})


def _bury_the_ask(email: Email) -> Email:
    """One ask, still present, no longer where a reader meets it.

    Moved off the end into the middle, where somebody scanning reaches it
    before they have been given a reason to act, and the link text replaced by
    words that describe nothing. Nothing is added and nothing is deleted, so
    the pair isolates the ask itself.
    """
    blocks = _blocks(email.body)
    if len(blocks) < 3:
        return email
    ask, rest = blocks[-1], blocks[:-1]
    return email.model_copy(
        update={
            "body": "\n\n".join([*rest[:-1], ask, rest[-1]]),
            # Not "click here" or "read more": those are on the spam gate's
            # list, and a mutation this file calls judgment-only must not be
            # quietly catchable by a regular expression.
            "call_to_action": "Learn more",
        }
    )


_COMPANY_OPENING = (
    "We have been building something we are quite proud of, and we wanted to "
    "put it in front of you. Our team has spent a long time getting it right."
)


def _open_on_the_company(email: Email) -> Email:
    """The first two sentences about the sender instead of the reader.

    The rest of the email is untouched. This is the floor of the bench: an
    opening that could be pasted into any competitor's email unchanged is the
    failure the writer's prompt names first, and a judge that cannot see it is
    not measuring copy at all.
    """
    blocks = _blocks(email.body)
    if not blocks:
        return email
    return email.model_copy(update={"body": "\n\n".join([_COMPANY_OPENING, *blocks[1:]])})


_PROOF_RE = re.compile(r"[\"“”]|\b(?:said|says|told|put it like this)\b", re.IGNORECASE)


def _strip_the_proof(email: Email) -> Email:
    """The paragraph carrying the evidence, removed and nothing put back.

    Every remaining claim is now unbacked. Nothing was invented, so no gate
    fires and the evidence ledger is untouched - which is exactly why this one
    belongs to the judges: it is the difference between an email that argues
    from a fact and one that asserts at a stranger.
    """
    blocks = _blocks(email.body)
    if len(blocks) < 3:
        return email
    proof = next((index for index, block in enumerate(blocks) if _PROOF_RE.search(block)), -1)
    if proof < 0:
        return email
    return email.model_copy(update={"body": "\n\n".join(blocks[:proof] + blocks[proof + 1 :])})


def _clickbait_subject(email: Email) -> Email:
    """The body left alone, the line that earns the open thrown away.

    The only pair here where the emails are identical below the subject, so it
    is the only one that isolates what the inbox scanner is for.
    """
    return email.model_copy(
        update={
            "subject": "Quick question for you",
            "preview_text": "I wanted to reach out about something",
        }
    )


# ------------------------------------------------------------- gate-visible

def _stock_phrase_open(email: Email) -> Email:
    """The opening every cold email has already used on this reader."""
    return email.model_copy(
        update={"body": f"I hope this email finds you well.\n\n{email.body}"}
    )


def _wall_of_text(email: Email) -> Email:
    """The same words with the paragraph breaks taken out."""
    return email.model_copy(update={"body": " ".join(_blocks(email.body))})


def _shout_and_exclaim(email: Email) -> Email:
    """Deliverability thrown away: shouting, spam vocabulary, punctuation."""
    return email.model_copy(
        update={"body": f"{email.body}\n\nHURRY - act now, this offer will not last!!"}
    )


# ---------------------------------------------------------------- invariance

def _identity(email: Email) -> Email:
    """The email against itself.

    The noise floor, and the only case here with a known correct answer that
    is not a preference: a judge that is reading rather than guessing should
    land near an even split, because the two emails are the same email. A
    lopsided result is position bias the alternating ballot failed to cancel,
    or an instrument answering from something other than the copy.
    """
    return email.model_copy()


def _neutral_greeting(email: Email) -> Email:
    """A change with no persuasive content at all.

    Distinct from `identity` because the two emails do differ - if a judge
    swings on this, it is swinging on difference itself rather than on quality,
    and every detection it scores elsewhere is worth less than it looks.
    """
    greeting = email.greeting.replace("Hi there", "Hello there")
    if greeting == email.greeting:
        greeting = email.greeting.replace("Hi", "Hello")
    return email.model_copy(update={"greeting": greeting})


MUTATIONS: tuple[Mutation, ...] = (
    Mutation(
        name="specifics_to_adjectives",
        breaks="Specifics, not adjectives - a figure the reader could check, traded for one they cannot",
        apply=_specifics_to_adjectives,
    ),
    Mutation(
        name="open_on_the_company",
        breaks="Open on them - the first sentence is about the sender, not the reader's situation",
        apply=_open_on_the_company,
    ),
    Mutation(
        name="strip_the_proof",
        breaks="The claim survives, the evidence behind it does not",
        apply=_strip_the_proof,
    ),
    Mutation(
        name="hedge_the_claims",
        breaks="The same claims, made by somebody unwilling to stand behind them",
        apply=_hedge_the_claims,
    ),
    Mutation(
        name="bury_the_ask",
        breaks="One ask, low friction, stated once - moved off the end and made vague",
        apply=_bury_the_ask,
    ),
    Mutation(
        name="clickbait_subject",
        breaks="A subject that promises curiosity instead of naming what is inside",
        apply=_clickbait_subject,
    ),
    Mutation(
        name="stock_phrase_open",
        breaks="An opening interchangeable with every other cold email",
        apply=_stock_phrase_open,
        gate_visible=True,
    ),
    Mutation(
        name="wall_of_text",
        breaks="One block of prose - a memo, not an email",
        apply=_wall_of_text,
        gate_visible=True,
    ),
    Mutation(
        name="shout_and_exclaim",
        breaks="Shouting, spam vocabulary and punctuation the filters read as promotion",
        apply=_shout_and_exclaim,
        gate_visible=True,
    ),
    Mutation(
        name="identity",
        breaks="Nothing - the email against itself, to measure what the judge does with a tie",
        apply=_identity,
        invariant=True,
    ),
    Mutation(
        name="neutral_greeting",
        breaks="Nothing persuasive - a different greeting, to see if the judge swings on difference alone",
        apply=_neutral_greeting,
        invariant=True,
    ),
)


def mutation_named(name: str) -> Mutation | None:
    return next((item for item in MUTATIONS if item.name == name), None)
