"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { ScrollText, Search, SearchX } from "lucide-react";

import { EmptyState } from "@/components/empty-state";
import { ExpandableText } from "@/components/expandable-text";
import { PageHeader } from "@/components/page-header";
import { LogLevelBadge } from "@/components/status-badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
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
          .catch(() => [])
      : await api.listLogs(200).catch(() => []);
    return { logs };
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
                ? `Every line logged during one run${agent ? ` by ${agent}` : ""}.`
                : "The most recent lines across all campaign runs."
            }
            // Scoped here from a run's live view, so the way out is the unscoped
            // list rather than whichever page happened to link in.
            backTo={execution ? { href: "/logs", label: "All activity" } : undefined}
          />
          {logs.length === 0 ? (
            <EmptyState
              icon={ScrollText}
              title="Nothing logged yet"
              description="Every step a run takes is written here as it happens. Start a campaign and the lines will arrive."
            />
          ) : (
            <LogTable logs={logs} execution={execution} agent={agent} />
          )}
        </div>
      )}
    </PageData>
  );
}

type Level = "all" | "useful" | "problems";

const LEVELS: { value: Level; label: string; keeps: (level: LogLevel) => boolean }[] = [
  { value: "useful", label: "Hide debug", keeps: (level) => level !== "debug" },
  { value: "problems", label: "Problems", keeps: (level) => level === "warning" || level === "error" },
  { value: "all", label: "Everything", keeps: () => true },
];

/**
 * The log, filtered.
 *
 * Half of what a run logs is DEBUG transport chatter - "Sent 16,094
 * characters to gpt-5.6-sol" - and it arrives in threes, one per cold reader.
 * Shown unfiltered, the five warnings in a run sat somewhere among a hundred
 * of those. Debug is hidden until asked for; problems are one click away.
 */
function LogTable({
  logs,
  execution,
  agent,
}: {
  logs: ExecutionLog[];
  execution: string | undefined;
  agent: string | undefined;
}) {
  const [level, setLevel] = useState<Level>("useful");
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
        (!needle || `${log.message} ${log.agent_id ?? ""}`.toLocaleLowerCase().includes(needle)),
    );
  }, [logs, level, query]);

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-3 rounded-xl border border-border bg-card p-3">
        <div className="relative min-w-48 flex-1">
          <Search
            className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
            aria-hidden="true"
          />
          <Input
            type="search"
            aria-label="Search activity"
            placeholder="Search messages or agents…"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            className="h-9 pl-9"
          />
        </div>
        <div role="group" aria-label="Filter by level" className="flex flex-wrap gap-1.5">
          {LEVELS.map((option) => (
            <button
              key={option.value}
              type="button"
              aria-pressed={level === option.value}
              onClick={() => setLevel(option.value)}
              className={cn(
                buttonVariants({ variant: level === option.value ? "secondary" : "ghost", size: "sm" }),
                level === option.value && "ring-1 ring-violet-400/40",
              )}
            >
              {option.label}
              <span className="tabular-nums text-muted-foreground">{counts.get(option.value) ?? 0}</span>
            </button>
          ))}
        </div>
      </div>

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
                  <TableHead className="w-40">Agent</TableHead>
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
                      log.level === "error" && "bg-destructive/[0.04]",
                      log.level === "warning" && "bg-amber-400/[0.03]",
                    )}
                  >
                    <TableCell>
                      <LogLevelBadge level={log.level} />
                    </TableCell>
                    <TableCell data-label="Agent" className="text-sm text-muted-foreground">
                      {log.agent_id && execution && !agent ? (
                        <Link
                          href={`/logs?execution=${execution}&agent=${encodeURIComponent(log.agent_id)}`}
                          className="hover:text-foreground hover:underline"
                          title={`Only ${log.agent_id}'s lines`}
                        >
                          {log.agent_id}
                        </Link>
                      ) : (
                        log.agent_id ?? "—"
                      )}
                      {log.step !== null && (
                        <span className="ml-1.5 text-xs text-muted-foreground/70 tabular-nums">
                          #{log.step}
                        </span>
                      )}
                    </TableCell>
                    {/* A run writes whole prompts into this column. Wrapping
                        them is right; letting one line own a screen and a half
                        is not - the excerpt is what makes the list scannable,
                        and the full text is one click away. */}
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
      <p role="status" className="text-xs text-muted-foreground">
        Showing {visible.length} of {logs.length} lines{execution ? "" : " - the most recent 200"}.
      </p>
    </div>
  );
}
