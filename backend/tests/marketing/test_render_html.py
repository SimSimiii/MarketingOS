"""What the rendered email must satisfy to survive a real inbox.

These are the whole quality bar for rendering, and they can be, because no
model is involved: the same email renders to the same bytes every time. The
rules are not taste - they are the ones that decide whether a message arrives
looking like it was designed or like it was broken, in clients nobody can
test by hand on every run.
"""

import re

import pytest

from app.marketing.email_copy import Email
from app.marketing.render_html import (
    MAX_EMAIL_BYTES,
    BrandStyle,
    EmailTier,
    render_html,
    text_alternative,
)


def _email(**overrides) -> Email:
    fields = {
        "position": 1,
        "subject": "The 4pm Friday paragraph",
        "preview_text": "the part of shipping nobody scheduled time for",
        "greeting": "Hi there,",
        "body": (
            "The work shipped Tuesday. The note about it is what keeps you here Friday.\n\n"
            "Your script assembles the commits. It cannot say why any of them matter.\n\n"
            "Point it at the branch you merged and read what comes back."
        ),
        "call_to_action": "Point it at a branch",
        "sign_off": "- the Notewright team",
        "postscript": "The free tier stays free after the trial.",
    }
    fields.update(overrides)
    return Email(**fields)


BRAND = BrandStyle(
    name="Notewright",
    logo_url="https://example.com/logo.png",
    primary_color="#1a56db",
    footer_lines=("Notewright Ltd", "12 Example Street, London"),
)


# ------------------------------------------------------------- the copy survives


@pytest.mark.parametrize("tier", list(EmailTier))
def test_every_word_of_the_email_reaches_the_page(tier: EmailTier):
    """The renderer's one absolute duty. Copy that took thirteen minutes and
    four rewrites to get right must not be silently dropped by a layout."""
    email = _email()
    html = render_html(email, tier, BRAND)

    for fragment in (
        "The work shipped Tuesday",
        "It cannot say why any of them matter",
        "Point it at the branch you merged",
        "Hi there,",
        "Point it at a branch",
        "- the Notewright team",
        "The free tier stays free after the trial.",
    ):
        assert fragment in html, fragment


def test_the_writers_line_breaks_are_kept():
    """"A short opening line on its own" is a rule in the writing prompt.
    Collapsing single newlines into prose deletes the thing it asked for."""
    email = _email(body="One line.\nAnother line.\n\nA second block here.")

    assert "<br />" in render_html(email)


def test_a_bulleted_block_becomes_a_real_list():
    email = _email(
        body=(
            "Here is what changes.\n\n"
            "- notes written from the branch\n"
            "- your tone, learned from old notes\n\n"
            "That is the whole product."
        )
    )
    html = render_html(email)

    assert html.count("<li") == 2
    assert "<ul" in html


def test_a_postscript_that_already_says_ps_does_not_say_it_twice():
    assert "P.S. P.S." not in render_html(_email(postscript="P.S. One more thing."))


def test_an_email_without_a_postscript_renders_without_one():
    assert "P.S." not in render_html(_email(postscript=""))


# ------------------------------------------------------------------ safety


def test_copy_containing_html_is_escaped_not_executed():
    """The body is text written by a model from a user's own material, and
    both are untrusted input to a renderer. A subject with a tag in it must
    render as characters, never as markup."""
    email = _email(
        subject="<script>alert(1)</script>",
        body=(
            "First block is fine here.\n\n"
            "<img src=x onerror=alert(1)> is what they pasted.\n\n"
            "Third block, still fine."
        ),
    )
    html = render_html(email)

    # The test is about tag brackets, not about the word "onerror": once `<`
    # is escaped the attribute is inert text, and asserting on the word alone
    # fails on markup that is already safe.
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "<img src=x" not in html
    assert "&lt;img src=x" in html


def test_a_brand_colour_that_is_not_a_colour_cannot_reach_the_page():
    """`primary_color` goes straight into a style attribute, so a value that
    is not a hex colour is a way into the markup."""
    hostile = BrandStyle(name="X", primary_color='#fff;"><script>alert(1)</script>')

    html = render_html(_email(), EmailTier.BRANDED, hostile)

    assert "<script>" not in html
    assert "#1a56db" in html


def test_no_remote_asset_is_requested_by_a_plain_email():
    """The typographic tier must be entirely self-contained: a remote image in
    a cold email is a tracking pixel as far as a filter is concerned."""
    html = render_html(_email(), EmailTier.PLAIN, BRAND)

    assert "<img" not in html
    assert "example.com/logo.png" not in html


def test_nothing_loads_a_stylesheet_or_a_script():
    for tier in EmailTier:
        html = render_html(_email(), tier, BRAND)
        assert "<style" not in html
        assert "<script" not in html
        assert "<link" not in html


# ------------------------------------------------------- client compatibility


@pytest.mark.parametrize("tier", list(EmailTier))
def test_the_layout_is_tables_with_inline_styles(tier: EmailTier):
    """Outlook renders mail through Word, which ignores most of the CSS a
    modern page is built with. Tables and inline styles are what survive."""
    html = render_html(_email(), tier, BRAND)

    assert "<table" in html
    assert 'role="presentation"' in html, "layout tables must not be read out by screen readers"
    assert 'style="' in html


@pytest.mark.parametrize("tier", list(EmailTier))
def test_it_is_readable_on_a_phone(tier: EmailTier):
    html = render_html(_email(), tier, BRAND)

    assert 'name="viewport"' in html
    assert "max-width:600px" in html


@pytest.mark.parametrize("tier", list(EmailTier))
def test_it_stays_well_under_the_clipping_limit(tier: EmailTier):
    """Gmail clips past ~102KB and hides everything below - in an email, that
    is usually the call to action."""
    size = len(render_html(_email(), tier, BRAND).encode("utf-8"))

    assert size < MAX_EMAIL_BYTES // 4, f"{size} bytes"


def test_the_preview_text_is_present_but_not_shown_twice():
    html = render_html(_email())

    assert "the part of shipping nobody scheduled time for" in html
    assert "display:none" in html


def test_the_logo_falls_back_to_the_name_it_is_blocked():
    """Images are blocked on first open in most clients, so a header that is
    only a logo is usually a blank header."""
    html = render_html(_email(), EmailTier.BRANDED, BRAND)

    assert 'alt="Notewright"' in html


def test_a_brand_with_no_style_at_all_still_renders():
    html = render_html(_email(), EmailTier.BRANDED, BrandStyle())

    assert "The work shipped Tuesday" in html
    assert "<img" not in html


# ------------------------------------------------------------- the text part


def test_the_text_part_is_the_canonical_deliverable():
    """Every HTML email carries a text alternative: some readers force it,
    and a message without one scores worse with filters."""
    text = text_alternative(_email())

    assert "Subject: The 4pm Friday paragraph" in text
    assert "<table" not in text


def test_the_html_says_nothing_the_text_does_not():
    """Content parity - the two parts are the same message, not two messages."""
    email = _email()
    html = render_html(email)
    stripped = re.sub(r"<[^>]+>", " ", html)

    for sentence in ("The work shipped Tuesday", "Point it at a branch"):
        assert sentence in stripped
        assert sentence in text_alternative(email)
