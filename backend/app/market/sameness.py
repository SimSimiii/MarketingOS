"""The check nothing in this system was making: is the copy *different*?

Three gates already read every draft. The structure gate asks whether it is
shaped like an email. The evidence gate asks whether every claim is licensed
by the material. The substantiation check asks whether the email spent the
facts it was built on. An email can pass all three - cleanly, first time - and
still be an email the reader has received eleven times this year, because
"true, well-formed and grounded" says nothing about "unlike anyone else's".

That is not hypothetical. The draft this module was written for passed every
existing check and opened:

    Subject: Your competitor isn't waiting on you

Every word of it was true and licensed. It is also the single most-sent cold
email opening in B2B software, and a cold reader scored it two clicks in a
hundred. No regular expression in the codebase could have caught it, and no
model was asked - so it shipped.

Two different things are checked here, and they block differently.

**Interchangeable openings** are a closed list of argument shapes, matched by
pattern. These block. The list is short and stays short, for exactly the
reason the spam list is short: a gate that flags ordinary copy is a gate
everybody learns to ignore. Every entry on it is a *frame*, not a phrase -
"name the competitor as the threat" is on the list, and the twenty ways to
word it all fail the same way, so the copy is sent back with the frame named
rather than the words.

**The swap test** is the interesting one, and it is advisory. Take a paragraph
and strip out the words every competitor in this market also uses. If nothing
distinctive is left, that paragraph could be pasted into any of their emails
unchanged - which is the operational definition of copy that says nothing.
Advisory because the corpus behind it is a handful of crawled competitors, not
the category, and a check whose corpus is thin must not be able to stop a run.
It reaches the writer's correction turn beside the cold reader's report, which
is where it is actually fixable.
"""

import re

from pydantic import BaseModel, Field

from app.market.claims import significant_words
from app.market.positioning import PositioningMap, Territory

#: Argument frames that arrive in every inbox, matched loosely enough to catch
#: the rewording and tightly enough not to catch ordinary sentences. Each entry
#: is (pattern, what the frame is, what to do instead) - the last of which is
#: the only part the writer can act on, so it is never "be more original".
#:
#: Every one of these is a frame a stranger has no reason to accept from a
#: stranger. That is the common thread, and it is why the list is not a style
#: preference: they are all arguments that require trust the sender has not
#: earned yet, in the one email where they have earned none at all.
_INTERCHANGEABLE: tuple[tuple[re.Pattern[str], str, str], ...] = (
    (
        re.compile(
            r"\b(?:your|the)\s+competitors?\b(?:[^.!?]{0,40}?)"
            r"\b(?:already|isn'?t|is not|aren'?t|are not|won'?t|will not|ahead|"
            r"waiting|moving|shipping|beating|leaving)\b",
            re.IGNORECASE,
        ),
        "naming the reader's competitor as the threat",
        (
            "a stranger does not know who their competitors are or what those "
            "competitors are doing, so this reads as a guess with a deadline attached. "
            "Say the thing that is true about the reader's own week instead"
        ),
    ),
    (
        re.compile(r"\bwhile\s+you(?:'re| are)?\s+(?:still\s+)?\w+ing\b", re.IGNORECASE),
        "the 'while you are still doing X' scold",
        (
            "it tells the reader they are behind, which is an accusation from someone "
            "they have never met. Describe the situation without ranking them in it"
        ),
    ),
    (
        re.compile(r"\bstill\s+(?:doing|managing|tracking|handling|running)\b[^.!?]{0,30}"
                   r"\b(?:manually|by hand|in spreadsheets?|in excel)\b", re.IGNORECASE),
        "the 'still doing it manually' opening",
        (
            "every product in every category opens this way. Name what the manual "
            "version actually costs, in their units"
        ),
    ),
    (
        re.compile(r"\bwhat if (?:i told you|you could|there was)\b", re.IGNORECASE),
        "the 'what if I told you' hook",
        "it delays the point by one sentence and signals a pitch. Lead with the point",
    ),
    (
        re.compile(r"\b(?:quick question|got a (?:quick )?(?:second|minute))\b", re.IGNORECASE),
        "the false 'quick question' opening",
        (
            "the email is not a question and the reader knows it by line two. Ask the "
            "real thing, or open on their situation"
        ),
    ),
    (
        re.compile(r"\bimagine\s+(?:a\s+world|if|being able|never having)\b", re.IGNORECASE),
        "the 'imagine' hypothetical",
        (
            "asking a busy reader to imagine something costs them effort before you "
            "have given them anything. Show the real thing instead"
        ),
    ),
    (
        re.compile(r"\b(?:most|many)\s+(?:companies|teams|founders|businesses)\b[^.!?]{0,40}"
                   r"\b(?:don'?t (?:realize|know)|are (?:unaware|missing)|make this mistake)\b",
                   re.IGNORECASE),
        "the 'most companies don't realise' frame",
        (
            "it claims private knowledge the reader cannot check and puts them in the "
            "ignorant majority. State the specific thing you know"
        ),
    ),
    (
        re.compile(r"\bis\s+(?:costing|losing)\s+you\b[^.!?]{0,30}"
                   r"\b(?:money|time|customers|revenue|sales)\b", re.IGNORECASE),
        "the 'this is costing you money' assertion",
        (
            "the number is invented and the reader knows it. Use a figure from the "
            "material, or drop the claim"
        ),
    ),
    (
        re.compile(r"\b(?:don'?t|do not) (?:get )?(?:left behind|miss out)\b", re.IGNORECASE),
        "fear of missing out as the reason to act",
        (
            "it is the reason every unwanted email gives. Give the reason this "
            "particular reader would act this particular week"
        ),
    ),
    (
        re.compile(r"\b(?:i'?ll|i will) (?:keep|make) this (?:short|brief|quick)\b",
                   re.IGNORECASE),
        "announcing that the email is short",
        "spending a line saying you will not spend lines. Delete it and be short",
    ),
)

