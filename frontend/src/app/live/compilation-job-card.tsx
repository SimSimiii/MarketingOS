import Link from "next/link";
import { BookOpen } from "lucide-react";

import { StatusBadge } from "@/components/status-badge";
import { Card, CardContent } from "@/components/ui/card";
import { formatDuration } from "@/lib/format";
import { jobProgress, problemText, progressText } from "@/lib/product-progress";
import type { CompilationJob } from "@/lib/types";

export function CompilationJobCard({ job, now }: { job: CompilationJob; now: number }) {
  const lines = jobProgress(job.log);
  const elapsed = (job.finished_at ? new Date(job.finished_at).getTime() : now)
    - new Date(job.started_at).getTime();

  return (
    <Card className={job.state === "running" ? "ring-violet-400/30" : undefined}>
      <CardContent className="space-y-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex min-w-0 flex-1 items-start gap-4">
          <span
            className={
              job.state === "running"
                ? "flex size-10 shrink-0 items-center justify-center rounded-xl bg-violet-500/15 ring-1 ring-violet-400/30"
                : "icon-tile flex size-10 shrink-0 items-center justify-center rounded-xl"
            }
          >
            {job.state === "running" ? <span className="live-dot" aria-hidden="true" /> : <BookOpen className="size-[1.125rem]" aria-hidden="true" />}
          </span>
          <div className="min-w-0 space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <Link href={`/brands/${job.brand_id}/knowledge/base`} className="font-semibold hover:text-violet-200">
                {job.brand_name} · Preparing brand knowledge
              </Link>
              <StatusBadge status={job.state === "idle" ? "pending" : job.state} />
            </div>
            <p role="status" className="text-sm text-muted-foreground">{job.state === "failed" ? problemText(job.message) : progressText(job.message, job.state === "completed" ? "Brand knowledge is ready." : "Reading your sources…")}</p>
          </div>
          </div>
          <span className="shrink-0 rounded-full bg-white/[0.05] px-3 py-1 text-sm tabular-nums text-muted-foreground ring-1 ring-white/[0.07]">{formatDuration(Math.max(0, elapsed))}</span>
        </div>
        <ul className="space-y-1 rounded-xl bg-black/25 p-3 text-xs leading-relaxed text-muted-foreground ring-1 ring-white/[0.05]">
          {lines.slice(-4).map((line, index) => <li key={index}>{line}</li>)}
        </ul>
        {lines.length > 4 && (
          <details className="text-xs text-muted-foreground">
            <summary className="cursor-pointer">Show earlier steps</summary>
            <ul className="mt-2 space-y-1">
              {lines.slice(0, -4).map((line, index) => <li key={index}>{line}</li>)}
            </ul>
          </details>
        )}
      </CardContent>
    </Card>
  );
}
