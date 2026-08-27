"""What one email is made of, how the writer writes it down, and what reaches
the user's clipboard.

The writer does NOT emit JSON. Copy is whitespace: a short opening line, one
idea per paragraph, a P.S. hanging on its own - and all of that has to survive
being a value inside a JSON string, alongside two other emails. It does not.
What comes back is a wall of prose, which is exactly the failure this module
exists to remove. So the writer writes an email the way an email is written,
inside a small labelled-field envelope parsed here, and the structural rules a
sendable email cannot break are checked deterministically rather than hoped
for.
"""

import logging
import re

from pydantic import BaseModel, Field

logger = logging.getLogger("marketingos.marketing")

#: Labels the writer puts in front of each field. BODY is last on purpose:
#: everything after it is the email, so a paragraph that happens to start
#: "Subject:" is never mistaken for a field.
_FIELD_NAMES = (
    "ROLE",
    "SUBJECT",
    "PREVIEW",
    "EYEBROW",
    "HEADLINE",
    "GREETING",
    "CTA",
    "SIGNOFF",
    "PS",
    "BODY",
)
_REQUIRED_FIELDS = ("SUBJECT", "PREVIEW", "GREETING", "CTA", "SIGNOFF", "BODY")

#: Tolerates the markdown a model decorates its labels with (`**SUBJECT:**`).
_FIELD_RE = re.compile(
    rf"^\s*[*#_\s]{{0,4}}({'|'.join(_FIELD_NAMES)})[*#_\s]{{0,4}}:\s*(.*)$",
    re.IGNORECASE,
)
_PARAGRAPH_SPLIT_RE = re.compile(r"\n\s*\n")
_BLANK_RUN_RE = re.compile(r"\n{3,}")
_BULLET_PREFIXES = ("-", "*", "•", "–", "—")
#: Where one sentence ends and the next begins, for the layout pass. A
#: closing quote or bracket may follow the stop, and often does at the end
#: of a testimonial.
_SENTENCE_SPLIT_RE = re.compile("(?<=[.!?])[\"'”’)\\]]*\\s+")

#: Deliverability and scannability, not taste. A subject over ~65 characters is
#: truncated in most inboxes; a paragraph over 50 words is the wall of text a
#: reader skips; an email under 60 words has not argued anything and one over
#: 220 has argued twice.
#:
#: The ceiling is 220 and not 320 because the writer is told to stop at 200
#: (see prompts/writer.md) and a rule nothing checks is a suggestion. The gap
#: between the two numbers was where every additive pass in the system landed:
#: the critic asks for unspent evidence, the rewrite works it in, and a 250-word
#: email that reads as a compressed product page passes every check there is.
#: The slack above 200 is deliberate - a draft is repaired inside the writer's
#: own turn, so the cost of the ceiling is one retry, not a whole rewrite
#: cycle, and it should only be paid by drafts that are actually long.
MAX_SUBJECT_CHARS = 65
MAX_PREVIEW_CHARS = 110
#: A headline is the first thing read in a broadcast email and it is set large,
#: so it has to survive being large: past this it wraps to three lines on a
#: phone and stops being a headline.
MAX_HEADLINE_CHARS = 62
#: The eyebrow is two or three words in small capitals. Anything longer is a
#: sentence pretending to be a label, and letterspaced capitals are the worst
#: possible setting for a sentence.
MAX_EYEBROW_CHARS = 22
_MAX_CTA_WORDS = 8
#: The writer is asked for 45 (see prompts/writer.md) and checked at 50. The
#: gap is deliberate slack: the prompt used to say "one to three lines", which
#: is not a word count at all, and three long lines clear 50 easily - so
#: drafts were rejected for breaking a rule they had never been told. Asking
#: for a number just under the check means ordinary variation costs nothing
#: and only a genuinely long paragraph pays for a repair turn.
_MAX_PARAGRAPH_WORDS = 50
_MAX_BULLET_WORDS = 16
#: A callout is the one thing an email is really about, set apart in a box of
#: its own. Past this it is a paragraph with a border round it, which is worse
#: than no box: the reader's eye is drawn to a block that then asks them to
#: read as much as the email around it.
_MAX_CALLOUT_WORDS = 35
_MIN_BODY_WORDS = 60
_MAX_BODY_WORDS = 220
_MIN_PARAGRAPHS = 3


