"use client";

import { useState } from "react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { formatDuration } from "@/lib/format";
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

  const lines = open ? job.log : job.log.slice(-TAIL);

  return (
    <Card
      className={cn(
        running && "ring-sky-500/30",
        job.state === "failed" && "ring-rose-500/30",
      )}
    >
      <CardContent className="space-y-3">
        <div className="flex flex-wrap items-start gap-3">
          <span
            className={cn(
              "mt-1.5 size-2 shrink-0 rounded-full",
              running ? "animate-pulse bg-sky-400" : "bg-muted-foreground/40",
            )}
          />
          <div className="min-w-0 flex-1 space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              {job.brand_id ? (
                <Link
                  href={`/brands/${job.brand_id}/market`}
                  className="font-medium hover:underline"
                >
                  {job.brand_name || "a brand"}
                </Link>
              ) : (
                <span className="font-medium">{job.brand_name || "a brand"}</span>
              )}
              <Badge variant={running ? "default" : "ghost"} className="font-normal">
                {KIND_LABELS[job.kind] ?? job.kind}
              </Badge>
            </div>
            <p className="truncate text-sm text-muted-foreground">
              {job.state === "failed" ? job.error : job.summary || job.message}
            </p>
          </div>
          <span className="shrink-0 text-sm text-muted-foreground tabular-nums">
            {formatDuration(elapsed)}
          </span>
        </div>

        {/* The spend, whether or not the trace is open. It is the one thing a
            user watching a job they started cannot get from the progress
            line, and the reason this card exists rather than a spinner. */}
        {job.calls > 0 && (
          <p className="text-xs text-muted-foreground tabular-nums">
            {job.calls} call{job.calls === 1 ? "" : "s"} ·{" "}
            {job.input_tokens.toLocaleString()} in / {job.output_tokens.toLocaleString()} out
            {job.cache_read_tokens > 0 && (
              <> · {job.cache_read_tokens.toLocaleString()} of the input was cached</>
            )}
            {job.cost_usd > 0 && <> · ${job.cost_usd.toFixed(4)}</>}
          </p>
        )}

        {job.log.length > 0 && (
          <div className="space-y-1">
            <ul className="space-y-0.5 font-mono text-[11px] leading-relaxed text-muted-foreground">
              {lines.map((line, index) => (
                <li key={`${index}-${line}`} className="break-words">
                  {line}
                </li>
              ))}
            </ul>
            {job.log.length > TAIL && (
              <button
                type="button"
                onClick={() => setOpen((current) => !current)}
                className="text-xs text-muted-foreground underline-offset-2 hover:underline"
              >
                {open ? "Show less" : `Show all ${job.log.length} lines`}
              </button>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
