"""Colour as a reader sees it: parsed, compared, and made legible.

A brand colour arrives from two places nobody controls - a form a person
typed a hex into, and a site's `theme-color` - and lands in an email where
it has to work on white. Some do not. A pale yellow is a fine button and an
unreadable link; a cream `theme-color` is the colour of a browser's toolbar,
not of a company. These are the few functions that tell the two apart, kept
here so the renderer that uses a colour and the reader that collects one
draw the line in the same place.

Contrast is WCAG's: relative luminance, ratio from 1 (no difference) to 21
(black on white).
"""

import colorsys
import re

WHITE = "#ffffff"

#: The ratio body-size text needs against its background (WCAG AA). Links,
#: the eyebrow and the button's own label are all set at body size or below.
MIN_TEXT_CONTRAST = 4.5
#: Below this a colour does not show on a white card at all: a surface in it
#: is a button nobody can see, and a site that declares it has described its
#: browser toolbar rather than its brand.
MIN_SURFACE_CONTRAST = 1.3

_HEX_RE = re.compile(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})")
_RGB_RE = re.compile(
    r"rgba?\(\s*(\d{1,3})[\s,]+(\d{1,3})[\s,]+(\d{1,3})(?:\s*[,/]\s*([\d.]+%?))?\s*\)",
    re.IGNORECASE,
)


def parse_colour(value: str) -> str:
    """`#rrggbb` in lower case, or "" for anything that is not a colour.

    Accepts the spellings sites actually use - `#abc`, `#aabbcc`,
    `rgb(250, 247, 240)`, `rgb(250 247 240 / 1)` - and refuses a transparent
    one, which is no colour at all.
    """
    text = value.strip()
    if match := _HEX_RE.fullmatch(text):
        digits = match.group(1)
        if len(digits) == 3:
            digits = "".join(character * 2 for character in digits)
        return f"#{digits.lower()}"
    if match := _RGB_RE.fullmatch(text):
        channels = [int(group) for group in match.groups()[:3]]
        alpha = match.group(4)
        if alpha is not None:
            opacity = float(alpha.rstrip("%")) / (100 if alpha.endswith("%") else 1)
            if opacity <= 0:
                return ""
        if all(channel <= 255 for channel in channels):
            return "#" + "".join(f"{channel:02x}" for channel in channels)
    return ""


def contrast(first: str, second: str) -> float:
    """WCAG contrast ratio between two `#rrggbb` colours."""
    lighter, darker = sorted((_luminance(first), _luminance(second)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def darken_to(colour: str, ratio: float, against: str = WHITE) -> str:
    """The same hue, darkened only as far as it takes to reach `ratio`.

    Hue and saturation are kept, so a pale brand orange becomes a deeper
    orange rather than a brown or a grey - still recognisably theirs, now
    readable. A colour that already reaches the ratio comes back unchanged.
    """
    if contrast(colour, against) >= ratio:
        return colour
    hue, lightness, saturation = colorsys.rgb_to_hls(*_channels(colour))
    while lightness > 0:
        lightness = max(0.0, lightness - 0.01)
        candidate = _hex(colorsys.hls_to_rgb(hue, lightness, saturation))
        if contrast(candidate, against) >= ratio:
            return candidate
    return "#000000"


def _channels(colour: str) -> tuple[float, float, float]:
    return tuple(int(colour[index : index + 2], 16) / 255 for index in (1, 3, 5))  # type: ignore[return-value]


def _hex(channels: tuple[float, float, float]) -> str:
    return "#" + "".join(f"{round(channel * 255):02x}" for channel in channels)


def _luminance(colour: str) -> float:
    def linear(channel: float) -> float:
        return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4

    red, green, blue = (linear(channel) for channel in _channels(colour))
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue
