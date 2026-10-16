import type { ReactNode } from "react";
import { AlertTriangle, CheckCircle2, Info, XCircle } from "lucide-react";

import { cn } from "@/lib/utils";

type Tone = "info" | "warning" | "success" | "danger";

/**
 * The inline banner that says something is wrong, stale, or worth knowing.
 *
 * There were seven of these written by hand, each picking its own amber:
 * `border-amber-400/20 bg-amber-400/5 text-amber-200` in one place,
 * `border-amber-500/50 bg-amber-500/5` in another, and a third with no border
 * at all. A warning that looks slightly different every time it appears stops
 * being read as a warning.
 *
 * `role="status"` rather than `alert` for everything but `danger`: an alert
 * interrupts a screen reader mid-sentence, which is right for a failure and
 * wrong for "this data is a minute old".
 */
export function Notice({
  tone = "info",
  title,
  children,
  icon = true,
  className,
}: {
  tone?: Tone;
  title?: ReactNode;
  children?: ReactNode;
  icon?: boolean;
  className?: string;
}) {
  const Icon = TONE_ICON[tone];
  const style = TONE_STYLE[tone];
  return (
    <div
      role={tone === "danger" ? "alert" : "status"}
      className={cn(
        "relative flex items-start gap-3.5 overflow-hidden rounded-xl border py-4 pr-4 pl-5 text-sm",
        style.shell,
        className,
      )}
    >
      {/* The edge carries the tone, so a glance down a page of notices finds
          the amber one without reading any of them. */}
      <span aria-hidden="true" className={cn("absolute inset-y-0 left-0 w-[3px]", style.edge)} />
      {icon && (
        <span className={cn("mt-px flex size-6 shrink-0 items-center justify-center rounded-md", style.icon)}>
          <Icon className="size-3.5" aria-hidden="true" />
        </span>
      )}
      <div className="min-w-0 flex-1 space-y-1">
        {title && <p className={cn("font-medium", style.title)}>{title}</p>}
        {children && <div className="leading-relaxed [&_p+p]:mt-1">{children}</div>}
      </div>
    </div>
  );
}

const TONE_STYLE: Record<Tone, { shell: string; edge: string; icon: string; title: string }> = {
  info: {
    shell: "border-white/[0.08] bg-white/[0.03] text-muted-foreground",
    edge: "bg-gradient-to-b from-violet-400 to-violet-500/40",
    icon: "bg-violet-500/15 text-violet-300",
    title: "text-foreground",
  },
  warning: {
    shell: "border-amber-400/20 bg-amber-400/[0.05] text-amber-100/80",
    edge: "bg-gradient-to-b from-amber-300 to-amber-500/40",
    icon: "bg-amber-400/15 text-amber-300",
    title: "text-amber-100",
  },
  success: {
    shell: "border-emerald-400/20 bg-emerald-400/[0.05] text-emerald-100/80",
    edge: "bg-gradient-to-b from-emerald-300 to-emerald-500/40",
    icon: "bg-emerald-400/15 text-emerald-300",
    title: "text-emerald-100",
  },
  danger: {
    shell: "border-red-400/25 bg-red-500/[0.07] text-red-100/85",
    edge: "bg-gradient-to-b from-red-400 to-red-500/40",
    icon: "bg-red-500/15 text-red-300",
    title: "text-red-100",
  },
};

const TONE_ICON: Record<Tone, typeof Info> = {
  info: Info,
  warning: AlertTriangle,
  success: CheckCircle2,
  danger: XCircle,
};
