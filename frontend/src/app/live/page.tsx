import { LiveRuns } from "@/app/live/live-runs";
import { PageHeader } from "@/components/page-header";
import { api } from "@/lib/api-server";

export default async function LivePage() {
  const [runs, jobs, compilations, linkedin] = await Promise.allSettled([
    api.listRunningExecutions(),
    api.listMarketJobs(),
    api.listKnowledgeJobs(),
    api.listRecentLinkedInRuns(),
  ]);

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="In progress" title="Runs" description="Follow your campaigns, knowledge compilation and market research. Use Refresh to load the latest saved progress." />
      <LiveRuns
        initialLinkedIn={linkedin.status === "fulfilled" ? linkedin.value : []}
        initialRuns={runs.status === "fulfilled" ? runs.value : []}
        initialJobs={jobs.status === "fulfilled" ? jobs.value : []}
        initialCompilations={compilations.status === "fulfilled" ? compilations.value : []}
        initiallyUnavailable={runs.status === "rejected" || jobs.status === "rejected" || compilations.status === "rejected" || linkedin.status === "rejected"}
      />
    </div>
  );
}
