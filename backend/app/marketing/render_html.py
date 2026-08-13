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

from app.marketing.email_copy import Email

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

    @property
    def accent(self) -> str:
        return self.primary_color if _HEX_RE.fullmatch(self.primary_color) else "#1a56db"


_HEX_RE = re.compile(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})")
_BULLET_PREFIXES = ("-", "*", "•", "–", "—")
_PARAGRAPH_SPLIT_RE = re.compile(r"\n\s*\n")


def render_html(
    email: Email,
    tier: EmailTier = EmailTier.PLAIN,
    brand: BrandStyle | None = None,
) -> str:
    """One sendable HTML document for one email.

    Self-contained: every style is inline, there is no <style> block to be
    stripped, no script, and no remote asset except a logo the user supplied.
    """
    style = brand or BrandStyle()
    blocks = [_greeting(email.greeting), *_body_blocks(email.body, style, tier)]
    blocks.append(_cta(email.call_to_action, style, tier))
    blocks.append(_signoff(email.sign_off))
    if email.postscript.strip():
        blocks.append(_postscript(email.postscript))

    header = _header(style) if tier is EmailTier.BRANDED else ""
    footer = _footer(style) if tier is EmailTier.BRANDED else ""

    return _document(
        subject=email.subject,
        preview=email.preview_text,
        inner=header + "".join(blocks) + footer,
        tier=tier,
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


def _document(subject: str, preview: str, inner: str, tier: EmailTier) -> str:
    background = "#f4f5f7" if tier is EmailTier.BRANDED else "#ffffff"
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
        f"<title>{html.escape(subject)}</title>\n"
        "</head>\n"
        f'<body style="margin:0;padding:0;background-color:{background};'
        f'-webkit-text-size-adjust:100%;">\n'
        f"{_preheader(preview)}"
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        f'border="0" style="background-color:{background};">\n'
        '<tr><td align="center" style="padding:24px 12px;">\n'
        f'<table role="presentation" width="{_CONTENT_WIDTH}" cellpadding="0" '
        f'cellspacing="0" border="0" style="width:100%;max-width:{_CONTENT_WIDTH}px;'
        f'background-color:#ffffff;border-radius:6px;">\n'
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
    return (
        '<div style="display:none;font-size:1px;color:#ffffff;line-height:1px;'
        'max-height:0;max-width:0;opacity:0;overflow:hidden;">'
        f"{html.escape(preview)}"
        "&#8199;&#65279;&#847; " * 8 + "</div>\n"
    )


def _row(content: str, padding: str = "0 32px 16px") -> str:
    return (
        f'<tr><td style="padding:{padding};font-family:{_SANS};font-size:16px;'
        f'line-height:1.55;color:#1f2328;">{content}</td></tr>\n'
    )


def _greeting(greeting: str) -> str:
    return _row(html.escape(greeting.strip()), padding="32px 32px 16px")


def _body_blocks(body: str, style: BrandStyle, tier: EmailTier) -> list[str]:
    blocks: list[str] = []
    for block in _PARAGRAPH_SPLIT_RE.split(body.strip()):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        if all(line.startswith(_BULLET_PREFIXES) for line in lines):
            blocks.append(_row(_bullets(lines)))
            continue
        # Single newlines inside a paragraph are the writer's line breaks, and
        # they carry rhythm - "A short opening line on its own" is a rule in
        # the writing prompt, and collapsing it to prose deletes the thing the
        # prompt asked for.
        blocks.append(_row("<br />".join(html.escape(line) for line in lines)))
    return blocks


def _bullets(lines: list[str]) -> str:
    items = "".join(
        f'<li style="margin:0 0 8px;">{html.escape(line.lstrip("".join(_BULLET_PREFIXES)).strip())}</li>'
        for line in lines
    )
    return f'<ul style="margin:0;padding-left:22px;">{items}</ul>'


def _cta(label: str, style: BrandStyle, tier: EmailTier) -> str:
    """The one thing the email asks for.

    No href: the writer is told it does not know the URL behind any button,
    and inventing one sends a real reader to a page that does not exist. The
    user pastes their own link in - so the anchor is a marked, obvious slot
    rather than a dead link pretending to work.
    """
    text = html.escape(label.strip())
    if tier is EmailTier.PLAIN:
        # A styled text link, not a button: in a person-to-person email a
        # button is the tell that it came from a marketing tool.
        return _row(
            f'<a href="#" style="color:{style.accent};font-weight:600;'
            f'text-decoration:underline;">{text} &rarr;</a>',
            padding="8px 32px 24px",
        )
    return (
        f'<tr><td style="padding:8px 32px 32px;font-family:{_SANS};">'
        f'<table role="presentation" cellpadding="0" cellspacing="0" border="0">'
        f'<tr><td align="center" style="background-color:{style.accent};'
        f'border-radius:6px;">'
        f'<a href="#" style="display:inline-block;padding:14px 28px;'
        f'font-family:{_SANS};font-size:16px;font-weight:600;color:#ffffff;'
        f'text-decoration:none;">{text}</a>'
        "</td></tr></table></td></tr>\n"
    )


def _signoff(sign_off: str) -> str:
    return _row(html.escape(sign_off.strip()), padding="0 32px 24px")


def _postscript(postscript: str) -> str:
    text = postscript.strip()
    if not text.upper().startswith("P.S"):
        text = f"P.S. {text}"
    return (
        f'<tr><td style="padding:0 32px 32px;font-family:{_SANS};font-size:15px;'
        f'line-height:1.5;color:#5a6069;border-top:1px solid #e8eaed;'
        f'padding-top:20px;">{html.escape(text)}</td></tr>\n'
    )


def _header(style: BrandStyle) -> str:
    """The brand's mark, with the name as the fallback that always renders.

    Images are blocked by default in most clients on first open, so a header
    that is only a logo is a header that is usually blank. The alt text is the
    company name for exactly that reason.
    """
    if not style.logo_url and not style.name:
        return ""
    inner = html.escape(style.name)
    if style.logo_url:
        inner = (
            f'<img src="{html.escape(style.logo_url, quote=True)}" '
            f'alt="{html.escape(style.name, quote=True)}" height="32" '
            'style="display:block;border:0;height:32px;max-height:32px;width:auto;" />'
        )
    return (
        f'<tr><td style="padding:32px 32px 0;font-family:{_SANS};font-size:18px;'
        f'font-weight:700;color:#1f2328;">{inner}</td></tr>\n'
    )


def _footer(style: BrandStyle) -> str:
    lines = list(style.footer_lines) or ([style.name] if style.name else [])
    if not lines:
        return ""
    body = "<br />".join(html.escape(line) for line in lines)
    return (
        f'<tr><td style="padding:24px 32px 32px;font-family:{_SANS};font-size:13px;'
        f'line-height:1.5;color:#8a9099;border-top:1px solid #e8eaed;">{body}</td></tr>\n'
    )
