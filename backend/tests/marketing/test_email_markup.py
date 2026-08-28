"""The two marks a writer may use, and everywhere they must not reach.

The load-bearing tests here are the stripping ones. Every gate in the system
runs on `render_email`, so markup that survives into that rendering is markup
the evidence gate tries to match against a ledger quotation and the stock
phrase gate tries to find a banned substring in. Both fail silently and in
opposite directions - one blocks a true sentence, the other lets a banned one
through - which is why the marks come out in exactly one place.
"""

from app.knowledge.ledger import Evidence, EvidenceIndex, EvidenceKind, EvidenceLedger
from app.marketing.email_copy import (
    _MAX_PARAGRAPH_WORDS,
    CALLOUT_PREFIX,
    MAX_BOLD_SPANS,
    Email,
    has_markup,
    render_email,
    strip_markup,
    structural_issues,
)
from app.marketing.gates import evidence_gate, stock_phrase_gate
from app.marketing.render_html import BrandStyle, EmailTier, render_html


def email(body: str, **overrides) -> Email:
    payload: dict = {
        "position": 1,
        "subject": "The thing that changed on Monday",
        "preview_text": "Two minutes, and you can stop doing it by hand",
        "greeting": "Hi there,",
        "body": body,
        "call_to_action": "See how it works",
        "sign_off": "- Marco",
    }
    payload.update(overrides)
    return Email(**payload)


# ------------------------------------------------------------- the stripping


def test_the_marks_never_reach_the_plain_text_deliverable():
    """`**` is noise to a person reading the text version, and the text
    version is what the user actually pastes and sends."""
    body = f"We shipped it.\n\n{CALLOUT_PREFIX}**20% off** until Friday.\n\nThat is all."

    rendered = render_email(email(body))

    assert "**" not in rendered
    assert "> " not in rendered
    assert "20% off until Friday." in rendered


def test_bold_inside_a_quotation_does_not_break_its_match_to_the_ledger():
    """The failure this stripping exists to prevent, in the one place it bites.

    A bare figure is fine either way - the gate looks the number up on its
    own, and the marks around it change nothing. A *quotation* is matched
    whole against the corpus, so a writer that emphasises three words inside a
    testimonial it was told to cite produces a string that matches nothing,
    and a true, correctly-cited quotation is blocked as something nobody said.
    Checked against the unstripped copy: it fails this gate.
    """
    ledger = EvidenceLedger(
        entries=[
            Evidence(
                id="E1",
                kind=EvidenceKind.TESTIMONIAL,
                claim="Dana Ellis at Foldwork on what it replaced",
                verbatim="It replaced a job nobody wanted, and it took nine seconds.",
            )
        ]
    )
    body = (
        "Dana put it plainly.\n\n"
        '"It replaced a job nobody wanted, and it took **nine seconds**."\n\n'
        "That was one afternoon of setup."
    )

    assert not evidence_gate(body, EvidenceIndex(ledger)).passed
    report = evidence_gate(render_email(email(body)), EvidenceIndex(ledger))

    assert report.passed, report.render()


def test_markup_cannot_smuggle_a_banned_phrase_past_the_gate():
    """The failure in the other direction: the stock phrase gate is a
    substring test, so `**limited time** only` would read as two harmless
    fragments if the marks survived."""
    body = (
        "It closes soon.\n\nThis is a **limited time** only deal.\n\nWorth a look."
    )

    report = stock_phrase_gate(render_email(email(body)), ("limited time only",))

    assert not report.passed


def test_a_callout_line_is_not_counted_as_a_word():
    body = f"{CALLOUT_PREFIX}Save twenty percent"

    assert len(strip_markup(body).split()) == 3


def test_an_unmarked_email_is_reported_as_unmarked():
    assert not has_markup("Nothing here is set apart.")
    assert has_markup("Something **is**.")
    assert has_markup(f"{CALLOUT_PREFIX}And so is this.")


# ---------------------------------------------------------------- the render


def test_bold_becomes_strong_and_the_text_around_it_is_escaped():
    """Escape first, substitute after - the only order that cannot print its
    own tags at the reader."""
    body = "Costs <£29> a month.\n\nThat is **half** what you pay now.\n\nSame data."

    out = render_html(email(body))

    assert "<strong style=" in out
    assert ">half</strong>" in out
    assert "&lt;£29&gt;" in out
    assert "**" not in out


