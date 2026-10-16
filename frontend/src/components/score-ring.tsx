import { cn } from "@/lib/utils";

/**
 * A score out of ten as an arc, with the number in the middle.
 *
 * The number is the fact; the arc is there so a 4 and an 8 look different
 * before either is read. Colour follows the same bands the copy uses - below
 * five is a draft that did not land, seven and up is one that did.
 */
export function ScoreRing({
  value,
  max = 10,
  size = 88,
  label,
  className,
}: {
  value: number;
  max?: number;
  size?: number;
  /** What the number is, for a screen reader. */
  label: string;
  className?: string;
}) {
  const stroke = 7;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const share = Math.max(0, Math.min(1, value / max));
  const band = value >= 7 ? "good" : value >= 5 ? "fair" : "low";
  const gradientId = `score-${band}`;

  return (
    <div
      className={cn("relative shrink-0", className)}
      style={{ width: size, height: size }}
      role="img"
      aria-label={`${label}: ${value.toFixed(1)} out of ${max}`}
    >
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="-rotate-90">
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="1" y2="1">
            {band === "good" ? (
              <>
                <stop offset="0%" stopColor="oklch(0.85 0.15 165)" />
                <stop offset="100%" stopColor="oklch(0.7 0.19 293)" />
              </>
            ) : band === "fair" ? (
              <>
                <stop offset="0%" stopColor="oklch(0.85 0.15 85)" />
                <stop offset="100%" stopColor="oklch(0.7 0.19 293)" />
              </>
            ) : (
              <>
                <stop offset="0%" stopColor="oklch(0.75 0.17 30)" />
                <stop offset="100%" stopColor="oklch(0.7 0.16 350)" />
              </>
            )}
          </linearGradient>
        </defs>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="oklch(1 0 0 / 8%)"
          strokeWidth={stroke}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={`url(#${gradientId})`}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference * (1 - share)}
          className="transition-[stroke-dashoffset] duration-700 ease-out"
        />
      </svg>
      <span className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-[1.375rem] leading-none font-semibold tracking-tight tabular-nums">
          {value.toFixed(1)}
        </span>
        <span className="mt-0.5 text-[0.625rem] text-muted-foreground">/ {max}</span>
      </span>
    </div>
  );
}
