"""Turning a finished email into HTML, deterministically.

No model is involved in how an email looks, and that is the point. Asking a
writer to emit HTML puts layout in the same response as copy, at copy prices,
and produces a different layout every time - each one a fresh chance to break
in Outlook, which renders mail through Word's engine and ignores most of what
a model has learned about CSS from the web. Layout has a correct answer, it
does not change per campaign, and anything with a correct answer belongs in
code.

So the model decides what the email says, and this decides what it looks like.
The input is the `Email` the writer already produces - subject, preview,
greeting, body, CTA, sign-off, P.S. are separate typed fields, which is
exactly the structured representation a renderer needs and it already exists.

The copy decides *what* is emphasised and this decides *how loudly*. A
writer marks the words a skimmer must not miss with `**bold**` and marks one
block as the thing the email is really about with a leading `> `; the tier
below then draws that block as a quiet ruled aside or as a filled box. That
split is the same one the whole module rests on - the writer knows which
sentence carries the offer and has no business knowing what colour it is.

Two tiers, because "more designed" is not the same as "better":

- PLAIN is for cold and one-to-one sales mail, and is the default. A person
  writing to a person does not send a newsletter, and a branded template with
  a hero image raises spam scores and depresses replies on exactly the mail
  this system writes most. What it fixes is real though: web-safe typography,
  real spacing, a readable measure, one obvious link.
- BRANDED is for announcements and newsletters, where looking like a company
  is the honest signal. Logo, brand colour, a real button, a footer.

Both are table-based with inline styles, which is not how anyone would write
a web page and is the only thing that survives Outlook, Gmail's clipping and
a decade of client quirks.
"""

import html
import re
from dataclasses import dataclass
from enum import StrEnum

from app.marketing.email_copy import CALLOUT_PREFIX, Email

#: Gmail clips a message past this and shows "[Message clipped] View entire
#: message", which hides the CTA below a fold nobody clicks through. Our own
#: output is nowhere near it; the check exists so an embedded logo cannot
#: quietly push a campaign over.
MAX_EMAIL_BYTES = 102_000

#: The measure every email client has agreed on for twenty years. Wider reads
#: badly on a phone in portrait, and narrower wastes the desktop.
_CONTENT_WIDTH = 600

#: Fonts that exist on the machines that read email, rather than the ones that
#: exist on the machine that wrote it. No webfont: a remote font is a remote
#: request, which Outlook blocks and privacy-minded clients strip.
_SANS = (
    "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif"
)


class EmailTier(StrEnum):
    """How designed this email should look."""

    #: Typography only. The default, and the right answer for cold outreach.
    PLAIN = "plain"
    #: Logo, colour, button, footer. For mail a reader expects from a company.
    BRANDED = "branded"


@dataclass(frozen=True)
class BrandStyle:
    """The few things a branded email needs to look like it came from someone.

    Deliberately tiny. A full design system would be a second product, and
    every field here is one the user can answer in a sentence - anything they
    leave empty falls back to something that still looks deliberate.
    """

    name: str = ""
    #: Absolute URL. Remote images are blocked by default in most clients, so
    #: the logo must never be the only thing carrying the brand.
    logo_url: str = ""
    #: Hex, e.g. "#1a56db". Used for links and the button.
    primary_color: str = "#1a56db"
    #: What goes in the footer under the sign-off - who is sending this, and
    #: any postal address the law where the user operates requires.
    footer_lines: tuple[str, ...] = ()
    #: Where the call to action goes. The writer never knows this - it is told
    #: so, and told to write the words on the link rather than the link - so
    #: it comes from the campaign, or from the brand's own website as a
    #: fallback. Empty renders the CTA as a marked slot rather than a button
    #: to nowhere, which is the honest failure: a dead button in a sent email
    #: costs the reader a click and the sender the reply.
    cta_url: str = ""
    #: Where "Unsubscribe" points in the footer. Marketing mail is required to
    #: carry one in most of the places this will be sent, and a footer that
    #: says "Unsubscribe" over a dead link is worse than one that does not
    #: mention it - so the line only renders when there is somewhere to go.
    unsubscribe_url: str = ""

    @property
    def accent(self) -> str:
        return self.primary_color if _HEX_RE.fullmatch(self.primary_color) else "#1a56db"