#: The whole markup vocabulary a writer may use, and it is two things.
#:
#: `**bold**` marks the few words a skimmer must not miss - the figure, the
#: date, the limit. `> ` at the start of a line marks one block as the thing
#: this email is really about, which the renderer draws as a set-apart box.
#:
#: Two, and no more, on purpose. Every token added here is a token the writer
#: will reach for, and an email with six kinds of emphasis has none: the
#: reader's eye has nothing left to land on. Everything else that would need
#: markup - a heading, a table, a second link - is a sign the email is trying
#: to be a landing page.
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*", re.DOTALL)

#: How a writer marks the block that carries the offer. A space after the
#: caret is required, so a line that merely begins with a quotation mark in
#: some client's reply format is not silently turned into a callout.
CALLOUT_PREFIX = "> "


def strip_markup(text: str) -> str:
    """The same copy with the layout marks taken out.

    Called in two places and for one reason: **nothing that reasons about the
    words should ever see the marks.** `render_email` is the plain-text
    deliverable the user pastes, where `**` is noise a real recipient would
    read; and every gate in the system runs on that same rendering, which
    makes this the single point where markup is prevented from reaching them.

    That matters more than it looks, and both directions of failure are real.
    `evidence_gate` matches a quotation whole against the corpus, so three
    emphasised words inside a testimonial the writer was told to cite produce
    a string that matches nothing - and a true, correctly-cited quotation is
    blocked as something nobody said. `stock_phrase_gate` fails the other way:
    it is a substring test, so `**limited time** only` reads as two harmless
    fragments and a banned phrase ships. Stripping here fixes both at once,
    and means a new gate cannot reintroduce either by forgetting markup exists.
    """
    without_callouts = "\n".join(
        line.removeprefix(CALLOUT_PREFIX)
        for line in text.splitlines()
    )
    return _BOLD_RE.sub(r"\1", without_callouts)


def has_markup(text: str) -> bool:
    """Whether the writer marked anything at all. Reported on the receipt, not
    enforced: an email with nothing worth setting apart is a normal email."""
    return bool(_BOLD_RE.search(text)) or any(
        line.startswith(CALLOUT_PREFIX) for line in text.splitlines()
    )


class EmailCopyError(ValueError):
    """The draft did not follow the field protocol, or broke a rule an email
    cannot be sent with. The message is written to be handed straight back to
    the writer as the correction to make."""


class Email(BaseModel):
    """One complete, sendable email.

    Every field is something the user would otherwise have to write
    themselves: without a greeting and a sign-off, what they copy is a
    fragment, not an email.
    """

    position: int
    role: str = ""
    subject: str
    preview_text: str
    #: Two or three words in small capitals above the headline - "YOUR CART",
    #: "LAST CALL". Optional, and empty for anything that is one person
    #: writing to another: an eyebrow is a magazine device and it announces
    #: that this is a broadcast, which is the truth for a launch and a lie for
    #: a cold email.
    eyebrow: str = ""
    #: The line the reader sees first, set large. Optional for the same reason
    #: and decided the same way - see prompts/writer.md. An email without one
    #: opens on its greeting, which is what a letter does.
    headline: str = ""
    greeting: str
    body: str
    call_to_action: str
    sign_off: str
    postscript: str = ""


class EmailSequence(BaseModel):
    """As many emails as the user asked for, in send order."""

    emails: list[Email] = Field(default_factory=list)
    sequence_rationale: str = ""


def parse_email(text: str, position: int) -> Email:
    """Turn one labelled-field draft into a validated `Email`.

    Raises `EmailCopyError` listing every problem at once, so a repair turn
    fixes them in one pass instead of surfacing them one at a time.
    """
    fields, body = _split_fields(text)
    missing = [name for name in _REQUIRED_FIELDS if not fields.get(name)]
    if missing:
        raise EmailCopyError(
            f"these labelled fields are missing or empty: {', '.join(missing)}. "
            "Re-send the email with every label on its own line and BODY last."
        )

    laid_out = reflow(body)
    if laid_out != body:
        logger.info(
            "email %d: re-broke the body into blocks - no words changed, only where the "
            "blank lines fall",
            position,
        )
    email = Email(
        position=position,
        role=fields.get("ROLE", ""),
        subject=fields["SUBJECT"],
        preview_text=fields["PREVIEW"],
        eyebrow=fields.get("EYEBROW", ""),
        headline=fields.get("HEADLINE", ""),
        greeting=fields["GREETING"],
        body=laid_out,
        call_to_action=fields["CTA"],
        sign_off=fields["SIGNOFF"],
        postscript=fields.get("PS", ""),
    )
    issues = structural_issues(email)
    if issues:
        raise EmailCopyError("; ".join(issues))
    return email


