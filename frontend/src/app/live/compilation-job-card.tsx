import Link from "next/link";

import { StatusBadge } from "@/components/status-badge";
import { Card, CardContent } from "@/components/ui/card";
import { formatDuration } from "@/lib/format";
import type { CompilationJob } from "@/lib/types";

export function CompilationJobCard({ job, now }: { job: CompilationJob; now: number }) {
  const elapsed = (job.finished_at ? new Date(job.finished_at).getTime() : now)
    - new Date(job.started_at).getTime();

  return (
    <Card>
      <CardContent className="space-y-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <Link href={`/brands/${job.brand_id}/knowledge/base`} className="font-medium hover:underline">
                {job.brand_name} · Knowledge compilation
              </Link>
              <StatusBadge status={job.state === "idle" ? "pending" : job.state} />
            </div>
            <p role="status" className="text-sm text-muted-foreground">{job.message}</p>
          </div>
          <span className="text-sm tabular-nums text-muted-foreground">{formatDuration(Math.max(0, elapsed))}</span>
        </div>
        {job.calls > 0 && (
          <p className="text-xs tabular-nums text-muted-foreground">
            {job.calls} model calls · {job.input_tokens.toLocaleString()} in / {job.output_tokens.toLocaleString()} out
          </p>
        )}
        <ul className="space-y-1 text-xs text-muted-foreground">
          {job.log.slice(-4).map((line, index) => <li key={index}>{line}</li>)}
        </ul>
        {job.log.length > 4 && (
          <details className="text-xs text-muted-foreground">
            <summary className="cursor-pointer">Show earlier steps</summary>
            <ul className="mt-2 space-y-1">
              {job.log.slice(0, -4).map((line, index) => <li key={index}>{line}</li>)}
            </ul>
          </details>
        )}
      </CardContent>
    </Card>
  );
}
