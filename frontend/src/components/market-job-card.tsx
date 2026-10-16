"use client";

import { useState } from "react";
import Link from "next/link";

import { Compass } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { formatDuration } from "@/lib/format";
import { jobProgress, problemText, progressText } from "@/lib/product-progress";
import { cn } from "@/lib/utils";
import type { MarketJob } from "@/lib/types";

/** What each kind of market job is doing, in the user's terms.
 *
 * The `kind` is an internal word ("prospects"), and a live board showing
 * internal words is a board somebody has to learn before they can read it. */
const KIND_LABELS: Record<string, string> = {
  scan: "Reading the competition",
  proof: "Searching for proof",
  audience: "Working out who buys this",
  audience_research: "Researching one audience",
  relevance_dossier: "Building audience relevance",
  prospects: "Finding named organisations",
};

/** How many trace lines to show without being asked.
 *
 * A market job makes a handful of calls, and the last few are the ones that
 * say what it is doing now. The rest is history, and history behind a toggle
 * is history the page does not have to scroll past. */
const TAIL = 4;

export function MarketJobCard({ job, now }: { job: MarketJob; now: number }) {
  const [open, setOpen] = useState(false);

  const running = job.state === "running";
  const elapsed = running
    ? now - new Date(job.started_at).getTime()
    : job.finished_at
      ? new Date(job.finished_at).getTime() - new Date(job.started_at).getTime()
      : 0;

  const progress = jobProgress(job.log);
  const lines = open ? progress : progress.slice(-TAIL);

  return (
    <Card
      className={cn(
        running && "ring-violet-400/30",
        job.state === "failed" && "ring-red-400/30",
      )}
    >
      <CardContent className="space-y-3">
        <div className="flex flex-wrap items-start gap-3">
          <span
            className={cn(
              "flex size-10 shrink-0 items-center justify-center rounded-xl",
              running
                ? "bg-violet-500/15 ring-1 ring-violet-400/30"
                : job.state === "failed"
                  ? "bg-red-500/10 text-red-300 ring-1 ring-red-400/25"
                  : "icon-tile",
            )}
          >
            {running ? <span className="live-dot" aria-hidden="true" /> : <Compass className="size-[1.125rem]" aria-hidden="true" />}
          </span>
          <div className="min-w-0 flex-1 space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              {job.brand_id ? (
                <Link
                  href={`/brands/${job.brand_id}/market`}
                  className="font-semibold hover:text-violet-200"
                >
                  {job.brand_name || "a brand"}
                </Link>
              ) : (
                <span className="font-semibold">{job.brand_name || "a brand"}</span>
              )}
              <Badge variant={running ? "default" : "secondary"} className="font-normal">
                {KIND_LABELS[job.kind] ?? job.kind}
              </Badge>
            </div>
            <p className="truncate text-sm text-muted-foreground">
              {job.state === "failed" ? problemText(job.error) : progressText(job.summary || job.message, job.state === "done" ? "Research complete." : KIND_LABELS[job.kind])}
            </p>
          </div>
          <span className="shrink-0 rounded-full bg-white/[0.05] px-3 py-1 text-sm tabular-nums text-muted-foreground ring-1 ring-white/[0.07]">
            {formatDuration(elapsed)}
          </span>
        </div>

        {progress.length > 0 && (
          <div className="space-y-1">
            <ul className="space-y-0.5 rounded-xl bg-black/25 p-3 text-xs leading-relaxed text-muted-foreground ring-1 ring-white/[0.05]">
              {lines.map((line, index) => (
                <li key={`${index}-${line}`} className="break-words">
                  {line}
                </li>
              ))}
            </ul>
            {progress.length > TAIL && (
              <button
                type="button"
                onClick={() => setOpen((current) => !current)}
                className="text-xs text-muted-foreground underline-offset-2 hover:underline"
              >
                {open ? "Show less" : "Show earlier progress"}
              </button>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