def test_a_callout_is_a_table_cell_in_both_tiers_and_filled_in_only_one():
    """Outlook renders mail through Word, which ignores background and padding
    on a div and honours both on a cell. The fill is what separates a
    person-to-person aside from a company's highlighted offer."""
    body = f"We shipped.\n\n{CALLOUT_PREFIX}**20% off** until Friday.\n\nThat is all."

    plain = render_html(email(body), EmailTier.PLAIN)
    branded = render_html(email(body), EmailTier.BRANDED, BrandStyle(name="Acme"))

    assert "border-left:3px solid" in plain
    assert "background-color:#f6f8fb" not in plain
    assert "background-color:#f6f8fb" in branded
    assert "20% off" in plain


def test_a_paragraph_that_opens_in_bold_is_not_rendered_as_a_bullet():
    """`*` is a bullet prefix, so a naive check turns an opening bold phrase
    into a one-item list nobody wrote."""
    body = "**Monday** is when it changes.\n\nHere is what happens.\n\nNothing else."

    out = render_html(email(body))

    assert "<ul" not in out
    assert "<strong" in out


def test_bold_inside_a_bullet_survives():
    body = "What you get:\n\n- **9 seconds** per note\n- no card\n\nThat is the whole thing."

    out = render_html(email(body))

    assert "<ul" in out
    assert "<strong" in out


# ------------------------------------------------------------------- the CTA


def test_without_a_url_the_branded_tier_falls_back_to_a_link():
    """A dead button is worse than a link: the reader clicks and lands
    nowhere, which is a thing they learn about the sender."""
    out = render_html(
        email("One.\n\nTwo.\n\nThree."), EmailTier.BRANDED, BrandStyle(name="Acme")
    )

    assert 'href="#"' in out
    assert "display:inline-block;padding:16px 40px" not in out


def test_with_a_url_the_branded_tier_draws_a_real_button():
    out = render_html(
        email("One.\n\nTwo.\n\nThree."),
        EmailTier.BRANDED,
        BrandStyle(name="Acme", cta_url="https://acme.test/start"),
    )

    assert 'href="https://acme.test/start"' in out
    assert "display:inline-block;padding:16px 40px" in out


def test_the_plain_tier_links_rather_than_buttons_even_with_a_url():
    """In a person-to-person email a button is the tell that it came from a
    marketing tool."""
    out = render_html(
        email("One.\n\nTwo.\n\nThree."),
        EmailTier.PLAIN,
        BrandStyle(cta_url="https://acme.test/start"),
    )

    assert 'href="https://acme.test/start"' in out
    assert "display:inline-block;padding:16px 40px" not in out


def test_a_cta_url_is_escaped_into_the_attribute():
    out = render_html(
        email("One.\n\nTwo.\n\nThree."),
        EmailTier.BRANDED,
        BrandStyle(name="Acme", cta_url='https://acme.test/"><script>'),
    )

    assert "<script>" not in out


def test_the_document_declares_itself_light():
    """Apple Mail and Outlook invert an undeclared palette themselves, and an
    inversion that repaints the callout's fill but not the text on it is how a
    highlighted offer becomes unreadable."""
    out = render_html(email("One.\n\nTwo.\n\nThree."))

    assert 'name="color-scheme" content="light"' in out


def test_no_field_leaks_a_mark_into_the_text_a_user_pastes():
    """Caught by rendering a real sample and reading it: stripping only the
    body left `**Friday**` in the P.S., which is where a deadline gets
    repeated and therefore the second most likely place to be bolded."""
    marked = email(
        "One.\n\nTwo.\n\nThree.",
        subject="**Friday** is the last day",
        preview_text="It stops working at **midnight**",
        greeting="Hi **there**,",
        call_to_action="Finish **now**",
        sign_off="- **Marco**",
        postscript="The code survives the week - the **20%** does not.",
    )

    rendered = render_email(marked)

    assert "**" not in rendered
    assert "20% does not" in rendered


# ------------------------------------------------------------- the layout pass


def test_a_long_callout_keeps_its_box_instead_of_being_dismembered():
    """The bug this guards is silent and unrecoverable.

    The layout pass splits any block over the paragraph width at a sentence
    boundary. A callout split that way keeps `> ` on the first piece only, so
    the box closes round the opening sentence and the rest of the offer
    becomes ordinary prose - and nothing downstream can tell, because by then
    it simply is ordinary prose.
    """
    from app.marketing.email_copy import reflow

    callout = (
        "> **20% off the first year** with the code that is already sitting on your "
        "cart right now. It stops working on Friday at midnight whatever else happens "
        "to you that week. This is genuinely the very last time that we are going to "
        "mention any part of it to you at all, and we do mean that."
    )
    assert len(callout.split()) > _MAX_PARAGRAPH_WORDS, "the sample must be wide enough to split"

    blocks = reflow(callout).split("\n\n")

    assert len(blocks) == 1
    assert blocks[0].startswith(CALLOUT_PREFIX)


