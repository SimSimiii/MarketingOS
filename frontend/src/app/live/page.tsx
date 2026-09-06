import { LiveRuns } from "@/app/live/live-runs";
import { PageHeader } from "@/components/page-header";
import { api } from "@/lib/api-client";

export default async function LivePage() {
  const [runs, jobs, compilations] = await Promise.allSettled([
    api.listRunningExecutions(),
    api.listMarketJobs(),
    api.listKnowledgeJobs(),
  ]);

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="In progress" title="Live studio" description="Follow your campaigns, knowledge compilation and market research. Open a run to see each step as it happens." />
      <LiveRuns
        initialRuns={runs.status === "fulfilled" ? runs.value : []}
        initialJobs={jobs.status === "fulfilled" ? jobs.value : []}
        initialCompilations={compilations.status === "fulfilled" ? compilations.value : []}
        initiallyUnavailable={runs.status === "rejected" || jobs.status === "rejected" || compilations.status === "rejected"}
      />
    </div>
  );
}
