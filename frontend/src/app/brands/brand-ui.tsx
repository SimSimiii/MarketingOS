import type { ReactNode } from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

export function BrandSectionHeader({ title, description, actions }: { title: string; description: string; actions?: ReactNode }) {
  return <header className="flex flex-wrap items-start justify-between gap-4">
    <div className="min-w-0 max-w-2xl"><h2 className="text-xl font-semibold tracking-tight">{title}</h2><p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{description}</p></div>
    {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
  </header>;
}

export function BrandDisclosure({ title, description, children, className }: { title: string; description?: string; children: ReactNode; className?: string }) {
  return <details className={cn("group/disclosure min-w-0 rounded-xl border border-border bg-card transition-colors open:border-violet-400/25 hover:border-violet-400/30", className)}>
    <summary className="flex min-h-16 cursor-pointer list-none items-center justify-between gap-4 rounded-xl p-4 transition-colors hover:bg-accent/20 focus-visible:outline-2 focus-visible:outline-ring [&::-webkit-details-marker]:hidden">
      <span className="min-w-0"><span className="block text-sm font-medium">{title}</span>{description && <span className="mt-1 block text-xs leading-relaxed text-muted-foreground">{description}</span>}</span>
      <ChevronDown className="size-4 shrink-0 text-muted-foreground transition-transform group-open/disclosure:rotate-180 group-open/disclosure:text-violet-300" aria-hidden="true" />
    </summary>
    <div className="border-t border-hairline p-4">{children}</div>
  </details>;
}
