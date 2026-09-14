"use client";

import { useState } from "react";
import Link from "next/link";

import { MarketJobCard } from "@/components/market-job-card";
import { CompilationJobCard } from "./compilation-job-card";
import { StatusBadge } from "@/components/status-badge";
import { Card, CardContent } from "@/components/ui/card";
import { api } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { formatDuration } from "@/lib/format";
import type { CompilationJob, LinkedInRun, MarketJob, RunningExecution } from "@/lib/types";

export function LiveRuns({
  initialRuns,
  initialLinkedIn,
  initialJobs,
  initialCompilations,
  initiallyUnavailable = false,
}: {
  initialRuns: RunningExecution[];
  initialLinkedIn: LinkedInRun[];
  initialJobs: MarketJob[];
  initialCompilations: CompilationJob[];
  initiallyUnavailable?: boolean;
}) {
  const [linkedin, setLinkedIn] = useState(initialLinkedIn);
  const [runs, setRuns] = useState(initialRuns);
  const [jobs, setJobs] = useState(initialJobs);
  const [compilations, setCompilations] = useState(initialCompilations);
  const [unavailable, setUnavailable] = useState(initiallyUnavailable);
  const [now, setNow] = useState(() => Date.now());

  const [refreshing, setRefreshing] = useState(false);
  async function refresh() {
    setRefreshing(true);
    const [runResult, jobResult, compilationResult, linkedinResult] = await Promise.allSettled([
      api.listRunningExecutions(), api.listMarketJobs(), api.listKnowledgeJobs(), api.listRecentLinkedInRuns(),
    ]);
    if (runResult.status === "fulfilled") setRuns(runResult.value);
    if (jobResult.status === "fulfilled") setJobs(jobResult.value);
    if (compilationResult.status === "fulfilled") setCompilations(compilationResult.value);
    setUnavailable([runResult, jobResult, compilationResult, linkedinResult].some((result) => result.status === "rejected"));
    if (linkedinResult.status === "fulfilled") setLinkedIn(linkedinResult.value);
    setNow(Date.now());
    setRefreshing(false);
  }

  const running = jobs.filter((job) => job.state === "running");
  // A finished job is kept on the board rather than dropped: five minutes
  // after a scan lands, "what happened" is still the question, and the answer
  // includes what it cost. Two is enough to answer it without becoming a
  // history page - that is what each brand's own market tab is for.
  const recent = jobs.filter((job) => job.state !== "running").slice(0, 2);

  const compiling = compilations.filter((job) => job.state === "running");
  const recentlyCompiled = compilations.filter((job) => job.state !== "running").slice(0, 2);

  return (
    <div className="space-y-4">
      <Button variant="outline" disabled={refreshing} onClick={refresh}>{refreshing ? "Refreshing…" : "Refresh runs"}</Button>
      <p className="text-xs text-muted-foreground">Snapshot from {new Date(now).toLocaleTimeString()}. Refresh to see progress.</p>
      {unavailable && (
        <p role="status" className="rounded-xl border border-amber-400/20 bg-amber-400/5 p-4 text-sm text-amber-200">
          Refresh failed. Cards show the last known state. Use Refresh runs to retry.
        </p>
      )}
      {runs.length === 0 && jobs.length === 0 && compilations.length === 0 && linkedin.length === 0 && !unavailable && (
        <Card>
          <CardContent className="py-10 text-center">
            <h2 className="font-medium">All quiet in the studio</h2>
            <p className="mx-auto mt-2 max-w-md text-sm leading-relaxed text-muted-foreground">
              Your campaigns, knowledge compilation and market research will appear here as they run.
            </p>
            <Link href="/campaigns" className="mt-5 inline-block text-sm font-medium text-violet-300 hover:underline">Open campaigns →</Link>
          </CardContent>
        </Card>
      )}
      {[...running, ...recent].map((job) => (
        <MarketJobCard key={`${job.brand_id}-${job.started_at}`} job={job} now={now} />
      ))}
      {[...compiling, ...recentlyCompiled].map((job) => (
        <CompilationJobCard key={`${job.brand_id}-${job.started_at}`} job={job} now={now} />
      ))}
      {linkedin.map((run) => (
        <Link key={run.id} href={`/brands/${run.brand_id}/linkedin`} className="block">
          <Card><CardContent className="space-y-1">
            <p className="font-medium">LinkedIn · {run.kind === "search" ? run.request.query : `Message to ${run.request.recipient_name}`}</p>
            <p className="text-sm text-muted-foreground">{run.state} · {run.calls} model calls</p>
          </CardContent></Card>
        </Link>
      ))}
      {runs.map((run) => (
        <Link
          key={run.id}
          href={`/campaigns/${run.campaign_id}/executions/${run.id}`}
          className="block"
        >
          <Card className="transition-colors hover:ring-foreground/25">
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
    </div>
  );
}
