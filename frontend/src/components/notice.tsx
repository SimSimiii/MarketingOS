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
  return (
    <div
      role={tone === "danger" ? "alert" : "status"}
      className={cn(
        "flex items-start gap-3 rounded-xl border p-4 text-sm",
        TONE_STYLE[tone],
        className,
      )}
    >
      {icon && <Icon className="mt-0.5 size-4 shrink-0" aria-hidden="true" />}
      <div className="min-w-0 flex-1 space-y-1">
        {title && <p className="font-medium">{title}</p>}
        {children && <div className="leading-relaxed [&_p+p]:mt-1">{children}</div>}
      </div>
    </div>
  );
}

const TONE_STYLE: Record<Tone, string> = {
  info: "border-border bg-muted/40 text-muted-foreground",
  warning: "border-amber-400/25 bg-amber-400/5 text-amber-200",
  success: "border-emerald-400/25 bg-emerald-400/5 text-emerald-200",
  danger: "border-destructive/40 bg-destructive/10 text-destructive",
};

const TONE_ICON: Record<Tone, typeof Info> = {
  info: Info,
  warning: AlertTriangle,
  success: CheckCircle2,
  danger: XCircle,
};
