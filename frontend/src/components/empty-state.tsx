import type { ComponentType, ReactNode } from "react";

import { cn } from "@/lib/utils";

/**
 * What a list looks like before it has anything in it.
 *
 * Every one of these in the app said something different in a different shape:
 * a bare grey sentence on one page, a centred illustration with a call to
 * action on the next. Emptiness is the first state a new account sees on most
 * of these pages, so it is worth treating as a designed one.
 *
 * `variant="inline"` is for an empty state already inside a card that has its
 * own surface - it drops the panel and keeps the padding.
 */
export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  variant = "panel",
  className,
}: {
  icon?: ComponentType<{ className?: string }>;
  title: string;
  description?: ReactNode;
  action?: ReactNode;
  variant?: "panel" | "inline";
  className?: string;
}) {
  return (
    <div
      className={cn(
        "relative isolate overflow-hidden px-6 py-14 text-center",
        variant === "panel" && "surface rounded-2xl",
        className,
      )}
    >
      <span
        aria-hidden="true"
        className="pointer-events-none absolute inset-x-0 top-0 -z-10 h-48 bg-[radial-gradient(ellipse_50%_100%_at_50%_0%,oklch(0.55_0.2_293/14%),transparent_70%)]"
      />
      {Icon && (
        <span className="relative mx-auto mb-6 flex size-14 items-center justify-center">
          {/* Two faint rings round the mark, the way a sonar draws an echo:
              the page is listening for the first thing to arrive. */}
          <span
            aria-hidden="true"
            className="absolute -inset-4 rounded-[1.6rem] border border-white/[0.04]"
          />
          <span
            aria-hidden="true"
            className="absolute -inset-2 rounded-[1.3rem] border border-white/[0.06]"
          />
          <span className="icon-tile relative flex size-14 items-center justify-center rounded-2xl shadow-[0_8px_30px_-8px_oklch(0.6_0.22_293/50%)]">
            <Icon className="size-6" aria-hidden="true" />
          </span>
        </span>
      )}
      <h3 className="text-base font-semibold tracking-tight">{title}</h3>
      {description && (
        <p className="mx-auto mt-2 max-w-md text-sm leading-relaxed text-muted-foreground">
          {description}
        </p>
      )}
      {action && <div className="mt-6 flex flex-wrap justify-center gap-2">{action}</div>}
    </div>
  );
}
