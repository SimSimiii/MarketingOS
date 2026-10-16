import { cn } from "@/lib/utils";
import type { ExecutionStatus, LogLevel } from "@/lib/types";

/** A pill with a dot. The dot carries the colour, so the badge still reads in
 * a row of six; the running one breathes, so a live run is found without
 * reading the word. */
const STATUS_STYLES: Record<ExecutionStatus, { pill: string; dot: string }> = {
  pending: { pill: "bg-white/[0.06] text-muted-foreground ring-white/10", dot: "bg-muted-foreground" },
  running: { pill: "bg-violet-500/15 text-violet-200 ring-violet-400/30", dot: "live-dot !size-1.5" },
  completed: { pill: "bg-emerald-400/10 text-emerald-300 ring-emerald-400/20", dot: "bg-emerald-400 shadow-[0_0_6px_oklch(0.8_0.17_160/70%)]" },
  failed: { pill: "bg-red-500/10 text-red-300 ring-red-400/25", dot: "bg-red-400" },
  cancelled: { pill: "bg-amber-400/10 text-amber-300 ring-amber-400/25", dot: "bg-amber-400" },
};

const PILL =
  "inline-flex h-[1.375rem] w-fit shrink-0 items-center gap-1.5 rounded-full px-2.5 text-[0.6875rem] font-medium whitespace-nowrap ring-1 ring-inset";

export function StatusBadge({ status, warning, label }: { status: ExecutionStatus; warning?: boolean; label?: string }) {
  const style = warning ? STATUS_STYLES.cancelled : STATUS_STYLES[status];
  return (
    <span className={cn(PILL, "capitalize", style.pill)}>
      <span className={cn("size-1.5 shrink-0 rounded-full", style.dot)} aria-hidden="true" />
      {label ?? (warning ? "Needs review" : status)}
    </span>
  );
}

const LOG_LEVEL_STYLES: Record<LogLevel, string> = {
  debug: "bg-white/[0.05] text-muted-foreground ring-white/10",
  info: "bg-violet-500/12 text-violet-200 ring-violet-400/25",
  warning: "bg-amber-400/10 text-amber-300 ring-amber-400/25",
  error: "bg-red-500/10 text-red-300 ring-red-400/25",
};

export function LogLevelBadge({ level }: { level: LogLevel }) {
  return (
    <span className={cn(PILL, "px-2 text-[0.625rem] tracking-wider uppercase", LOG_LEVEL_STYLES[level])}>
      {level}
    </span>
  );
}