_HEX_RE = re.compile(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})")
_BULLET_PREFIXES = ("-", "*", "•", "–", "—")
_PARAGRAPH_SPLIT_RE = re.compile(r"\n\s*\n")
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*", re.DOTALL)

#: The tint behind a callout. A fixed near-white grey rather than a wash of
#: the brand colour: the brand colour arrives as an arbitrary hex from a form,
#: and a dark one behind dark text is unreadable in a way no amount of care at
#: this end can fix. The colour is carried by the rule down the left edge and
#: by the hero figure, where it cannot hurt anything.
_CALLOUT_FILL = "#f6f8fb"


@dataclass(frozen=True)
class _Scale:
    """Everything the two tiers disagree about, in one place.

    The first version of the branded tier was the plain one with a logo, a
    colour and a button added, and it read as flat as the plain one because
    of a thing no amount of colour fixes: every visible size in it was 16px.
    A reader's eye needs somewhere to land, and a single type size gives it
    nowhere.

    So the tiers are two scales rather than one scale with decorations. Plain
    keeps one body size on purpose - a person writing to a person does not set
    a headline - and branded gets six, a hero figure and real dividers. What
    makes the branded one look designed is almost entirely in this table.
    """

    #: Behind the card.
    page: str
    #: Headings and the words a skimmer must not miss.
    ink: str
    body: str
    muted: str
    line: str
    #: Horizontal padding inside the card.
    pad: int
    body_size: int
    #: The first paragraph, set slightly larger so the email has an opening
    #: rather than a beginning. Equal to `body_size` on the plain tier.
    lead_size: int
    headline_size: int
    eyebrow_size: int
    #: Whether the first bolded fragment of a callout is promoted to a hero
    #: figure. This is the single biggest visual difference between the tiers:
    #: a tinted box round 16px text is a paragraph with a border, and the eye
    #: does not stop for it.
    hero: bool
    hero_size: int
    corner: int

    def row(self, inner: str, padding: str | None = None) -> str:
        pad = padding or f"0 {self.pad}px 18px"
        return f'<tr><td style="padding:{pad};">{inner}</td></tr>\n'

    def para(self, inner: str, size: int | None = None, colour: str | None = None) -> str:
        return (
            f'<p style="margin:0;font-family:{_SANS};font-size:{size or self.body_size}px;'
            f'line-height:1.6;color:{colour or self.body};">{inner}</p>'
        )


_PLAIN = _Scale(
    page="#ffffff",
    ink="#111418",
    body="#1f2328",
    muted="#5a6069",
    line="#e8eaed",
    pad=32,
    body_size=16,
    lead_size=16,
    headline_size=22,
    eyebrow_size=11,
    hero=False,
    hero_size=16,
    corner=6,
)

_BRANDED = _Scale(
    page="#eceef3",
    ink="#14161a",
    body="#3d434d",
    muted="#767d89",
    line="#e6e9ef",
    pad=36,
    body_size=16,
    lead_size=17,
    headline_size=29,
    eyebrow_size=11,
    hero=True,
    hero_size=34,
    corner=12,
)


def _scale(tier: EmailTier) -> _Scale:
    return _BRANDED if tier is EmailTier.BRANDED else _PLAIN


def render_html(
    email: Email,
    tier: EmailTier = EmailTier.PLAIN,
    brand: BrandStyle | None = None,
) -> str:
    """One sendable HTML document for one email.

    Self-contained: every style is inline, there is no <style> block to be
    stripped, no script, and no remote asset except a logo the user supplied.

    The two tiers assemble different documents rather than one document with
    decorations bolted on - see `_Scale`. A branded email opens on an eyebrow
    and a headline and gives its offer a hero figure; a plain one opens on the
    greeting and never sets anything larger than its body, because that is
    what one person writing to another looks like.
    """
    style = brand or BrandStyle()
    scale = _scale(tier)
    branded = tier is EmailTier.BRANDED

    blocks: list[str] = []
    if branded:
        blocks.append(_header(style, scale))
        if email.headline.strip():
            if email.eyebrow.strip():
                blocks.append(_eyebrow(email.eyebrow, style, scale))
            blocks.append(_headline(email.headline, scale))
    blocks.append(_greeting(email.greeting, scale, lead=branded and bool(email.headline)))
    blocks.extend(_body_blocks(email.body, style, scale))
    if branded:
        blocks.append(_divider(scale))
    blocks.append(_cta(email.call_to_action, style, tier, scale))
    blocks.append(_signoff(email.sign_off, scale))
    if email.postscript.strip():
        blocks.append(_postscript(email.postscript, scale))
    if branded:
        blocks.append(_footer(style, scale))

    return _document(
        subject=email.subject,
        preview=email.preview_text,
        inner="".join(blocks),
        scale=scale,
    )