#: How much of a paragraph has to be category vocabulary before it is called
#: interchangeable. High on purpose: at 0.8, a paragraph fails only when four
#: of its five distinctive words are words competitors also spend, which is a
#: paragraph that really could have come from any of them.
SWAP_TEST_THRESHOLD = 0.8

#: Paragraphs shorter than this are not tested. A four-word line ("Three
#: months, spent either way.") has too few distinctive words for a ratio to
#: mean anything, and rhythm depends on short lines existing.
_MIN_WORDS_FOR_SWAP_TEST = 6


class SamenessFinding(BaseModel):
    """One place the copy could have been sent by somebody else."""

    #: The words at fault, quoted from the draft - never a paraphrase. The
    #: writer's correction turn can only act on text it can find.
    quote: str
    #: What is wrong with it, named as a frame rather than as a phrase.
    frame: str
    #: What to do instead. Concrete, or this whole check is "be more original"
    #: with extra steps.
    instead: str
    where: str = "body"
    blocking: bool = True

    def as_issue(self) -> str:
        return (
            f"\"{self.quote}\" is {self.frame} - {self.instead}"
            if self.blocking
            else f"\"{self.quote}\" says nothing a competitor could not also say - {self.instead}"
        )


class SamenessReport(BaseModel):
    findings: list[SamenessFinding] = Field(default_factory=list)
    #: The share of the body that survived the swap test, 0 to 1. Reported
    #: even when nothing failed, because it is the number that moves when copy
    #: gets more specific and the one a user can watch across runs.
    distinctiveness: float = 1.0
    #: True when the map had no competitors in it, so only the closed list ran.
    #: A clean report means much less in that case and should not be read as
    #: "this copy is differentiated".
    blind: bool = True

    @property
    def blocking(self) -> list[SamenessFinding]:
        return [finding for finding in self.findings if finding.blocking]

    @property
    def advisory(self) -> list[SamenessFinding]:
        return [finding for finding in self.findings if not finding.blocking]

    @property
    def passed(self) -> bool:
        return not self.blocking

    def summary(self) -> str:
        if not self.findings:
            return (
                "nothing interchangeable found"
                if self.blind
                else f"{self.distinctiveness:.0%} of the copy is this company's own"
            )
        blocking = len(self.blocking)
        return (
            f"{blocking} interchangeable opening(s)"
            if blocking
            else f"only {self.distinctiveness:.0%} of the copy is this company's own"
        )


