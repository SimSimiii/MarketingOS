"use client";

import { useEffect, useState, type ComponentType, type ReactNode } from "react";
import { AlertTriangle, ClipboardCheck, Mail, RefreshCcw } from "lucide-react";

import { Skeleton } from "@/components/skeleton";
import { api } from "@/lib/api-client";
import type { RunForecast as Forecast } from "@/lib/types";

/** A brief estimate of the deliverables and reusable preparation. */
export function RunForecast({ campaignId, refreshKey }: { campaignId: string; refreshKey?: string }) {
  const [forecast, setForecast] = useState<Forecast | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let live = true;
    api
      .getCampaignForecast(campaignId)
      .then((result) => {
        if (live) { setForecast(result); setFailed(false); }
      })
      .catch(() => { if (live) { setForecast(null); setFailed(true); } });
    return () => {
      live = false;
    };
  }, [campaignId, refreshKey]);

  if (failed) {
    return (
      <p role="alert" className="flex items-start gap-2 rounded-xl border border-amber-400/20 bg-amber-400/[0.05] p-3 text-xs leading-relaxed text-amber-100/85">
        <AlertTriangle className="mt-px size-3.5 shrink-0 text-amber-300" aria-hidden="true" />
        The run estimate is unavailable. Refresh this page before starting.
      </p>
    );
  }
  if (!forecast) {
    return (
      <div role="status" aria-label="Loading the run estimate" className="space-y-2 border-t border-hairline pt-4">
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-4 w-2/3" />
        <Skeleton className="h-4 w-1/2" />
      </div>
    );
  }

  return (
    <div className="space-y-3.5 border-t border-hairline pt-4 text-xs leading-relaxed text-muted-foreground">
      <p className="text-[0.6875rem] font-medium uppercase tracking-[0.16em]">Run estimate</p>
      <Line icon={Mail}>
        <span className="text-foreground">
          {forecast.emails} {forecast.deliverable ?? "email"}
          {forecast.emails === 1 ? "" : "s"}
        </span>
        {forecast.count_is_explicit ? "" : " - you did not name a number, so this is the working assumption"}
      </Line>
      <Line icon={ClipboardCheck}>
        Each draft is checked against your sources and reviewed for clarity before delivery.
      </Line>
      {forecast.knowledge_reused ? (
        <Line icon={RefreshCcw} tone="good">
          Your material has already been read and has not changed, so this run reads none of it
          again.
        </Line>
      ) : (
        forecast.compile_high > 0 && (
          <Line icon={RefreshCcw}>
            Your material will be prepared on the first run. Later campaigns for this business
            can reuse it.
          </Line>
        )
      )}
    </div>
  );
}

function Line({
  icon: Icon,
  tone,
  children,
}: {
  icon: ComponentType<{ className?: string }>;
  tone?: "good";
  children: ReactNode;
}) {
  return (
    <p className="flex gap-2.5">
      <Icon
        className={tone === "good" ? "mt-0.5 size-3.5 shrink-0 text-emerald-300" : "mt-0.5 size-3.5 shrink-0 text-violet-300"}
        aria-hidden="true"
      />
      <span className="min-w-0">{children}</span>
    </p>
  );
}