def text_alternative(email: Email) -> str:
    """The plain-text part that travels beside the HTML.

    Every HTML email should carry one: some clients prefer it, some readers
    force it, and a message with no text part scores worse with spam filters
    than one with. `render_email` already produces exactly this.
    """
    from app.marketing.email_copy import render_email

    return render_email(email)


# ------------------------------------------------------------------ internals


def _document(subject: str, preview: str, inner: str, scale: _Scale) -> str:
    return (
        '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" '
        '"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">\n'
        '<html xmlns="http://www.w3.org/1999/xhtml" lang="en">\n'
        "<head>\n"
        '<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />\n'
        # Without this Outlook Mobile and Gmail on Android render at desktop
        # width and the reader pinches to zoom.
        '<meta name="viewport" content="width=device-width, initial-scale=1" />\n'
        '<meta name="x-apple-disable-message-reformatting" />\n'
        # Says out loud that this document is designed light. Without it Apple
        # Mail and Outlook invert the palette themselves, and an inversion
        # that repaints the callout\'s fill without repainting the text on it
        # is how a highlighted offer becomes unreadable in dark mode.
        '<meta name="color-scheme" content="light" />\n'
        '<meta name="supported-color-schemes" content="light" />\n'
        f"<title>{html.escape(subject)}</title>\n"
        "</head>\n"
        f'<body style="margin:0;padding:0;background-color:{scale.page};'
        f'-webkit-text-size-adjust:100%;">\n'
        f"{_preheader(preview)}"
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        f'border="0" style="background-color:{scale.page};">\n'
        '<tr><td align="center" style="padding:24px 12px;">\n'
        f'<table role="presentation" width="{_CONTENT_WIDTH}" cellpadding="0" '
        f'cellspacing="0" border="0" style="width:100%;max-width:{_CONTENT_WIDTH}px;'
        f'background-color:#ffffff;border-radius:{scale.corner}px;">\n'
        f"{inner}"
        "</table>\n</td></tr>\n</table>\n</body>\n</html>\n"
    )


def _preheader(preview: str) -> str:
    """The line the inbox shows next to the subject.

    Hidden in the message itself, so it is not said twice. The trailing
    entities stop clients padding the preview with the first words of the
    greeting, which is how a carefully written preview ends up reading
    "...what changes on Monday Hi there, The work shipped".
    """
    if not preview.strip():
        return ""
    # Built in two steps on purpose: adjacent string literals are joined
    # before `*` is applied, so multiplying the padding inline multiplies the
    # opening <div> and the preview with it - eight nested, unclosed divs
    # around eight copies of the preview line, in every email the system has
    # ever rendered.
    padding = "&#8199;&#65279;&#847; " * 8
    return (
        '<div style="display:none;font-size:1px;color:#ffffff;line-height:1px;'
        'max-height:0;max-width:0;opacity:0;overflow:hidden;">'
        f"{html.escape(preview)}{padding}</div>\n"
    )


def _row(content: str, padding: str = "0 32px 16px") -> str:
    return (
        f'<tr><td style="padding:{padding};font-family:{_SANS};font-size:16px;'
        f'line-height:1.55;color:#1f2328;">{content}</td></tr>\n'
    )


def _eyebrow(text: str, style: BrandStyle, scale: _Scale) -> str:
    """Two or three words in small capitals above the headline.

    Letterspaced and in the accent colour, which is the cheapest way to say
    "this is a designed message from a company" - it needs no image, cannot be
    blocked, and costs one table row.
    """
    return scale.row(
        f'<p style="margin:0;font-family:{_SANS};font-size:{scale.eyebrow_size}px;'
        f'font-weight:700;letter-spacing:1.4px;text-transform:uppercase;'
        f'color:{style.accent};">{html.escape(text.strip())}</p>',
        padding=f"26px {scale.pad}px 10px",
    )


