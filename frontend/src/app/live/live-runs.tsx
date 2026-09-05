"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { MarketJobCard } from "@/components/market-job-card";
import { StatusBadge } from "@/components/status-badge";
import { Card, CardContent } from "@/components/ui/card";
import { api } from "@/lib/api-client";
import { startVisiblePolling } from "@/lib/visible-polling";
import { formatDuration } from "@/lib/format";
import type { MarketJob, RunningExecution } from "@/lib/types";

//: Campaigns start and finish over minutes, not seconds - this is a "what is
//: happening" board, not a metrics feed, so a slow poll is enough. Each run's
//: own page is where the second-by-second detail lives.
const REFRESH_MS = 4000;

export function LiveRuns({
  initialRuns,
  initialJobs,
  initiallyUnavailable = false,
}: {
  initialRuns: RunningExecution[];
  initialJobs: MarketJob[];
  initiallyUnavailable?: boolean;
}) {
  const [runs, setRuns] = useState(initialRuns);
  const [jobs, setJobs] = useState(initialJobs);
  const [unavailable, setUnavailable] = useState(initiallyUnavailable);
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    let cancelled = false;
    const stop = startVisiblePolling(async () => {
      const [runResult, jobResult] = await Promise.allSettled([
        api.listRunningExecutions(), api.listMarketJobs(),
      ]);
      if (cancelled) return;
      if (runResult.status === "fulfilled") setRuns(runResult.value);
      if (jobResult.status === "fulfilled") setJobs(jobResult.value);
      setUnavailable(runResult.status === "rejected" || jobResult.status === "rejected");
    }, REFRESH_MS);
    return () => {
      cancelled = true;
      stop();
    };
  }, []);

  const running = jobs.filter((job) => job.state === "running");
  // A finished job is kept on the board rather than dropped: five minutes
  // after a scan lands, "what happened" is still the question, and the answer
  // includes what it cost. Two is enough to answer it without becoming a
  // history page - that is what each brand's own market tab is for.
  const recent = jobs.filter((job) => job.state !== "running").slice(0, 2);

  const hasActiveWork = runs.length > 0 || running.length > 0;
  useEffect(() => {
    if (!hasActiveWork) return;
    const stop = startVisiblePolling(async () => { setNow(Date.now()); }, 1000);
    return stop;
  }, [hasActiveWork]);

  return (
    <div className="space-y-4">
      {unavailable && (
        <p role="status" className="rounded-xl border border-amber-400/20 bg-amber-400/5 p-4 text-sm text-amber-200">
          Live updates are temporarily unavailable. Any cards below show the last known state. Retrying automatically.
        </p>
      )}
      {runs.length === 0 && jobs.length === 0 && !unavailable && (
        <Card>
          <CardContent className="py-10 text-center">
            <h2 className="font-medium">All quiet in the studio</h2>
            <p className="mx-auto mt-2 max-w-md text-sm leading-relaxed text-muted-foreground">
              Your campaigns and market research will appear here as they run.
            </p>
            <Link href="/campaigns" className="mt-5 inline-block text-sm font-medium text-violet-300 hover:underline">Open campaigns →</Link>
          </CardContent>
        </Card>
      )}
      {[...running, ...recent].map((job) => (
        <MarketJobCard key={`${job.brand_id}-${job.started_at}`} job={job} now={now} />
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
