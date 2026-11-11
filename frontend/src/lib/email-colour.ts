/** The email renderer's colour rules, for the appearance preview.
 *
 * Mirrors backend/app/core/colour.py and `BrandStyle` in
 * backend/app/marketing/render_html.py. The preview exists so a colour is
 * seen on a button before it is sent, and a pale brand colour is not drawn
 * as typed: its text is darkened until it reads on white and the button
 * label turns dark. A preview that showed the raw colour would show an email
 * nobody receives. */

export const DEFAULT_ACCENT = "#1a56db";
const WHITE = "#ffffff";
const LABEL_INK = "#14161a";
/** Body-size text against its background (WCAG AA). */
const MIN_TEXT_CONTRAST = 4.5;
/** Below this a colour does not show on the white card at all. */
const MIN_SURFACE_CONTRAST = 1.3;

export interface EmailColours {
  /** Links, the eyebrow, the hero figure: readable on white. */
  accent: string;
  /** The button and the rule across the top: the brand colour as given. */
  fill: string;
  /** The button label. */
  onFill: string;
}

export function emailColours(value: string): EmailColours {
  const colour = parseHex(value) ?? DEFAULT_ACCENT;
  const accent = darkenTo(colour, MIN_TEXT_CONTRAST);
  const fill = contrast(colour, WHITE) < MIN_SURFACE_CONTRAST ? accent : colour;
  const onFill = contrast(fill, WHITE) >= contrast(fill, LABEL_INK) ? WHITE : LABEL_INK;
  return { accent, fill, onFill };
}

/** `#rrggbb` in lower case, or null for anything else. */
export function parseHex(value: string): string | null {
  const match = /^#([0-9a-f]{3}|[0-9a-f]{6})$/i.exec(value.trim());
  if (!match) return null;
  const digits = match[1].length === 3 ? [...match[1]].map((c) => c + c).join("") : match[1];
  return `#${digits.toLowerCase()}`;
}

export function contrast(first: string, second: string): number {
  const [lighter, darker] = [luminance(first), luminance(second)].sort((a, b) => b - a);
  return (lighter + 0.05) / (darker + 0.05);
}

/** The same hue, darkened only as far as it takes to reach `ratio` on white. */
export function darkenTo(colour: string, ratio: number): string {
  if (contrast(colour, WHITE) >= ratio) return colour;
  const [hue, start, saturation] = rgbToHls(channels(colour));
  for (let lightness = start - 0.01; lightness > 0; lightness -= 0.01) {
    const candidate = toHex(hlsToRgb(hue, lightness, saturation));
    if (contrast(candidate, WHITE) >= ratio) return candidate;
  }
  return "#000000";
}

type Rgb = [number, number, number];

function channels(colour: string): Rgb {
  return [1, 3, 5].map((index) => parseInt(colour.slice(index, index + 2), 16) / 255) as Rgb;
}

function toHex(rgb: Rgb): string {
  return `#${rgb.map((c) => Math.round(c * 255).toString(16).padStart(2, "0")).join("")}`;
}

function luminance(colour: string): number {
  const [r, g, b] = channels(colour).map((c) =>
    c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4,
  );
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

// Python's colorsys, so both ends darken a colour to the same place.
function rgbToHls([r, g, b]: Rgb): Rgb {
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const lightness = (max + min) / 2;
  if (max === min) return [0, lightness, 0];
  const range = max - min;
  const saturation = lightness <= 0.5 ? range / (max + min) : range / (2 - max - min);
  const [rc, gc, bc] = [(max - r) / range, (max - g) / range, (max - b) / range];
  const hue = r === max ? bc - gc : g === max ? 2 + rc - bc : 4 + gc - rc;
  return [(((hue / 6) % 1) + 1) % 1, lightness, saturation];
}

function hlsToRgb(hue: number, lightness: number, saturation: number): Rgb {
  if (saturation === 0) return [lightness, lightness, lightness];
  const m2 =
    lightness <= 0.5 ? lightness * (1 + saturation) : lightness + saturation - lightness * saturation;
  const m1 = 2 * lightness - m2;
  const v = (h: number) => {
    const t = ((h % 1) + 1) % 1;
    if (t < 1 / 6) return m1 + (m2 - m1) * t * 6;
    if (t < 0.5) return m2;
    if (t < 2 / 3) return m1 + (m2 - m1) * (2 / 3 - t) * 6;
    return m1;
  };
  return [v(hue + 1 / 3), v(hue), v(hue - 1 / 3)];
}