def _headline(text: str, scale: _Scale) -> str:
    """The line the reader sees first.

    An `<h1>` with its margin zeroed: the element carries the meaning for a
    screen reader and every visual property is inline, because clients strip
    stylesheets and Outlook applies its own defaults to anything it recognises.
    """
    return scale.row(
        f'<h1 style="margin:0;font-family:{_SANS};font-size:{scale.headline_size}px;'
        f'line-height:1.2;font-weight:800;letter-spacing:-0.5px;color:{scale.ink};">'
        f"{html.escape(text.strip())}</h1>",
        padding=f"0 {scale.pad}px 20px",
    )


def _divider(scale: _Scale) -> str:
    """A rule before the ask.

    A cell with a top border rather than an `<hr>`, which Outlook renders at
    its own weight and colour whatever it is told.
    """
    return (
        f'<tr><td style="padding:6px {scale.pad}px 22px;">'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        f'border="0"><tr><td style="border-top:1px solid {scale.line};font-size:0;'
        'line-height:0;">&nbsp;</td></tr></table></td></tr>\n'
    )


def _greeting(greeting: str, scale: _Scale, lead: bool = False) -> str:
    """The greeting, with less room above it when a headline already opened
    the email - otherwise the two sit in a gap that reads as a missing
    paragraph."""
    top = 10 if lead else 32
    return scale.row(
        scale.para(html.escape(greeting.strip()), colour=scale.body),
        padding=f"{top}px {scale.pad}px 16px",
    )


def _body_blocks(body: str, style: BrandStyle, scale: _Scale) -> list[str]:
    blocks: list[str] = []
    parts = _PARAGRAPH_SPLIT_RE.split(body.strip())
    for index, block in enumerate(parts):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        if all(line.startswith(CALLOUT_PREFIX.strip()) for line in lines):
            blocks.append(
                _callout(
                    [line.removeprefix(CALLOUT_PREFIX.strip()).strip() for line in lines],
                    style,
                    scale,
                )
            )
            continue
        # `**` is checked before the bullet prefixes because `*` is one of
        # them, so a paragraph opening in bold would otherwise be rendered as
        # a one-item list.
        if all(
            line.startswith(_BULLET_PREFIXES) and not line.startswith("**") for line in lines
        ):
            blocks.append(_bullets(lines, style, scale))
            continue
        # Single newlines inside a paragraph are the writer's line breaks, and
        # they carry rhythm - "A short opening line on its own" is a rule in
        # the writing prompt, and collapsing it to prose deletes the thing the
        # prompt asked for.
        size = scale.lead_size if index == 0 else scale.body_size
        blocks.append(
            scale.row(scale.para("<br />".join(_inline(line, scale) for line in lines), size=size))
        )
    return blocks


def _inline(text: str, scale: _Scale) -> str:
    """One line of copy, escaped, with `**bold**` turned into markup.

    Escaping happens first and the tags are added after, which is the only
    safe order: substituting into escaped text can only ever produce the tags
    this function wrote, whereas escaping afterwards would escape its own
    output and print `&lt;strong&gt;` at the reader.

    `<strong>` rather than `<b>`, and with an explicit weight beside it: a few
    clients still normalise `<strong>` to their own idea of bold, and Outlook
    honours the inline style when it ignores the element.
    """
    return _BOLD_RE.sub(
        f'<strong style="font-weight:700;color:{scale.ink};">\\1</strong>', html.escape(text)
    )


def _bullets(lines: list[str], style: BrandStyle, scale: _Scale) -> str:
    """A scannable list, drawn differently by the two tiers.

    Plain keeps a real `<ul>`. It is the semantic element, a screen reader
    announces it as a list of three things, and a person writing to a person
    has no reason to want a coloured marker - the whole point of that tier is
    that nothing in it was designed.

    Branded lays the same lines out as table rows with an accent marker.
    Outlook honours none of `list-style`, `padding` or `margin` on a list, so
    a `<ul>` there is a list at whatever indent Word feels like; the table is
    what every ESP does and it is the only way to put the brand's colour on
    the marker at all. The cost is real and is paid knowingly: the list stops
    being a list to a screen reader.
    """
    if not scale.hero:
        items = "".join(
            f'<li style="margin:0 0 8px;">'
            f"{_inline(line.lstrip(''.join(_BULLET_PREFIXES)).strip(), scale)}</li>"
            for line in lines
        )
        return _row(f'<ul style="margin:0;padding-left:22px;">{items}</ul>')
    items = "".join(
        f"<tr>"
        f'<td valign="top" style="padding:0 10px 10px 0;font-family:{_SANS};'
        f'font-size:{scale.body_size}px;line-height:1.6;color:{style.accent};'
        f'font-weight:700;">&#9656;</td>'
        f'<td valign="top" style="padding:0 0 10px;font-family:{_SANS};'
        f'font-size:{scale.body_size}px;line-height:1.6;color:{scale.body};">'
        f"{_inline(line.lstrip(''.join(_BULLET_PREFIXES)).strip(), scale)}</td></tr>"
        for line in lines
    )
    return (
        f'<tr><td style="padding:0 {scale.pad}px 18px;">'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        f'border="0"><!-- bullets -->{items}</table></td></tr>\n'
    )


def _callout(lines: list[str], style: BrandStyle, scale: _Scale) -> str:
    """The one block this email is really about - the offer, the number, the
    deadline.

    On the branded tier the first bolded fragment is promoted to a hero
    figure at `hero_size` and the rest becomes supporting text under it. That
    single move is the difference between an offer a reader stops for and a
    paragraph with a border round it: what makes "20% off" land is size, not
    a background.

    Drawn as a nested table rather than a styled `<div>` because Outlook
    renders mail through Word, which ignores padding and background on block
    elements and honours both on a table cell.

    Quiet on the plain tier: no fill, no hero, just the rule and the spacing.
    A person writing to a person does not send tinted boxes, and the same
    sentence still deserves to be set apart.
    """
    text = "\n".join(lines)
    figure = ""
    if scale.hero and (match := _BOLD_RE.search(text)):
        figure = match.group(1).strip()
        text = (text[: match.start()] + text[match.end() :]).strip(" \n.,;:-")

    rest = "<br />".join(_inline(line, scale) for line in text.splitlines() if line.strip())
    inner = ""
    if figure:
        inner += (
            f'<p style="margin:0 0 6px;font-family:{_SANS};font-size:{scale.hero_size}px;'
            f'line-height:1.1;font-weight:800;letter-spacing:-1px;color:{style.accent};">'
            f"{html.escape(figure)}</p>"
        )
    if rest:
        inner += scale.para(rest, size=15 if figure else scale.body_size)

    if scale.hero:
        cell = (
            f'background-color:{_CALLOUT_FILL};border:1px solid {scale.line};'
            f"border-radius:10px;padding:22px 24px;"
        )
    else:
        cell = (
            f"border-left:3px solid {style.accent};padding:14px 18px;"
            "border-radius:0 4px 4px 0;"
        )
    return (
        f'<tr><td style="padding:4px {scale.pad}px 22px;">'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        f'border="0"><tr><td style="{cell}font-family:{_SANS};">{inner}</td></tr>'
        "</table></td></tr>\n"
    )


def _cta(label: str, style: BrandStyle, tier: EmailTier, scale: _Scale) -> str:
    """The one thing the email asks for.

    The writer never supplies the href - it is told it does not know the URL
    behind any button, because inventing one sends a real reader to a page
    that does not exist. It comes from the campaign instead, or from the
    brand's website, and when there is neither the anchor stays a marked slot
    for the user to fill rather than a dead link pretending to work.

    A dead button is worse than a link, which is why the branded tier falls
    back to the plain tier's styled link when no URL is known: a reader who
    clicks a button and lands nowhere has been told something about the
    sender that no amount of copy recovers.
    """
    text = html.escape(label.strip())
    href = html.escape(style.cta_url, quote=True) if style.cta_url else ""
    if tier is EmailTier.PLAIN or not href:
        # A styled text link, not a button: in a person-to-person email a
        # button is the tell that it came from a marketing tool.
        return scale.row(
            f'<a href="{href or "#"}" style="font-family:{_SANS};'
            f'font-size:{scale.body_size}px;color:{style.accent};font-weight:600;'
            f'text-decoration:underline;">{text} &rarr;</a>',
            padding=f"8px {scale.pad}px 24px",
        )
    return (
        f'<tr><td align="center" style="padding:4px {scale.pad}px 8px;">'
        f'<table role="presentation" cellpadding="0" cellspacing="0" border="0">'
        f'<tr><td align="center" style="background-color:{style.accent};'
        f'border-radius:8px;">'
        f'<a href="{href}" style="display:inline-block;padding:16px 40px;'
        f'font-family:{_SANS};font-size:16px;font-weight:700;color:#ffffff;'
        f'text-decoration:none;letter-spacing:0.2px;">{text}</a>'
        "</td></tr></table></td></tr>\n"
    )


