"use client";

import { useEffect, useState } from "react";

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

  if (failed) return <p role="alert" className="text-sm text-amber-300">The run estimate is unavailable. Refresh this page before starting.</p>;
  if (!forecast) return <p className="text-sm text-muted-foreground">Loading the run estimate…</p>;

  return (
    <div className="space-y-1 text-sm text-muted-foreground">
      <p className="tabular-nums">
        Prepared for {forecast.emails} {forecast.deliverable ?? "email"}
        {forecast.emails === 1 ? "" : "s"}
        {forecast.count_is_explicit ? "" : " (you did not name a number, so this is the working assumption)"}
        .
      </p>
      <p className="tabular-nums">
        Estimated model calls: {forecast.low}–{forecast.high}
        {forecast.compile_high > 0 ? `, including ${forecast.compile_low}–${forecast.compile_high} for source preparation` : ""}.
        This is a planning range; a run can stop early or use transport retries.
      </p>
      {forecast.observed_runs > 0 ? <p>
        Historical processing estimate: ${(forecast.observed_cost_per_email * forecast.emails).toFixed(2)} for this quantity,
        based on {forecast.observed_runs} completed {forecast.preset} runs. This is not a quoted credit charge or a spending cap.
      </p> : <p>No processing-cost estimate is available here. The call range does not define a credit spending cap.</p>}
      {forecast.knowledge_reused ? (
        <p>
          Your material has already been read and has not changed, so this run reads none of it
          again.
        </p>
      ) : (
        forecast.compile_high > 0 && (
          <p>
            Your material will be prepared on the first run. Later campaigns for this business
            can reuse it.
          </p>
        )
      )}
    </div>
  );
}
