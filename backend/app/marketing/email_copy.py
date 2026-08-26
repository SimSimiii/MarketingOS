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
_FIELD_NAMES = ("ROLE", "SUBJECT", "PREVIEW", "GREETING", "CTA", "SIGNOFF", "PS", "BODY")
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
_MAX_CTA_WORDS = 8
#: The writer is asked for 45 (see prompts/writer.md) and checked at 50. The
#: gap is deliberate slack: the prompt used to say "one to three lines", which
#: is not a word count at all, and three long lines clear 50 easily - so
#: drafts were rejected for breaking a rule they had never been told. Asking
#: for a number just under the check means ordinary variation costs nothing
#: and only a genuinely long paragraph pays for a repair turn.
_MAX_PARAGRAPH_WORDS = 50
_MAX_BULLET_WORDS = 16
_MIN_BODY_WORDS = 60
_MAX_BODY_WORDS = 220
_MIN_PARAGRAPHS = 3


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


def _is_bullets(block: str) -> bool:
    lines = [line.strip() for line in block.splitlines() if line.strip()]
    return bool(lines) and all(line.startswith(_BULLET_PREFIXES) for line in lines)


def _split_wide(block: str) -> list[str]:
    """One block, re-broken into pieces inside the width. Sentences are packed
    greedily so the first piece carries as much as it may - a two-word
    paragraph left over at the end reads as a mistake."""
    if _is_bullets(block) or len(block.split()) <= _MAX_PARAGRAPH_WORDS:
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
    if _is_bullets(block):
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
    if len(email.call_to_action.split()) > _MAX_CTA_WORDS:
        issues.append(
            f"the call to action is a sentence - it must be the {_MAX_CTA_WORDS} words or "
            "fewer that go on the link"
        )

    paragraphs = _paragraphs(email.body)
    words = len(email.body.split())
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
    """
    blocks = [
        f"Subject: {email.subject}",
        f"Preview text: {email.preview_text}",
        "",
        email.greeting,
        "",
        email.body.strip(),
        "",
        f"{email.call_to_action} →",
        "",
        email.sign_off,
    ]
    if email.postscript.strip():
        blocks.extend(["", _with_ps_prefix(email.postscript.strip())])
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
    issues: list[str] = []
    for index, paragraph in enumerate(paragraphs, start=1):
        lines = [line.strip() for line in paragraph.splitlines() if line.strip()]
        if lines and all(line.startswith(_BULLET_PREFIXES) for line in lines):
            long_bullets = [line for line in lines if len(line.split()) > _MAX_BULLET_WORDS]
            if long_bullets:
                issues.append(
                    f"a bullet in block {index} runs past {_MAX_BULLET_WORDS} words "
                    f'("{_excerpt(long_bullets[0])}") - bullets are for scanning'
                )
            continue
        word_count = len(paragraph.split())
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
