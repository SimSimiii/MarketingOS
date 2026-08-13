"""The structural contract of an email: what the writer must hand over, and
what the user ends up with on their clipboard."""

import pytest

from app.marketing.email_copy import (
    Email,
    EmailCopyError,
    parse_email,
    render_email,
    structural_issues,
)

WELL_FORMED = """ROLE: hook
SUBJECT: Your release notes, written for you
PREVIEW: from the commits you already pushed
GREETING: Hi there,
CTA: Start free
SIGNOFF: - The team
PS: The free tier stays free after the trial.
BODY:
You wrote the same release note three times last month.

Each one started as a changelog nobody read, and ended as a paragraph you rewrote twice before
you were willing to ship it to anyone.

This turns the commits you already pushed into that paragraph, in about nine seconds. You edit
it, or you send it exactly as it came out.

Most people ask first whether it sounds like them. It reads your last twenty notes before it
writes a word, so it does.
"""


def test_a_well_formed_draft_becomes_a_typed_email():
    email = parse_email(WELL_FORMED, position=2)

    assert email.position == 2
    assert email.subject == "Your release notes, written for you"
    assert email.greeting == "Hi there,"
    assert email.call_to_action == "Start free"
    assert email.sign_off == "- The team"
    assert email.body.startswith("You wrote the same release note")
    assert "PS:" not in email.body


def test_labels_survive_the_markdown_a_model_decorates_them_with():
    email = parse_email(WELL_FORMED.replace("SUBJECT:", "**SUBJECT:**"), position=1)
    assert email.subject == "Your release notes, written for you"


def test_everything_after_body_is_the_email():
    """A paragraph opening "Subject:" is copy, not a field - which is the whole
    reason BODY comes last."""
    draft = WELL_FORMED + "\nSubject: is a word people write in emails.\n"
    email = parse_email(draft, position=1)
    assert email.body.endswith("Subject: is a word people write in emails.")


def test_a_missing_label_names_itself_so_the_writer_can_fix_it():
    without_cta = "\n".join(
        line for line in WELL_FORMED.splitlines() if not line.startswith("CTA:")
    )
    with pytest.raises(EmailCopyError, match="CTA"):
        parse_email(without_cta, position=1)


def test_a_wall_of_prose_is_rejected():
    """The exact failure this pipeline shipped: one unbroken block of text that
    reads like a memo and gets archived like one."""
    wall = WELL_FORMED.split("BODY:")[0] + "BODY:\n" + " ".join(["word"] * 120)

    with pytest.raises(EmailCopyError) as caught:
        parse_email(wall, position=1)

    assert "block" in str(caught.value)


def test_an_email_that_argues_twice_is_rejected():
    """The writer is told to stop at 200 words, and a rule nothing checks is a
    suggestion. The gap between that instruction and the old 320-word ceiling
    is where every additive pass in the system landed: a 250-word email that
    reads as a compressed product page used to pass every check there is."""
    long_email = Email(
        position=1,
        subject="Short enough",
        preview_text="something else entirely",
        greeting="Hi there,",
        body="\n\n".join(" ".join(["word"] * 40) for _ in range(7)),
        call_to_action="Start free",
        sign_off="- The team",
    )
    assert any("280 words" in issue for issue in structural_issues(long_email))


def test_a_paragraph_over_three_lines_is_rejected_by_name():
    email = Email(
        position=1,
        subject="Short enough",
        preview_text="something else entirely",
        greeting="Hi there,",
        body=" ".join(["word"] * 60) + "\n\nSecond block.\n\nThird block here.",
        call_to_action="Start free",
        sign_off="- The team",
    )
    assert any("block 1 is 60 words" in issue for issue in structural_issues(email))


def test_bullets_are_allowed_to_be_a_block_but_not_to_be_paragraphs():
    scannable = Email(
        position=1,
        subject="Short enough",
        preview_text="something else entirely",
        greeting="Hi there,",
        body=(
            "You wrote it three times last month, by hand, every single release without fail, "
            "and every one of them still needed a second pass before it went out.\n\n"
            "- Reads your commits\n- Writes the note\n- Sounds like you\n\n"
            "Nine seconds, then you edit it or you send it exactly as it stands today, which is "
            "what most people end up doing after the first week."
        ),
        call_to_action="Start free",
        sign_off="- The team",
    )
    assert structural_issues(scannable) == []


def test_a_preview_that_only_repeats_the_subject_is_rejected():
    email = Email(
        position=1,
        subject="Your release notes, written for you",
        preview_text="Your release notes, written for you.",
        greeting="Hi there,",
        body="One block here.\n\nSecond block here.\n\n" + " ".join(["word"] * 60),
        call_to_action="Start free",
        sign_off="- The team",
    )
    assert any("repeats the subject" in issue for issue in structural_issues(email))


def test_the_rendered_email_is_complete_enough_to_send_untouched():
    rendered = render_email(parse_email(WELL_FORMED, position=1))

    assert rendered.startswith("Subject: Your release notes, written for you")
    assert "Preview text: from the commits you already pushed" in rendered
    assert "\nHi there,\n" in rendered
    # The ask reaches the clipboard - as its own line, ready to be hyperlinked.
    assert "\nStart free →\n" in rendered
    assert "\n- The team" in rendered
    assert rendered.rstrip().endswith("P.S. The free tier stays free after the trial.")


def test_a_postscript_is_not_labelled_twice():
    email = parse_email(WELL_FORMED.replace("PS: The free", "PS: P.S. The free"), position=1)
    assert render_email(email).count("P.S.") == 1