def reflow(body: str) -> str:
    """Put the blank lines where the rules already say they belong.

    Two of the structural rules are about layout and nothing else: a block
    wider than `_MAX_PARAGRAPH_WORDS`, and a body in fewer than
    `_MIN_PARAGRAPHS` blocks. The repair the writer was sent back to make was
    literally "split it" - and a whole deep-tier call was bought to move a
    blank line, at which point the model rewrote the words too, and the draft
    that came back had to be read cold all over again.

    Splitting at a sentence boundary is that repair, done in code, for
    nothing, and it changes not one word. It is the same kind of
    normalisation `_split_fields` already does when it collapses a run of
    blank lines - the copy is what the writer wrote; where it breaks is
    typesetting.

    Deliberately conservative:

    - a block already inside the width is left exactly as it was, soft line
      breaks and all;
    - a bullet list is never touched - bullets have their own rule and
      re-breaking them would make a list of lists;
    - a single sentence over the width is left alone, because shortening it
      means changing words and that is the writer's job. The gate still fires
      and the repair still happens - it just happens for a reason a repair can
      actually fix.
    """
    blocks = _paragraphs(body)
    if not blocks:
        return body

    widened: list[str] = []
    for block in blocks:
        widened.extend(_split_wide(block))
    # Only after the width pass: a body that is one long block becomes three
    # by being too wide, and splitting further for the minimum would be
    # cutting a paragraph that no rule objects to.
    for _ in range(_MIN_PARAGRAPHS):
        if len(widened) >= _MIN_PARAGRAPHS:
            break
        longest = max(range(len(widened)), key=lambda index: len(widened[index].split()))
        halves = _halve(widened[longest])
        if len(halves) == 1:
            break
        widened[longest : longest + 1] = halves
    return "\n\n".join(widened)


def _sentences(block: str) -> list[str]:
    return [piece.strip() for piece in _SENTENCE_SPLIT_RE.split(block) if piece.strip()]


def _is_callout(block: str) -> bool:
    """Whether this block is the one the writer set apart."""
    lines = [line.strip() for line in block.splitlines() if line.strip()]
    return bool(lines) and all(line.startswith(CALLOUT_PREFIX.strip()) for line in lines)


def _keeps_its_shape(block: str) -> bool:
    """Whether the layout pass must leave this block alone.

    A bullet list and a callout are both *one* thing whose shape carries
    meaning, and the paragraph-splitting rule below would take them apart:
    splitting a callout at a sentence boundary drops the `> ` from every piece
    after the first, so the box closes round the opening sentence and the rest
    of the offer silently becomes ordinary prose. Nothing downstream can
    detect that, because by then it simply is ordinary prose.

    Over-long ones are not lost, they are reported: `_paragraph_issues` sends
    them back to the writer as a fix, which is the right place for a block
    that is too big to be one thing.
    """
    return _is_bullets(block) or _is_callout(block)


def _is_bullets(block: str) -> bool:
    """Whether every line here is a list item.

    `**` is excluded explicitly because `*` is one of the bullet prefixes, so
    a paragraph that opens in bold reads as a list to a naive prefix test -
    and would then be rendered as one, turning a sentence into a bullet
    nobody wrote.
    """
    lines = [line.strip() for line in block.splitlines() if line.strip()]
    return bool(lines) and all(
        line.startswith(_BULLET_PREFIXES) and not line.startswith("**") for line in lines
    )


