import type { ReactNode } from "react";
import { Search } from "lucide-react";

import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

/**
 * The strip above a list: a search field and the filters beside it.
 *
 * Campaigns, brands and activity each built this by hand, with the same
 * search icon placed three slightly different ways and three sets of filter
 * buttons that did not look like the same control. One strip, one control.
 */
export function Toolbar({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={cn("surface flex flex-wrap items-center gap-2.5 rounded-2xl p-2.5", className)}>
      {children}
    </div>
  );
}

export function SearchField({
  value,
  onChange,
  placeholder,
  label,
}: {
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
  label: string;
}) {
  return (
    <div className="relative min-w-48 flex-1">
      <Search
        className="pointer-events-none absolute top-1/2 left-3.5 size-4 -translate-y-1/2 text-muted-foreground"
        aria-hidden="true"
      />
      <Input
        type="search"
        aria-label={label}
        placeholder={placeholder}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="h-10 rounded-xl pl-10"
      />
    </div>
  );
}

/** A row of mutually exclusive filters, each with how many rows it keeps. */
export function FilterPills<T extends string>({
  options,
  value,
  onChange,
  label,
}: {
  options: { value: T; label: string; count?: number }[];
  value: T;
  onChange: (value: T) => void;
  label: string;
}) {
  return (
    <div
      role="group"
      aria-label={label}
      className="flex flex-wrap gap-1 rounded-xl bg-black/25 p-1 shadow-[inset_0_1px_2px_0_oklch(0_0_0/30%)] ring-1 ring-white/[0.06]"
    >
      {options.map((option) => {
        const active = option.value === value;
        return (
          <button
            key={option.value}
            type="button"
            aria-pressed={active}
            onClick={() => onChange(option.value)}
            className={cn(
              "inline-flex h-8 cursor-pointer items-center gap-2 rounded-lg px-3 text-[0.8125rem] font-medium whitespace-nowrap transition-all focus-visible:ring-3 focus-visible:ring-ring/45 focus-visible:outline-none",
              active
                ? "bg-white/[0.09] text-foreground shadow-[inset_0_1px_0_0_oklch(1_0_0/8%),0_2px_8px_-2px_oklch(0_0_0/50%)]"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            {option.label}
            {option.count !== undefined && (
              <span
                className={cn(
                  "rounded-full px-1.5 py-px text-[0.6875rem] tabular-nums",
                  active ? "bg-violet-500/25 text-violet-100" : "bg-white/[0.06] text-muted-foreground",
                )}
              >
                {option.count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
