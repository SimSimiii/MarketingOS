"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { ScrollText, SearchX } from "lucide-react";

import { EmptyState } from "@/components/empty-state";
import { ExpandableText } from "@/components/expandable-text";
import { PageHeader } from "@/components/page-header";
import { LogLevelBadge } from "@/components/status-badge";
import { FilterPills, SearchField, Toolbar } from "@/components/toolbar";
import { Card, CardContent } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { api } from "@/lib/api-client";
import { formatAbsolute, formatTime } from "@/lib/format";
import { PageData, usePageData } from "@/lib/page-data";
import { activityLabel, activityMessage } from "@/lib/product-progress";
import type { ExecutionLog, LogLevel } from "@/lib/types";
import { cn } from "@/lib/utils";

/** Optionally scoped to one run (`?execution=<id>`, how the live view links
 * here) and one specialist (`&agent=<agent_id>`), because "show me
 * everything that ever happened" stops being useful after the first
 * campaign. */
export function LogsView() {
  const search = useSearchParams();
  const execution = search.get("execution") ?? undefined;
  const agent = search.get("agent") ?? undefined;
  const state = usePageData(async () => {
    const logs: ExecutionLog[] = execution
      ? await api
          .getExecutionLogs(execution, { agentId: agent, includeDebug: true })
      : await api.listLogs(200);
    return { logs: logs.flatMap((log) => {
      const message = activityMessage(log);
      return message === null ? [] : [{ ...log, message }];
    }) };
  }, [execution, agent]);

  return (
    <PageData state={state}>
      {({ logs }) => (
        <div className="space-y-6">
          <PageHeader
            eyebrow={execution ? "One run" : "Across all runs"}
            title="Activity"
            description={
              execution
                ? `Progress and feedback for this run${agent ? ` · ${activityLabel(agent)}` : ""}.`
                : "Recent campaign progress, review feedback, and problems that need attention."
            }
            // Scoped here from a run's live view, so the way out is the unscoped
            // list rather than whichever page happened to link in.
            backTo={execution ? { href: "/logs", label: "All activity" } : undefined}
          />
          {logs.length === 0 ? (
            <EmptyState
              icon={ScrollText}
              title="No activity yet"
              description="Campaign progress and review feedback will appear here when you start a run."
            />
          ) : (
            <LogTable logs={logs} execution={execution} agent={agent} />
          )}
        </div>
      )}
    </PageData>
  );
}

type Level = "all" | "problems";

const LEVELS: { value: Level; label: string; keeps: (level: LogLevel) => boolean }[] = [
  { value: "all", label: "All activity", keeps: () => true },
  { value: "problems", label: "Problems", keeps: (level) => level === "warning" || level === "error" },
];

/** Customer activity only; diagnostics are excluded before search and counts. */
function LogTable({
  logs,
  execution,
  agent,
}: {
  logs: ExecutionLog[];
  execution: string | undefined;
  agent: string | undefined;
}) {
  const [level, setLevel] = useState<Level>("all");
  const [query, setQuery] = useState("");

  const counts = useMemo(
    () => new Map(LEVELS.map((option) => [option.value, logs.filter((log) => option.keeps(log.level)).length])),
    [logs],
  );
  const visible = useMemo(() => {
    const keeps = LEVELS.find((option) => option.value === level)?.keeps ?? (() => true);
    const needle = query.trim().toLocaleLowerCase();
    return logs.filter(
      (log) =>
        keeps(log.level) &&
        (!needle || `${log.message} ${activityLabel(log.agent_id)}`.toLocaleLowerCase().includes(needle)),
    );
  }, [logs, level, query]);

  return (
    <div className="space-y-3">
      <Toolbar>
        <SearchField
          label="Search activity"
          placeholder="Search progress or feedback…"
          value={query}
          onChange={setQuery}
        />
        <FilterPills
          label="Filter by level"
          value={level}
          onChange={setLevel}
          options={LEVELS.map((option) => ({
            value: option.value,
            label: option.label,
            count: counts.get(option.value) ?? 0,
          }))}
        />
      </Toolbar>

      <Card className="gap-0 py-0">
        <CardContent className="p-0">
          {visible.length === 0 ? (
            <EmptyState
              variant="inline"
              icon={SearchX}
              title={level === "problems" && !query ? "No warnings or errors" : "No matching lines"}
              description={
                level === "problems" && !query
                  ? "Nothing in these lines went wrong."
                  : "Nothing here answers to that search and filter together."
              }
            />
          ) : (
            <Table className="stacked-table">
              <TableHeader>
                <TableRow>
                  <TableHead className="w-24">Level</TableHead>
                  <TableHead className="w-40">Activity</TableHead>
                  <TableHead>Message</TableHead>
                  <TableHead className="w-44 text-right">Time</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {visible.map((log) => (
                  <TableRow
                    key={log.id}
                    className={cn(
                      "group/log",
                      log.level === "error" && "bg-red-500/[0.05] hover:bg-red-500/[0.08]",
                      log.level === "warning" && "bg-amber-400/[0.035] hover:bg-amber-400/[0.06]",
                    )}
                  >
                    <TableCell>
                      <LogLevelBadge level={log.level} />
                    </TableCell>
                    <TableCell data-label="Activity" className="text-xs text-muted-foreground">
                      {log.agent_id && execution && !agent ? (
                        <Link
                          href={`/logs?execution=${execution}&agent=${encodeURIComponent(log.agent_id)}`}
                          className="hover:text-foreground hover:underline"
                          title={`Show ${activityLabel(log.agent_id).toLowerCase()}`}
                        >
                          {activityLabel(log.agent_id)}
                        </Link>
                      ) : (
                        activityLabel(log.agent_id)
                      )}
                      {log.step !== null && (
                        <span className="ml-1.5 text-xs text-muted-foreground/70 tabular-nums">
                          #{log.step}
                        </span>
                      )}
                    </TableCell>
                    {/* Long product feedback remains available in full. */}
                    <TableCell data-label="Message" className="max-w-xl whitespace-normal">
                      <ExpandableText text={log.message} limit={180} />
                      {!execution && log.campaign_execution_id && (
                        <Link
                          href={`/logs?execution=${log.campaign_execution_id}`}
                          className="mt-1 inline-block text-xs text-muted-foreground transition-opacity hover:text-violet-300 focus-visible:opacity-100 md:opacity-0 md:group-hover/log:opacity-100"
                        >
                          This run only →
                        </Link>
                      )}
                    </TableCell>
                    <TableCell
                      data-label="Logged"
                      className="text-right text-xs text-muted-foreground tabular-nums"
                      title={formatAbsolute(log.created_at)}
                    >
                      {new Date(log.created_at).toDateString() === new Date().toDateString()
                        ? formatTime(log.created_at)
                        : formatAbsolute(log.created_at)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
      <p role="status" className="px-1 text-xs text-muted-foreground">
        Showing {visible.length} of {logs.length} recent updates.
      </p>
    </div>
  );
}
