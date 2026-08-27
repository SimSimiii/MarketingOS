import { LiveRuns } from "@/app/live/live-runs";
import { api } from "@/lib/api-client";

export default async function LivePage() {
  const [runs, jobs] = await Promise.all([
    api.listRunningExecutions().catch(() => []),
    api.listMarketJobs().catch(() => []),
  ]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Live</h1>
        <p className="text-sm text-muted-foreground">
          Every campaign and every market job running right now. Open one to watch it step by
          step.
        </p>
      </div>

      <LiveRuns initialRuns={runs} initialJobs={jobs} />
    </div>
  );
}
