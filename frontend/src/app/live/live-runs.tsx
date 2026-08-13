"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { StatusBadge } from "@/components/status-badge";
import { Card, CardContent } from "@/components/ui/card";
import { api } from "@/lib/api-client";
import { formatDuration } from "@/lib/format";
import type { RunningExecution } from "@/lib/types";

//: Campaigns start and finish over minutes, not seconds - this is a "what is
//: happening" board, not a metrics feed, so a slow poll is enough. Each run's
//: own page is where the second-by-second detail lives.
const REFRESH_MS = 4000;

export function LiveRuns({ initialRuns }: { initialRuns: RunningExecution[] }) {
  const [runs, setRuns] = useState(initialRuns);
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const refresh = setInterval(() => {
      api.listRunningExecutions().then(setRuns).catch(() => undefined);
    }, REFRESH_MS);
    const clock = setInterval(() => setNow(Date.now()), 1000);
    return () => {
      clearInterval(refresh);
      clearInterval(clock);
    };
  }, []);

  if (runs.length === 0) {
    return (
      <Card>
        <CardContent className="py-10 text-center text-sm text-muted-foreground">
          Nothing is running right now. Start a campaign and it will show up here.
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-3">
      {runs.map((run) => (
        <Link
          key={run.id}
          href={`/campaigns/${run.campaign_id}/executions/${run.id}`}
          className="block"
        >
          <Card className="transition-colors hover:ring-foreground/25">
            <CardContent className="flex items-start gap-4">
              <span className="mt-1.5 size-2 shrink-0 animate-pulse rounded-full bg-primary" />
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
