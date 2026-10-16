import type { ComponentType, ReactNode } from "react";
import Link from "next/link";
import { ArrowUpRight } from "lucide-react";

import { cn } from "@/lib/utils";

/**
 * A single number and what it counts.
 *
 * There were five of these in the app - `Stat`, `Figure`, and three inline
 * grids - at three different type scales, so the same count looked like a
 * different kind of fact depending on which page you read it on. One
 * component, one scale.
 *
 * `href` makes the whole tile the link rather than adding one inside it: a
 * number the reader can act on should have a target the size of the number.
 */
export function StatTile({
  label,
  value,
  hint,
  href,
  icon: Icon,
  tone = "default",
  className,
}: {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  href?: string;
  icon?: ComponentType<{ className?: string }>;
  /** `attention` for a count the reader is meant to go and clear. */
  tone?: "default" | "attention";
  className?: string;
}) {
  const attention = tone === "attention";
  const body = (
    <>
      {/* The lit corner. Brighter on hover for a tile that goes somewhere. */}
      <span
        aria-hidden="true"
        className={cn(
          "pointer-events-none absolute -top-16 -right-16 size-44 rounded-full blur-3xl transition-opacity duration-300",
          attention ? "bg-amber-400/15 opacity-70" : "bg-violet-500/15 opacity-50",
          href && "group-hover/stat:opacity-100",
        )}
      />
      <div className="relative flex items-start justify-between gap-3">
        <p className="min-w-0 pt-1 text-xs font-medium text-muted-foreground sm:text-[0.8125rem]">{label}</p>
        {Icon && (
          <span
            className={cn(
              "flex size-7 shrink-0 items-center justify-center rounded-lg sm:size-8",
              attention
                ? "bg-amber-400/10 text-amber-300 ring-1 ring-amber-400/25"
                : "icon-tile",
            )}
          >
            <Icon className="size-4" aria-hidden="true" />
          </span>
        )}
      </div>
      <p
        className={cn(
          "relative mt-3 text-[1.75rem] leading-none font-semibold tracking-tight tabular-nums sm:mt-4 sm:text-[2.125rem]",
          attention ? "text-amber-100" : "text-gradient",
        )}
      >
        {value}
      </p>
      {hint && (
        <p
          className={cn(
            "relative mt-2.5 flex items-center gap-1 text-[0.6875rem] leading-relaxed text-muted-foreground sm:mt-3 sm:text-xs",
            href && "transition-colors group-hover/stat:text-violet-200",
          )}
        >
          <span className="min-w-0">{hint}</span>
          {href && (
            <ArrowUpRight
              className="size-3.5 shrink-0 opacity-0 transition-all duration-200 group-hover/stat:translate-x-0.5 group-hover/stat:opacity-100"
              aria-hidden="true"
            />
          )}
        </p>
      )}
    </>
  );

  const shell = cn(
    "relative isolate block overflow-hidden rounded-2xl p-4 sm:p-5",
    attention
      ? "bg-card bg-[linear-gradient(180deg,oklch(0.8_0.15_80/7%),transparent_60%)] shadow-[var(--shadow-surface),0_0_0_1px_oklch(0.8_0.15_80/22%)]"
      : "surface",
    className,
  );

  if (!href) {
    return <div className={shell}>{body}</div>;
  }

  return (
    <Link href={href} className={cn(shell, "group/stat surface-interactive")}>
      {body}
    </Link>
  );
}

/**
 * The compact form, for a row of figures already inside a card. Same idea,
 * without the surface - a tile inside a tile is a box the reader has to parse
 * before they can read the number.
 */
export function StatFigure({
  label,
  value,
  hint,
}: {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
}) {
  return (
    <div className="min-w-0">
      <p className="text-xl font-semibold tracking-tight tabular-nums">{value}</p>
      <p className="mt-1 text-xs text-muted-foreground">{label}</p>
      {hint && <p className="mt-0.5 text-[0.6875rem] text-muted-foreground/70">{hint}</p>}
    </div>
  );
}