def _split_wide(block: str) -> list[str]:
    """One block, re-broken into pieces inside the width. Sentences are packed
    greedily so the first piece carries as much as it may - a two-word
    paragraph left over at the end reads as a mistake."""
    if _keeps_its_shape(block) or len(block.split()) <= _MAX_PARAGRAPH_WORDS:
        return [block]
    sentences = _sentences(block)
    if len(sentences) < 2:
        return [block]

    pieces: list[str] = []
    current: list[str] = []
    words = 0
    for sentence in sentences:
        length = len(sentence.split())
        if current and words + length > _MAX_PARAGRAPH_WORDS:
            pieces.append(" ".join(current))
            current, words = [], 0
        current.append(sentence)
        words += length
    if current:
        pieces.append(" ".join(current))
    return pieces


def _halve(block: str) -> list[str]:
    """The same block in two, split as near the middle as a sentence allows."""
    if _keeps_its_shape(block):
        return [block]
    sentences = _sentences(block)
    if len(sentences) < 2:
        return [block]
    half = len(block.split()) / 2
    taken = 0
    for index, sentence in enumerate(sentences[:-1], start=1):
        taken += len(sentence.split())
        if taken >= half:
            return [" ".join(sentences[:index]), " ".join(sentences[index:])]
    return [" ".join(sentences[:-1]), sentences[-1]]


def structural_issues(email: Email) -> list[str]:
    """Every way this email is not sendable, phrased as the fix."""
    issues: list[str] = []

    if len(email.subject) > MAX_SUBJECT_CHARS:
        issues.append(
            f"the subject is {len(email.subject)} characters and inboxes cut it at "
            f"{MAX_SUBJECT_CHARS} - shorten it"
        )
    if normalized(email.preview_text) == normalized(email.subject):
        issues.append("the preview text repeats the subject instead of extending it")
    if len(email.preview_text) > MAX_PREVIEW_CHARS:
        issues.append(f"the preview text is longer than {MAX_PREVIEW_CHARS} characters")
    if len(email.headline) > MAX_HEADLINE_CHARS:
        issues.append(
            f"the headline is {len(email.headline)} characters and it is set large - past "
            f"{MAX_HEADLINE_CHARS} it wraps to three lines on a phone and stops being a "
            "headline. Cut it, or leave it out and let the email open on the greeting"
        )
    if len(email.eyebrow) > MAX_EYEBROW_CHARS:
        issues.append(
            f"the eyebrow is {len(email.eyebrow)} characters - it is set in small "
            f"capitals, where anything past {MAX_EYEBROW_CHARS} is a sentence pretending "
            "to be a label. Two or three words"
        )
    if email.eyebrow and not email.headline:
        # The eyebrow is a label *for* the headline. On its own it is a stray
        # line of capitals over a greeting, which reads as a mistake.
        issues.append(
            "there is an eyebrow but no headline - the eyebrow labels the headline, so "
            "either write one or drop the eyebrow"
        )
    if len(email.call_to_action.split()) > _MAX_CTA_WORDS:
        issues.append(
            f"the call to action is a sentence - it must be the {_MAX_CTA_WORDS} words or "
            "fewer that go on the link"
        )

    # The totals are measured on the words rather than on the marks: `> `
    # would otherwise count as a word in every callout line. The *blocks* are
    # taken from the unstripped body, because `_paragraph_issues` has to be
    # able to tell a callout from a paragraph - and stripping first is exactly
    # what would hide it.
    paragraphs = _paragraphs(email.body)
    words = len(strip_markup(email.body).split())
    if len(paragraphs) < _MIN_PARAGRAPHS:
        issues.append(
            f"the body is {len(paragraphs)} block(s) of text - break it into at least "
            f"{_MIN_PARAGRAPHS}, one idea each, with a blank line between them"
        )
    if words < _MIN_BODY_WORDS:
        issues.append(f"the body is {words} words - too short to have argued anything")
    if words > _MAX_BODY_WORDS:
        issues.append(
            f"the body is {words} words - over {_MAX_BODY_WORDS} means a second idea crept in, "
            "cut it"
        )
    issues.extend(_paragraph_issues(paragraphs))
    return issues


