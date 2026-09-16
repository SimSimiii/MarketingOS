import type { ComponentType, ReactNode } from "react";
import Link from "next/link";

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
  const body = (
    <>
      <div className="flex items-start justify-between gap-3">
        <p className="text-xs font-medium text-muted-foreground">{label}</p>
        {Icon && (
          <Icon
            className={cn(
              "size-4 shrink-0 transition-colors",
              tone === "attention" ? "text-amber-300" : "text-muted-foreground",
              href && "group-hover/stat:text-violet-300",
            )}
          />
        )}
      </div>
      <p
        className={cn(
          "mt-3 text-3xl font-semibold tracking-tight tabular-nums",
          tone === "attention" && "text-amber-200",
        )}
      >
        {value}
      </p>
      {hint && (
        <p
          className={cn(
            "mt-2 text-xs leading-relaxed text-muted-foreground",
            href && "transition-colors group-hover/stat:text-violet-300",
          )}
        >
          {hint}
          {href && <span aria-hidden="true"> →</span>}
        </p>
      )}
    </>
  );

  const shell = cn(
    "rounded-xl border p-4 sm:p-5",
    tone === "attention"
      ? "border-amber-400/25 bg-amber-400/5"
      : "border-border bg-card",
    className,
  );

  if (!href) {
    return <div className={shell}>{body}</div>;
  }

  return (
    <Link
      href={href}
      className={cn(
        shell,
        "group/stat block transition-colors hover:border-violet-400/40 hover:bg-accent/20",
      )}
    >
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
      <p className="mt-0.5 text-xs text-muted-foreground">{label}</p>
      {hint && <p className="mt-0.5 text-xs text-muted-foreground/70">{hint}</p>}
    </div>
  );
}
