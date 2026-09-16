"use client";

import { useState } from "react";
import Link from "next/link";
import { AudioLines, ContactRound, RefreshCw } from "lucide-react";

import { EmptyState } from "@/components/empty-state";
import { MarketJobCard } from "@/components/market-job-card";
import { Notice } from "@/components/notice";
import { CompilationJobCard } from "./compilation-job-card";
import { StatusBadge } from "@/components/status-badge";
import { Card, CardContent } from "@/components/ui/card";
import { api } from "@/lib/api-client";
import { Button, buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
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
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <Button variant="outline" size="sm" disabled={refreshing} onClick={refresh}>
          <RefreshCw
            className={cn("size-3.5", refreshing && "motion-safe:animate-spin")}
            aria-hidden="true"
          />
          {refreshing ? "Refreshing…" : "Refresh runs"}
        </Button>
        <p className="text-xs text-muted-foreground tabular-nums">
          Snapshot from {new Date(now).toLocaleTimeString()}
        </p>
      </div>
      {unavailable && (
        <Notice tone="warning" title="Refresh failed">
          Cards show the last known state. Use Refresh runs to retry.
        </Notice>
      )}
      {runs.length === 0 && jobs.length === 0 && compilations.length === 0 && linkedin.length === 0 && !unavailable && (
        <EmptyState
          icon={AudioLines}
          title="All quiet in the studio"
          description="Your campaigns, knowledge compilation and market research will appear here as they run."
          action={
            <Link href="/campaigns" className={buttonVariants({ variant: "outline", size: "sm" })}>
              Open campaigns
            </Link>
          }
        />
      )}
      {[...running, ...recent].map((job) => (
        <MarketJobCard key={`${job.brand_id}-${job.started_at}`} job={job} now={now} />
      ))}
      {[...compiling, ...recentlyCompiled].map((job) => (
        <CompilationJobCard key={`${job.brand_id}-${job.started_at}`} job={job} now={now} />
      ))}
      {linkedin.map((run) => (
        <Link key={run.id} href={`/brands/${run.brand_id}/linkedin`} className="block">
          <Card className="transition-colors hover:ring-violet-400/40">
            <CardContent className="flex items-start gap-4">
              <span className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-lg border border-hairline bg-background/40 text-violet-300">
                <ContactRound className="size-4" aria-hidden="true" />
              </span>
              <div className="min-w-0 flex-1 space-y-1">
                <p className="truncate font-medium">{linkedInLabel(run)}</p>
                <p className="text-sm text-muted-foreground">
                  LinkedIn · {run.state} · {run.calls} model calls
                </p>
              </div>
            </CardContent>
          </Card>
        </Link>
      ))}
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
    </div>
  );
}

/** What a LinkedIn run is called on the board.
 *
 * `request` is a `Partial`, and there is a third kind - `criteria` - that the
 * board used to fold into the message branch, so a run with no recipient read
 * as "Message to undefined" and a search with no stored query as nothing at
 * all. Naming the kind is always possible; naming its subject is not. */
function linkedInLabel(run: LinkedInRun): string {
  if (run.kind === "search") {
    return run.request.query ? `Search: ${run.request.query}` : "LinkedIn search";
  }
  if (run.kind === "criteria") {
    return "Working out who to look for";
  }
  return run.request.recipient_name
    ? `Message to ${run.request.recipient_name}`
    : "LinkedIn message";
}
