import { LiveRuns } from "@/app/live/live-runs";
import { PageHeader } from "@/components/page-header";
import { api } from "@/lib/api-client";

export default async function LivePage() {
  const [runs, jobs] = await Promise.allSettled([
    api.listRunningExecutions(),
    api.listMarketJobs(),
  ]);

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="In progress" title="Live studio" description="Follow your campaigns and market research. Open a run to see each step as it happens." />
      <LiveRuns
        initialRuns={runs.status === "fulfilled" ? runs.value : []}
        initialJobs={jobs.status === "fulfilled" ? jobs.value : []}
        initiallyUnavailable={runs.status === "rejected" || jobs.status === "rejected"}
      />
    </div>
  );
}
