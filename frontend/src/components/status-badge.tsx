import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { ExecutionStatus, LogLevel } from "@/lib/types";

const STATUS_STYLES: Record<ExecutionStatus, string> = {
  pending: "bg-muted text-muted-foreground",
  running: "bg-primary/20 text-primary",
  completed: "bg-emerald-500/15 text-emerald-400",
  failed: "bg-destructive/15 text-destructive",
  cancelled: "bg-amber-500/15 text-amber-400",
};

export function StatusBadge({ status, warning, label }: { status: ExecutionStatus; warning?: boolean; label?: string }) {
  return (
    <Badge variant="outline" className={cn("border-transparent capitalize", warning ? STATUS_STYLES.cancelled : STATUS_STYLES[status])}>
      {label ?? (warning ? "Needs review" : status)}
    </Badge>
  );
}

const LOG_LEVEL_STYLES: Record<LogLevel, string> = {
  debug: "bg-muted text-muted-foreground",
  info: "bg-primary/20 text-primary",
  warning: "bg-amber-500/15 text-amber-400",
  error: "bg-destructive/15 text-destructive",
};

export function LogLevelBadge({ level }: { level: LogLevel }) {
  return (
    <Badge variant="outline" className={cn("border-transparent uppercase", LOG_LEVEL_STYLES[level])}>
      {level}
    </Badge>
  );
}