def test_an_over_long_callout_comes_back_to_the_writer_as_a_fix():
    """Not splitting it is only half the answer: a box round a whole paragraph
    draws the eye to something that then has to be read like everything else,
    so the writer is told to shorten it or drop the marks."""
    from app.marketing.email_copy import structural_issues

    long_callout = (
        "> **20% off the first year** with the code already sitting on your cart right "
        "now. It stops working on Friday at midnight whatever else happens that week. "
        "This is genuinely the very last time that we are going to mention it at all."
    )
    marked = email(
        "One short opener here now.\n\n"
        + long_callout
        + "\n\nAnd a closing line that carries more weight than nothing at all."
    )

    issues = structural_issues(marked)

    assert any("set apart" in issue for issue in issues), issues


def test_a_callout_inside_the_limit_is_left_alone():
    from app.marketing.email_copy import structural_issues

    marked = email(
        "You left a Trellis Pro plan sitting in your cart on Tuesday afternoon.\n\n"
        f"{CALLOUT_PREFIX}**20% off** with the code on your cart. It stops on Friday.\n\n"
        "If the migration is the thing that is stopping you here, reply to this and we "
        "will sit down and do the whole of it with you this week, at whatever hour "
        "happens to suit you and your team best."
    )

    assert structural_issues(marked) == []


# ------------------------------------------------------- the branded tier

BRAND = BrandStyle(
    name="Trellis",
    primary_color="#7c3aed",
    footer_lines=("Trellis Ltd",),
    cta_url="https://trellis.test/cart",
    unsubscribe_url="https://trellis.test/unsubscribe",
)


def marked_email(**overrides) -> Email:
    body = (
        "You left a Pro plan in your cart on Tuesday and never came back to it.\n\n"
        f"{CALLOUT_PREFIX}**20% off the first year** with the code already on your cart. "
        "It stops **Friday**.\n\n"
        "Reply to this and we will do the migration with you this week."
    )
    return email(body, **overrides)


def test_the_offer_becomes_a_hero_figure_on_the_branded_tier_only():
    """The single biggest visual difference between the tiers.

    A tinted box round 16px text is a paragraph with a border and the eye
    does not stop for it. What makes "20% off" land is size - so the first
    bolded fragment of a callout is promoted out of the sentence and set at
    34px, and the rest becomes supporting text under it.
    """
    branded = render_html(marked_email(), EmailTier.BRANDED, BRAND)
    plain = render_html(marked_email(), EmailTier.PLAIN)

    assert "font-size:34px" in branded
    assert ">20% off the first year</p>" in branded
    # Plain sets nothing larger than its body. That is the tier, not an
    # oversight: a person writing to a person does not set a hero figure.
    assert "font-size:34px" not in plain
    assert "20% off the first year" in plain


def test_a_callout_with_nothing_bolded_still_renders_without_a_hero():
    body = (
        "You left a Pro plan in your cart on Tuesday and never came back to it.\n\n"
        f"{CALLOUT_PREFIX}The code on your cart stops working on Friday at midnight.\n\n"
        "Reply to this and we will do the migration with you this week."
    )

    out = render_html(email(body), EmailTier.BRANDED, BRAND)

    assert "font-size:34px" not in out
    assert "stops working on Friday" in out


def test_a_headline_and_eyebrow_open_a_branded_email():
    out = render_html(
        marked_email(eyebrow="Your cart", headline="You left a Pro plan behind"),
        EmailTier.BRANDED,
        BRAND,
    )

    assert "font-size:29px" in out
    assert "<h1 style=" in out
    assert "text-transform:uppercase" in out
    assert "You left a Pro plan behind" in out


def test_the_plain_tier_ignores_a_headline_it_was_handed():
    """The tier is chosen per campaign and the writer decides the copy, so the
    two can disagree. A cold email that arrives with a headline is a cold
    email, not a newsletter - the headline is dropped rather than setting a
    29px line above "Hi there,"."""
    out = render_html(
        marked_email(eyebrow="Your cart", headline="You left a Pro plan behind"),
        EmailTier.PLAIN,
    )

    assert "<h1" not in out
    assert "text-transform:uppercase" not in out


