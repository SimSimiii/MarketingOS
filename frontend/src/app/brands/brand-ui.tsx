import type { ReactNode } from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

export function BrandSectionHeader({ title, description, actions }: { title: string; description: string; actions?: ReactNode }) {
  return <header className="flex flex-wrap items-end justify-between gap-4">
    <div className="min-w-0 max-w-2xl"><h2 className="font-display text-[1.875rem] leading-tight tracking-[-0.005em]">{title}</h2><p className="mt-1 text-sm leading-relaxed text-muted-foreground">{description}</p></div>
    {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
  </header>;
}

export function BrandDisclosure({ title, description, children, className }: { title: string; description?: string; children: ReactNode; className?: string }) {
  return <details className={cn("group/disclosure surface min-w-0 rounded-2xl transition-shadow open:shadow-[var(--shadow-surface),0_0_0_1px_oklch(0.7_0.16_293/28%)]", className)}>
    <summary className="flex min-h-16 cursor-pointer list-none items-center justify-between gap-4 rounded-2xl p-4 transition-colors hover:bg-white/[0.025] focus-visible:outline-2 focus-visible:outline-ring [&::-webkit-details-marker]:hidden">
      <span className="min-w-0"><span className="block text-sm font-semibold tracking-tight">{title}</span>{description && <span className="mt-1 block text-xs leading-relaxed text-muted-foreground">{description}</span>}</span>
      <span className="flex size-7 shrink-0 items-center justify-center rounded-full border border-white/[0.08] bg-white/[0.03] text-muted-foreground transition-colors group-open/disclosure:border-violet-400/30 group-open/disclosure:text-violet-300"><ChevronDown className="size-3.5 transition-transform duration-200 group-open/disclosure:rotate-180" aria-hidden="true" /></span>
    </summary>
    <div className="border-t border-hairline p-4">{children}</div>
  </details>;
}
