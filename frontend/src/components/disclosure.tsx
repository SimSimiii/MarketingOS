import type { ReactNode } from "react";
import { ChevronDown } from "lucide-react";

import { cn } from "@/lib/utils";

/**
 * A titled panel the reader opens when they want the detail.
 *
 * Native `<details>` rather than state: it opens with the keyboard, is
 * announced as expandable, survives a re-render without a hook, and the
 * browser's find-in-page opens it when a match is inside.
 */
export function Disclosure({
  title,
  summary,
  badge,
  defaultOpen = false,
  tone = "default",
  className,
  children,
}: {
  title: ReactNode;
  /** One line under the title saying what is inside, so the reader can tell
   * whether to open it without opening it. */
  summary?: ReactNode;
  badge?: ReactNode;
  defaultOpen?: boolean;
  tone?: "default" | "attention";
  className?: string;
  children: ReactNode;
}) {
  return (
    <details
      open={defaultOpen}
      className={cn(
        "group/disclosure rounded-xl border bg-card",
        tone === "attention" ? "border-amber-400/25" : "border-border",
        className,
      )}
    >
      <summary className="flex cursor-pointer list-none items-center gap-3 rounded-xl p-4 transition-colors hover:bg-accent/15 focus-visible:outline-2 focus-visible:outline-ring sm:px-5 [&::-webkit-details-marker]:hidden">
        <span className="min-w-0 flex-1">
          <span className="block text-sm font-medium">{title}</span>
          {summary && (
            <span className="mt-0.5 block text-xs leading-relaxed text-muted-foreground">
              {summary}
            </span>
          )}
        </span>
        {badge}
        <ChevronDown
          className="size-4 shrink-0 text-muted-foreground transition-transform group-open/disclosure:rotate-180"
          aria-hidden="true"
        />
      </summary>
      <div className="border-t border-hairline p-4 sm:p-5">{children}</div>
    </details>
  );
}
