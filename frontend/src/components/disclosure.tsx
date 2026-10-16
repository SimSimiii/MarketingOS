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
        "group/disclosure surface rounded-2xl",
        tone === "attention" && "shadow-[var(--shadow-surface),0_0_0_1px_oklch(0.8_0.15_80/25%)]",
        className,
      )}
    >
      <summary className="flex cursor-pointer list-none items-center gap-3 rounded-2xl p-4 transition-colors hover:bg-white/[0.025] focus-visible:outline-2 focus-visible:outline-ring sm:px-5 [&::-webkit-details-marker]:hidden">
        <span className="min-w-0 flex-1">
          <span className="block text-sm font-semibold tracking-tight">{title}</span>
          {summary && (
            <span className="mt-0.5 block text-xs leading-relaxed text-muted-foreground">
              {summary}
            </span>
          )}
        </span>
        {badge}
        <span className="flex size-7 shrink-0 items-center justify-center rounded-full border border-white/[0.08] bg-white/[0.03] text-muted-foreground transition-colors group-hover/disclosure:text-foreground group-open/disclosure:border-violet-400/30 group-open/disclosure:text-violet-300">
          <ChevronDown
            className="size-3.5 transition-transform duration-200 group-open/disclosure:rotate-180"
            aria-hidden="true"
          />
        </span>
      </summary>
      <div className="border-t border-hairline p-4 sm:p-5">{children}</div>
    </details>
  );
}