def _signoff(sign_off: str, scale: _Scale) -> str:
    return scale.row(
        scale.para(html.escape(sign_off.strip()), size=15, colour=scale.muted),
        padding=f"22px {scale.pad}px 20px",
    )


def _postscript(postscript: str, scale: _Scale) -> str:
    """The last thing read, and often the only thing read twice.

    Set apart from the sign-off rather than run on from it: a P.S. that looks
    like another paragraph is a P.S. nobody notices, and the whole reason to
    write one is that people read them.
    """
    text = postscript.strip()
    if not text.upper().startswith("P.S"):
        text = f"P.S. {text}"
    body = _inline(text, scale)
    if scale.hero:
        return (
            f'<tr><td style="padding:0 {scale.pad}px 28px;">'
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            f'border="0" style="background-color:#f6f7f9;border-radius:8px;">'
            f'<tr><td style="padding:14px 18px;font-family:{_SANS};font-size:14px;'
            f'line-height:1.55;color:{scale.muted};">{body}</td></tr>'
            "</table></td></tr>\n"
        )
    return (
        f'<tr><td style="padding:0 {scale.pad}px 32px;font-family:{_SANS};font-size:15px;'
        f'line-height:1.5;color:{scale.muted};border-top:1px solid {scale.line};'
        f'padding-top:20px;">{body}</td></tr>\n'
    )


def _header(style: BrandStyle, scale: _Scale) -> str:
    """The brand's mark, under a rule in the brand's colour.

    Images are blocked by default in most clients on first open, so a header
    that is only a logo is a header that is usually blank - the alt text is
    the company name for exactly that reason. The rule above it carries the
    brand when the logo does not, and cannot be blocked by anything.
    """
    rule = (
        f'<tr><td style="background-color:{style.accent};height:4px;font-size:0;'
        'line-height:0;">&nbsp;</td></tr>\n'
    )
    if not style.logo_url and not style.name:
        return rule
    inner = html.escape(style.name)
    if style.logo_url:
        inner = (
            f'<img src="{html.escape(style.logo_url, quote=True)}" '
            f'alt="{html.escape(style.name, quote=True)}" height="30" '
            'style="display:block;border:0;height:30px;max-height:30px;width:auto;" />'
        )
    return rule + (
        f'<tr><td style="padding:26px {scale.pad}px 0;font-family:{_SANS};font-size:15px;'
        f'font-weight:700;letter-spacing:0.2px;color:{scale.ink};">{inner}</td></tr>\n'
    )


def _footer(style: BrandStyle, scale: _Scale) -> str:
    """Who sent this, where they are, and how to stop receiving it.

    The unsubscribe line renders only when there is somewhere for it to go.
    A footer that says "Unsubscribe" over a dead link is worse than one that
    does not mention it: the reader clicks, nothing happens, and the next
    thing they press is the spam button.
    """
    lines = list(style.footer_lines) or ([style.name] if style.name else [])
    if not lines and not style.unsubscribe_url:
        return ""
    body = "<br />".join(html.escape(line) for line in lines)
    if style.unsubscribe_url:
        href = html.escape(style.unsubscribe_url, quote=True)
        body += (
            f'<br /><br /><a href="{href}" style="color:{scale.muted};'
            'text-decoration:underline;">Unsubscribe</a>'
        )
    return (
        f'<tr><td align="center" style="padding:22px {scale.pad}px 28px;'
        f'background-color:#fafbfc;border-top:1px solid {scale.line};'
        f'font-family:{_SANS};font-size:12px;line-height:1.7;color:{scale.muted};">'
        f"{body}</td></tr>\n"
    )
