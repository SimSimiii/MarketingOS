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
 * own border - it drops the dashed outline and keeps the padding.
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
        "px-6 py-12 text-center",
        variant === "panel" && "rounded-xl border border-dashed border-border/80 bg-card/30",
        className,
      )}
    >
      {Icon && (
        <span className="mx-auto mb-4 flex size-11 items-center justify-center rounded-xl border border-violet-400/20 bg-violet-500/10 text-violet-300">
          <Icon className="size-5" aria-hidden="true" />
        </span>
      )}
      <h3 className="text-sm font-medium">{title}</h3>
      {description && (
        <p className="mx-auto mt-2 max-w-sm text-sm leading-relaxed text-muted-foreground">
          {description}
        </p>
      )}
      {action && <div className="mt-5 flex flex-wrap justify-center gap-2">{action}</div>}
    </div>
  );
}