def test_a_branded_email_without_a_headline_opens_on_its_greeting():
    out = render_html(marked_email(), EmailTier.BRANDED, BRAND)

    assert "<h1" not in out
    assert "Hi there," in out


def test_the_branded_tier_has_a_scale_and_the_plain_tier_does_not():
    """The diagnosis this whole tier exists to answer: the first version had
    one visible size, 16px, from greeting to sign-off, so a reader's eye had
    nowhere to land."""
    import re

    def sizes(out: str) -> set[int]:
        return {int(n) for n in re.findall(r"font-size:(\d+)px", out)} - {0, 1}

    branded = sizes(
        render_html(
            marked_email(eyebrow="Your cart", headline="You left a Pro plan behind"),
            EmailTier.BRANDED,
            BRAND,
        )
    )
    plain = sizes(render_html(marked_email(), EmailTier.PLAIN))

    assert max(branded) >= 34
    assert len(branded) >= 6
    assert max(plain) <= 16


def test_the_footer_only_offers_an_unsubscribe_when_there_is_one():
    """A footer that says "Unsubscribe" over a dead link is worse than one
    that does not mention it: the reader clicks, nothing happens, and the next
    thing they press is the spam button."""
    with_link = render_html(marked_email(), EmailTier.BRANDED, BRAND)
    without = render_html(
        marked_email(), EmailTier.BRANDED, BrandStyle(name="Trellis", footer_lines=("Trellis Ltd",))
    )

    assert "Unsubscribe" in with_link
    assert 'href="https://trellis.test/unsubscribe"' in with_link
    assert "Unsubscribe" not in without


def test_the_accent_rule_renders_even_with_no_logo_and_no_name():
    """The cheapest "this was designed" signal there is, and the one thing in
    the header that no client can block."""
    out = render_html(marked_email(), EmailTier.BRANDED, BrandStyle(primary_color="#7c3aed"))

    assert "background-color:#7c3aed;height:4px" in out


def test_a_branded_email_stays_far_inside_the_clipping_limit():
    from app.marketing.render_html import MAX_EMAIL_BYTES

    out = render_html(
        marked_email(eyebrow="Your cart", headline="You left a Pro plan behind"),
        EmailTier.BRANDED,
        BRAND,
    )

    assert len(out.encode("utf-8")) < MAX_EMAIL_BYTES // 4


# --------------------------------------------------------- the markup budget


def _body(*blocks: str) -> str:
    return "\n\n".join(blocks)


def test_a_fourth_bold_phrase_comes_back_to_the_writer():
    """prompts/writer.md asks for at most two and says why - "three bold
    phrases is the same as none, because the eye has nothing left to land on".
    Nothing checked it, and a rule nothing checks is a suggestion.
    """
    over = email(
        _body(
            "**Nine seconds** is what it takes.",
            "You shipped on **Tuesday** and wrote it up on **Friday**, which is the "
            "gap this closes.",
            "It reads your last **twenty** entries first.",
        )
    )

    issues = structural_issues(over)

    assert any("in bold" in issue for issue in issues)
    assert f"{MAX_BOLD_SPANS} at the outside" in " ".join(issues)


def test_the_budget_leaves_room_for_the_two_the_prompt_asks_for():
    """Checked at three and asked for at two, the same slack as 45 words asked
    and 50 checked: ordinary variation must not cost a repair turn."""
    inside = email(
        _body(
            "**Nine seconds** is what it takes.",
            "You shipped on Tuesday and wrote it up on Friday. That gap is not a "
            "discipline problem: the person who has to describe the work is the person "
            "who just spent a week doing it.",
            "It reads the commits you already merged, and your last twenty entries "
            "before that, so the note comes out sounding like you wrote it.",
            f"{CALLOUT_PREFIX}**1,500 free credits** - no card, and it stays free.",
        )
    )

    assert structural_issues(inside) == []


def test_a_second_box_is_a_second_headline():
    """`render_html` sets the first bolded phrase inside a callout very large
    and treats it as the one thing the email is about, so two boxes leave the
    layout with no focal point rather than with two."""
    two_boxes = email(
        _body(
            "You shipped on Tuesday and wrote it up on Friday, which is the gap.",
            f"{CALLOUT_PREFIX}**1,500 free credits** to start.",
            f"{CALLOUT_PREFIX}**20% off** until Friday.",
        )
    )

    issues = structural_issues(two_boxes)

    assert any("set apart in a box" in issue for issue in issues)
