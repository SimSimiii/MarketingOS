"use client";

import { LiveRuns } from "@/app/live/live-runs";
import { PageHeader } from "@/components/page-header";
import { api } from "@/lib/api-client";
import { PageData, usePageData } from "@/lib/page-data";

export function LiveView() {
  const state = usePageData(
    () =>
      Promise.allSettled([
        api.listRunningExecutions(),
        api.listMarketJobs(),
        api.listKnowledgeJobs(),
      ]),
    [],
  );

  return (
    <PageData state={state}>
      {([runs, jobs, compilations]) => (
        <div className="space-y-6">
          <PageHeader eyebrow="In progress" title="Runs" description="Follow your campaigns, knowledge compilation and market research. Use Refresh to load the latest saved progress." />
          <LiveRuns
            initialRuns={runs.status === "fulfilled" ? runs.value : []}
            initialJobs={jobs.status === "fulfilled" ? jobs.value : []}
            initialCompilations={compilations.status === "fulfilled" ? compilations.value : []}
            initiallyUnavailable={runs.status === "rejected" || jobs.status === "rejected" || compilations.status === "rejected"}
          />
        </div>
      )}
    </PageData>
  );
}
