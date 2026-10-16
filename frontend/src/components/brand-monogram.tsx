import { cn } from "@/lib/utils";

/** The same name always lands on the same hue, so a brand keeps its colour
 * across the directory, its header and the switcher without storing one. */
function hueFor(name: string): number {
  let hash = 0;
  for (const char of name) hash = (hash * 31 + char.charCodeAt(0)) >>> 0;
  // Kept inside the cool half of the wheel - violets, blues, teals, roses -
  // so no brand's tile argues with the accent or reads as a warning.
  const hues = [293, 265, 245, 220, 190, 330, 310, 275];
  return hues[hash % hues.length];
}

/** "iFixit — pilot validation" -> "IF"; "National Trust" -> "NT". */
function lettersFor(name: string): string {
  const words = name
    .replace(/[—–-].*$/, "")
    .split(/\s+/)
    .map((word) => word.replace(/[^\p{L}\p{N}]/gu, ""))
    .filter(Boolean);
  if (words.length === 0) return "?";
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
  return `${words[0][0]}${words[1][0]}`.toUpperCase();
}

/**
 * A brand's mark: its initials on a tile of its own colour.
 *
 * Every brand used to wear the same building icon, so a directory of seven
 * businesses was seven identical glyphs and the name was the only thing to
 * tell them apart. A monogram is recognisable before it is read.
 */
export function BrandMonogram({
  name,
  size = "md",
  className,
}: {
  name: string;
  size?: "sm" | "md" | "lg";
  className?: string;
}) {
  const hue = hueFor(name);
  return (
    <span
      aria-hidden="true"
      className={cn(
        "flex shrink-0 items-center justify-center font-semibold tracking-tight text-white",
        size === "sm" && "size-7 rounded-lg text-[0.625rem]",
        size === "md" && "size-11 rounded-xl text-sm",
        size === "lg" && "size-16 rounded-2xl text-xl",
        className,
      )}
      style={{
        background: `radial-gradient(120% 120% at 30% 0%, oklch(0.82 0.11 ${hue} / 85%), transparent 55%), linear-gradient(145deg, oklch(0.6 0.19 ${hue}), oklch(0.45 0.17 ${hue - 12}))`,
        boxShadow: `inset 0 1px 0 0 oklch(1 0 0 / 30%), inset 0 -1px 0 0 oklch(0 0 0 / 25%), 0 0 0 1px oklch(0.55 0.17 ${hue} / 55%), 0 10px 28px -10px oklch(0.55 0.2 ${hue} / 70%)`,
      }}
    >
      {lettersFor(name)}
    </span>
  );
}
