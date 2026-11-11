"""What the rendered email must satisfy to survive a real inbox.

These are the whole quality bar for rendering, and they can be, because no
model is involved: the same email renders to the same bytes every time. The
rules are not taste - they are the ones that decide whether a message arrives
looking like it was designed or like it was broken, in clients nobody can
test by hand on every run.
"""

import re
from dataclasses import replace
from html.parser import HTMLParser

import pytest

from app.marketing.email_copy import Email
from app.marketing.render_html import (
    MAX_EMAIL_BYTES,
    BrandStyle,
    EmailTier,
    Picture,
    render_html,
    resolve_tier,
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
    # Once. The preheader's padding entities used to be multiplied by eight
    # together with the literals they were written beside, which repeated the
    # opening <div> and the preview line with them - so the reader saw their
    # preview text eight times, inside eight divs only one of which closed.
    assert html.count("the part of shipping nobody scheduled time for") == 1


@pytest.mark.parametrize("tier", list(EmailTier))
def test_every_tag_that_opens_is_closed(tier: EmailTier):
    """Well-formedness, checked rather than assumed.

    Every other test here reads the document as a string, which is how eight
    unclosed divs shipped: each assertion passed on markup no client could
    render. Outlook and Gmail both repair broken structure by guessing, and
    what they guess is not what the layout was for.
    """
    html = render_html(_email(), tier, BRAND)

    unclosed = _unclosed_tags(html)

    assert not unclosed, f"never closed: {unclosed}"


def test_a_preview_that_is_only_whitespace_renders_no_preheader():
    assert "display:none" not in render_html(_email(preview_text="   "))


class _TagStack(HTMLParser):
    """Open tags that never close, in document order.

    `convert_charrefs` stays on so the padding entities are text rather than
    parse events. Void elements close themselves and are never stacked.
    """

    VOID = frozenset({"meta", "img", "br", "hr", "input", "link", "area", "base"})

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.open: list[str] = []
        self.unclosed: list[str] = []

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag not in self.VOID:
            self.open.append(tag)

    def handle_startendtag(self, tag: str, attrs: list) -> None:
        pass

    def handle_endtag(self, tag: str) -> None:
        if tag in self.open:
            # Everything opened after the tag being closed is unclosed itself.
            while self.open:
                popped = self.open.pop()
                if popped == tag:
                    break
                self.unclosed.append(popped)


def _unclosed_tags(markup: str) -> list[str]:
    parser = _TagStack()
    parser.feed(markup)
    parser.close()
    return parser.unclosed + list(reversed(parser.open))


def test_the_logo_falls_back_to_the_name_it_is_blocked():
    """Images are blocked on first open in most clients, so a header that is
    only a logo is usually a blank header."""
    html = render_html(_email(), EmailTier.BRANDED, BRAND)

    assert 'alt="Notewright"' in html


def test_a_brand_with_no_style_at_all_still_renders():
    html = render_html(_email(), EmailTier.BRANDED, BrandStyle())

    assert "The work shipped Tuesday" in html
    assert "<img" not in html


def test_the_wordmark_links_to_the_brand_site_and_the_footer_names_it():
    """Most brands never upload a logo, so the name is their mark. The footer
    that fell back to the same name now says where the company lives."""
    style = BrandStyle(name="Cabaia", website_url="https://www.cabaia.fr/")
    html = render_html(_email(), EmailTier.BRANDED, style)

    assert html.count('href="https://www.cabaia.fr/"') == 2
    assert ">cabaia.fr</a>" in html


def test_a_footer_that_already_names_the_site_does_not_name_it_twice():
    style = BrandStyle(
        name="Cabaia",
        website_url="https://www.cabaia.fr/",
        footer_lines=("Cabaia SAS", "cabaia.fr - 12 rue des Lilas, Paris"),
    )
    html = render_html(_email(), EmailTier.BRANDED, style)

    assert ">cabaia.fr</a>" not in html
    assert "cabaia.fr - 12 rue des Lilas, Paris" in html


def test_a_plain_email_grows_no_masthead_from_the_site_alone():
    """Plain is one person writing to another. A website on the brand is not
    a reason to give the letter a header or a footer."""
    style = BrandStyle(name="Cabaia", website_url="https://www.cabaia.fr/")

    assert "cabaia.fr" not in render_html(_email(), EmailTier.PLAIN, style)


def test_a_site_that_is_not_a_web_address_is_never_linked():
    style = BrandStyle(name="Cabaia", website_url="javascript:alert(1)")

    assert "javascript:" not in render_html(_email(), EmailTier.BRANDED, style)


# ------------------------------------------------------------- the product

DUFFLE = Picture(
    url="https://www.cabaia.fr/cdn/shop/files/duffle.jpg?v=1",
    alt='Duffle "Reykjavik" <grand>',
    width=1200,
    height=1200,
)


def test_the_product_sits_under_the_headline_and_leads_where_the_button_does():
    """A reader who taps a photograph of a bag expects to land on the bag."""
    style = replace(BRAND, cta_url="https://www.cabaia.fr/products/duffle", picture=DUFFLE)

    html = render_html(_email(headline="Partir le vendredi soir"), EmailTier.BRANDED, style)

    assert 'src="https://www.cabaia.fr/cdn/shop/files/duffle.jpg?v=1"' in html
    assert html.count('href="https://www.cabaia.fr/products/duffle"') == 2
    assert 'alt="Duffle &quot;Reykjavik&quot; &lt;grand&gt;"' in html
    assert html.index("Partir le vendredi soir") < html.index("duffle.jpg") < html.index("Hi there,")


def test_a_square_photograph_is_set_smaller_than_a_landscape_one():
    """A square shot at the full measure is 528px tall and pushes the whole
    argument below the fold."""
    def rendered(picture: Picture) -> str:
        return render_html(_email(), EmailTier.BRANDED, replace(BRAND, picture=picture))

    assert 'width="360"' in rendered(DUFFLE)
    assert 'width="528"' in rendered(replace(DUFFLE, width=1200, height=630))
    assert 'width="360"' in rendered(replace(DUFFLE, width=0, height=0))


def test_a_plain_email_never_carries_a_photograph():
    html = render_html(_email(), EmailTier.PLAIN, replace(BRAND, picture=DUFFLE))

    assert "duffle.jpg" not in html


def test_a_picture_that_is_not_a_web_address_is_dropped():
    style = replace(BRAND, picture=Picture(url="javascript:alert(1)"))

    assert "javascript:" not in render_html(_email(), EmailTier.BRANDED, style)


def test_a_quoted_customer_is_set_as_a_testimonial_not_as_an_offer():
    """A number inside somebody's sentence is theirs; set at hero size it
    would become ours."""
    body = (
        "A weekend away starts on Friday, straight from the office desk.\n\n"
        "> « **Le seul sac** qui tient tout mon week-end. »\n> — Julie, cliente\n\n"
        "The bag opens wide enough for the laptop and the shoes."
    )

    html = render_html(_email(body=body), EmailTier.BRANDED, BRAND)

    assert "&mdash; Julie, cliente" in html
    assert "qui tient tout mon week-end. »" in html
    assert "font-size:34px" not in html


def test_a_speaker_named_after_the_quotation_on_one_line_is_found_too():
    body = (
        "A weekend away starts on Friday, straight from the office desk.\n\n"
        "> “It holds everything for two nights.” - Julie, verified buyer\n\n"
        "The bag opens wide enough for the laptop and the shoes."
    )

    html = render_html(_email(body=body), EmailTier.PLAIN, BRAND)

    assert "&mdash; Julie, verified buyer" in html
    assert "“It holds everything for two nights.”" in html


# ------------------------------------------------------------- the colour


def test_a_pale_brand_colour_keeps_its_button_and_gets_dark_words_on_it():
    """Yellow is a fine button and an unreadable link."""
    style = replace(BRAND, primary_color="#ffd400", cta_url="https://x.example/")

    html = render_html(_email(headline="New season", eyebrow="Nouveau"), EmailTier.BRANDED, style)

    button = re.search(r'background-color:#ffd400;border-radius:8px;"><a [^>]*?;color:(#[0-9a-f]{6})', html)
    assert button is not None and button.group(1) == "#14161a"
    assert 'color:#8a7200;">Nouveau</p>' in html, "the eyebrow, darkened until it reads"


def test_a_colour_too_pale_to_see_on_white_is_never_a_surface():
    style = replace(BRAND, primary_color="#faf7f0", cta_url="https://x.example/")

    html = render_html(_email(), EmailTier.BRANDED, style)

    assert "background-color:#faf7f0" not in html


# ------------------------------------------------------------- which tier


@pytest.mark.parametrize(
    ("requested", "has_brand", "relationship", "expected"),
    [
        # A choice the user made wins, whoever is reading.
        ("plain", True, "subscriber", EmailTier.PLAIN),
        ("branded", False, "cold", EmailTier.BRANDED),
        # A brand writing to anyone who is not cold looks like a company -
        # including a reader nobody described, who has not bought but is not
        # cold for that.
        (None, True, "unknown", EmailTier.BRANDED),
        (None, True, "prospect", EmailTier.BRANDED),
        (None, True, "subscriber", EmailTier.BRANDED),
        (None, True, "customer", EmailTier.BRANDED),
        # Cold outreach looks like a person, and no brand has nothing to brand.
        (None, True, "cold", EmailTier.PLAIN),
        (None, False, "subscriber", EmailTier.PLAIN),
        # A stored value that is not a tier is no choice at all.
        ("fancy", True, "unknown", EmailTier.BRANDED),
    ],
)
def test_with_no_choice_the_tier_follows_who_is_reading(
    requested, has_brand, relationship, expected
):
    assert resolve_tier(requested, has_brand=has_brand, relationship=relationship) is expected


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


def test_text_export_keeps_the_html_action_destination_without_html_escaping():
    url = "https://example.com/product?source=email&offer=kit"
    email = _email()
    style = BrandStyle(cta_url=url)
    text = text_alternative(email, style)
    assert f"Point it at a branch → {url}" in text
    assert "&amp;" not in text
    assert url.replace("&", "&amp;") in render_html(email, EmailTier.PLAIN, style)


@pytest.mark.parametrize("url", ["javascript:alert(1)", "https://example.com/a\nb", ""])
def test_text_export_does_not_add_an_invalid_or_missing_destination(url):
    assert text_alternative(_email(), BrandStyle(cta_url=url)) == text_alternative(_email())


@pytest.mark.parametrize("tier", [EmailTier.PLAIN, EmailTier.BRANDED])
def test_explicit_sender_footer_survives_both_export_formats(tier):
    style = BrandStyle(footer_lines=("Société Exemple", "12 rue des Lilas"),
                       unsubscribe_url="https://example.com/unsubscribe?a=1&b=2")
    email = _email()
    markup = render_html(email, brand=style, tier=tier)
    text = text_alternative(email, style)
    assert "12 rue des Lilas" in markup
    assert "12 rue des Lilas" in text
    assert "https://example.com/unsubscribe?a=1&amp;b=2" in markup
    assert "https://example.com/unsubscribe?a=1&b=2" in text
