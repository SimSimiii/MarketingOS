"use client";

import { useState } from "react";
import Link from "next/link";
import { AudioLines, RefreshCw } from "lucide-react";

import { EmptyState } from "@/components/empty-state";
import { MarketJobCard } from "@/components/market-job-card";
import { Notice } from "@/components/notice";
import { CompilationJobCard } from "./compilation-job-card";
import { StatusBadge } from "@/components/status-badge";
import { Card, CardContent } from "@/components/ui/card";
import { api } from "@/lib/api-client";
import { Button, buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { formatDuration, formatTime } from "@/lib/format";
import type { CompilationJob, MarketJob, RunningExecution } from "@/lib/types";

export function LiveRuns({
  initialRuns,
  initialJobs,
  initialCompilations,
  initiallyUnavailable = false,
}: {
  initialRuns: RunningExecution[];
  initialJobs: MarketJob[];
  initialCompilations: CompilationJob[];
  initiallyUnavailable?: boolean;
}) {
  const [runs, setRuns] = useState(initialRuns);
  const [jobs, setJobs] = useState(initialJobs);
  const [compilations, setCompilations] = useState(initialCompilations);
  const [unavailable, setUnavailable] = useState(initiallyUnavailable);
  const [now, setNow] = useState(() => Date.now());

  const [refreshing, setRefreshing] = useState(false);
  async function refresh() {
    setRefreshing(true);
    api.invalidate();
    const [runResult, jobResult, compilationResult] = await Promise.allSettled([
      api.listRunningExecutions(), api.listMarketJobs(), api.listKnowledgeJobs(),
    ]);
    if (runResult.status === "fulfilled") setRuns(runResult.value);
    if (jobResult.status === "fulfilled") setJobs(jobResult.value);
    if (compilationResult.status === "fulfilled") setCompilations(compilationResult.value);
    setUnavailable([runResult, jobResult, compilationResult].some((result) => result.status === "rejected"));
    setNow(Date.now());
    setRefreshing(false);
  }

  const running = jobs.filter((job) => job.state === "running");
  const recent = jobs.filter((job) => job.state !== "running").slice(0, 2);

  const compiling = compilations.filter((job) => job.state === "running");
  const recentlyCompiled = compilations.filter((job) => job.state !== "running").slice(0, 2);
  const nothingRunning =
    runs.length === 0 && running.length === 0 && compiling.length === 0;
  const finishedCount = recent.length + recentlyCompiled.length;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <Button variant="outline" size="sm" disabled={refreshing} onClick={refresh}>
          <RefreshCw
            className={cn("size-3.5", refreshing && "motion-safe:animate-spin")}
            aria-hidden="true"
          />
          {refreshing ? "Refreshing…" : "Refresh runs"}
        </Button>
        <p className="text-xs text-muted-foreground tabular-nums">
          Snapshot from {formatTime(now)}
        </p>
      </div>
      {unavailable && (
        <Notice tone="warning" title="Refresh failed">
          Cards show the last known state. Use Refresh runs to retry.
        </Notice>
      )}
      {nothingRunning && !unavailable && (
        <EmptyState
          icon={AudioLines}
          title="All quiet in the studio"
          description="Nothing is running. Campaigns, knowledge compilation and market research appear here while they work."
          action={
            <Link href="/campaigns" className={buttonVariants({ variant: "outline", size: "sm" })}>
              Open campaigns
            </Link>
          }
        />
      )}

      {/* Running first, and campaign runs first among them: they are what a
          reader opens this page to watch. They used to render last, under
          every finished LinkedIn search, on a page whose eyebrow said "in
          progress". */}
      {!nothingRunning && (
        <section aria-labelledby="running-title" className="space-y-3">
          <h2 id="running-title" className="flex items-center gap-2 text-xs font-medium uppercase tracking-widest text-muted-foreground">
            <span className="size-1.5 rounded-full bg-violet-400 motion-safe:animate-pulse" aria-hidden="true" />
            Running now
          </h2>
          {runs.map((run) => (
            <Link
              key={run.id}
              href={`/campaigns/${run.campaign_id}/executions/${run.id}`}
              className="block"
            >
              <Card className="transition-colors hover:ring-violet-400/40">
                <CardContent className="flex items-start gap-4">
                  <span className="mt-1.5 size-2 shrink-0 motion-safe:animate-pulse rounded-full bg-primary" />
                  <div className="min-w-0 flex-1 space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-medium">{run.campaign_name}</span>
                      <StatusBadge status={run.status} />
                    </div>
                    <p className="truncate text-sm text-muted-foreground">{run.campaign_request}</p>
                  </div>
                  <span className="shrink-0 text-sm text-muted-foreground tabular-nums">
                    {run.started_at
                      ? formatDuration(now - new Date(run.started_at).getTime())
                      : "starting"}
                  </span>
                </CardContent>
              </Card>
            </Link>
          ))}
          {running.map((job) => (
            <MarketJobCard key={`${job.brand_id}-${job.started_at}`} job={job} now={now} />
          ))}
          {compiling.map((job) => (
            <CompilationJobCard key={`${job.brand_id}-${job.started_at}`} job={job} now={now} />
          ))}
        </section>
      )}

      {/* A finished job is kept on the board rather than dropped: five minutes
          after a scan lands, "what happened" is still the question, and the
          answer includes what it cost. A few are enough to answer it without
          becoming a history page - that is what each brand's own tabs are for. */}
      {finishedCount > 0 && (
        <section aria-labelledby="finished-title" className="space-y-3 pt-2">
          <h2 id="finished-title" className="text-xs font-medium uppercase tracking-widest text-muted-foreground">
            Recently finished
          </h2>
          {recent.map((job) => (
            <MarketJobCard key={`${job.brand_id}-${job.started_at}`} job={job} now={now} />
          ))}
          {recentlyCompiled.map((job) => (
            <CompilationJobCard key={`${job.brand_id}-${job.started_at}`} job={job} now={now} />
          ))}
        </section>
      )}
    </div>
  );
}