def render_email(email: Email) -> str:
    """The deliverable: what the user pastes into their email tool and sends.

    The subject and preview are labelled at the top because they go in their
    own fields; everything below them is the message itself, complete from the
    greeting to the P.S.

    Every field is stripped, not only the body. The P.S. is where a deadline
    gets repeated and is the second most likely place for a bolded date, and
    stripping only the body leaves `**Friday**` in the text a user pastes -
    which is exactly the bug this was written to prevent, one field over. The
    subject and the link text are stripped for the same reason and not because
    they should carry marks: a stray one there must not reach a recipient
    either, and no email has ever needed a literal `**` in its subject line.
    """
    blocks = [
        f"Subject: {strip_markup(email.subject)}",
        f"Preview text: {strip_markup(email.preview_text)}",
        "",
    ]
    # The headline ships, so it belongs in the text a user pastes and in the
    # text every gate reads. The eyebrow does not: it is three words of
    # typography, and in a plain-text email it is a line of shouting that the
    # spam gate would be right to flag.
    if email.headline.strip():
        blocks.extend([strip_markup(email.headline).strip(), ""])
    blocks += [
        strip_markup(email.greeting),
        "",
        strip_markup(email.body).strip(),
        "",
        f"{strip_markup(email.call_to_action)} →",
        "",
        strip_markup(email.sign_off),
    ]
    if email.postscript.strip():
        blocks.extend(["", _with_ps_prefix(strip_markup(email.postscript).strip())])
    return "\n".join(blocks)


def _with_ps_prefix(postscript: str) -> str:
    return postscript if postscript.upper().startswith("P.S") else f"P.S. {postscript}"


def _split_fields(text: str) -> tuple[dict[str, str], str]:
    """Read the labelled lines up to `BODY:`; everything after it is the body."""
    fields: dict[str, str] = {}
    body_lines: list[str] = []
    in_body = False

    for line in _strip_fences(text).splitlines():
        if in_body:
            body_lines.append(line)
            continue
        match = _FIELD_RE.match(line)
        if match is None:
            continue
        name, value = match.group(1).upper(), match.group(2).strip().strip("*_").strip()
        if name == "BODY":
            in_body = True
            if value:
                body_lines.append(value)
            continue
        fields[name] = value

    body = _BLANK_RUN_RE.sub("\n\n", "\n".join(body_lines)).strip()
    if body:
        fields["BODY"] = body
    return fields, body


def _strip_fences(text: str) -> str:
    return text.replace("```markdown", "").replace("```text", "").replace("```", "")


def _paragraphs(body: str) -> list[str]:
    return [block.strip() for block in _PARAGRAPH_SPLIT_RE.split(body) if block.strip()]


def _paragraph_issues(paragraphs: list[str]) -> list[str]:
    """Every block that is the wrong shape, phrased as the fix.

    Takes the blocks unstripped, so a callout can be recognised and held to
    its own limit. A callout is not split by the layout pass - see
    `_keeps_its_shape` - so this is the only thing standing between an
    over-long one and a box with a whole paragraph in it.
    """
    issues: list[str] = []
    for index, paragraph in enumerate(paragraphs, start=1):
        lines = [line.strip() for line in paragraph.splitlines() if line.strip()]
        if _is_callout(paragraph):
            words = len(strip_markup(paragraph).split())
            if words > _MAX_CALLOUT_WORDS:
                issues.append(
                    f"the block you set apart in block {index} is {words} words "
                    f'("{_excerpt(strip_markup(paragraph))}...") - a box round a whole '
                    f"paragraph draws the eye to something that then has to be read like "
                    f"everything else. Keep it under {_MAX_CALLOUT_WORDS} words or drop "
                    f"the marks and let it be prose"
                )
            continue
        if lines and all(line.startswith(_BULLET_PREFIXES) for line in lines):
            long_bullets = [line for line in lines if len(line.split()) > _MAX_BULLET_WORDS]
            if long_bullets:
                issues.append(
                    f"a bullet in block {index} runs past {_MAX_BULLET_WORDS} words "
                    f'("{_excerpt(long_bullets[0])}") - bullets are for scanning'
                )
            continue
        word_count = len(strip_markup(paragraph).split())
        if word_count > _MAX_PARAGRAPH_WORDS:
            issues.append(
                f"block {index} is {word_count} words in one paragraph "
                f'("{_excerpt(paragraph)}...") - split it, no paragraph over three lines'
            )
    return issues


def _excerpt(text: str, limit: int = 45) -> str:
    flat = " ".join(text.split())
    return flat if len(flat) <= limit else flat[:limit].rstrip()


def normalized(text: str) -> str:
    return " ".join(text.lower().split()).strip(" .!?")