def check(
    *,
    subject: str,
    preview: str,
    body: str,
    positioning: PositioningMap | None = None,
) -> SamenessReport:
    """Read a draft for everything about it that is not this company's own.

    The parts are separated because they fail differently: a cliché frame in
    the subject line is the same defect as one in the body and costs far more,
    since it is the only line most recipients read.
    """
    findings: list[SamenessFinding] = []

    for text, where in ((subject, "subject"), (preview, "preview text"), (body, "body")):
        findings.extend(_interchangeable(text, where))

    crowd = set(positioning.crowd_words) if positioning else set()
    ours = _our_words(positioning)
    distinctiveness = 1.0
    if crowd:
        distinctiveness, swapped = _swap_test(body, crowd, ours)
        findings.extend(swapped)

    return SamenessReport(
        findings=findings,
        distinctiveness=distinctiveness,
        blind=not crowd,
    )


def _interchangeable(text: str, where: str) -> list[SamenessFinding]:
    findings: list[SamenessFinding] = []
    for pattern, frame, instead in _INTERCHANGEABLE:
        match = pattern.search(text)
        if match is None:
            continue
        findings.append(
            SamenessFinding(
                quote=_sentence_around(text, match.start(), match.end()),
                frame=frame,
                instead=instead,
                where=where,
                blocking=True,
            )
        )
    return findings


def _swap_test(
    body: str, crowd: set[str], ours: set[str]
) -> tuple[float, list[SamenessFinding]]:
    """How much of the body only this company could have written.

    A word counts against the copy when competitors spend it *and* it is not
    one of the words this company owns. That second half matters: a company
    whose open ground is model coverage will and should say "models", and a
    check that punished the word would push the copy off the one axis it wins
    on.
    """
    distinctive = 0
    total = 0
    findings: list[SamenessFinding] = []

    for paragraph in [block.strip() for block in body.split("\n\n") if block.strip()]:
        words = significant_words(paragraph)
        if not words:
            continue
        mine = {word for word in words if word not in crowd or word in ours}
        total += len(words)
        distinctive += len(mine)
        if len(words) < _MIN_WORDS_FOR_SWAP_TEST:
            continue
        shared = 1 - (len(mine) / len(words))
        if shared >= SWAP_TEST_THRESHOLD:
            findings.append(
                SamenessFinding(
                    quote=_first_sentence(paragraph),
                    frame="built entirely out of the category's own words",
                    instead=(
                        "every distinctive word here is one competitors also use. Put "
                        "something in it only this company could have written - a figure, a "
                        "name, a limit, the specific thing that happens"
                    ),
                    blocking=False,
                )
            )

    return (distinctive / total if total else 1.0), findings


def _our_words(positioning: PositioningMap | None) -> set[str]:
    """The vocabulary this company has earned - its open and contested ground.

    Table stakes are deliberately excluded: those are the axes where using the
    category's words really does make the copy interchangeable.
    """
    if positioning is None:
        return set()
    words: set[str] = set()
    for reading in positioning.readings:
        if reading.territory in (Territory.OPEN, Territory.CONTESTED):
            for claim in reading.ours:
                words |= significant_words(f"{claim.text} {claim.verbatim}")
    return words


_SENTENCE_END = re.compile(r"[.!?]")


def _sentence_around(text: str, start: int, end: int) -> str:
    """The whole sentence a match sits in, so the writer is shown the line it
    has to replace rather than the fragment that tripped the pattern."""
    left = max(
        (match.end() for match in _SENTENCE_END.finditer(text, 0, start)), default=0
    )
    right = _SENTENCE_END.search(text, end)
    return text[left : right.end() if right else len(text)].strip()


def _first_sentence(paragraph: str) -> str:
    match = _SENTENCE_END.search(paragraph)
    return paragraph[: match.end()].strip() if match else paragraph.strip()
