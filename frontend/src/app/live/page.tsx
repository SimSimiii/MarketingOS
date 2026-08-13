import { LiveRuns } from "@/app/live/live-runs";
import { api } from "@/lib/api-client";

export default async function LivePage() {
  const runs = await api.listRunningExecutions().catch(() => []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Live</h1>
        <p className="text-sm text-muted-foreground">
          Every campaign your team is working on right now. Open one to watch each specialist step
          by step.
        </p>
      </div>

      <LiveRuns initialRuns={runs} />
    </div>
  );
}
