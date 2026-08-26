"use client";

import { useEffect, useState } from "react";

import { api } from "@/lib/api-client";
import { formatCost } from "@/lib/format";
import type { RunForecast as Forecast } from "@/lib/types";

/**
 * What this run will cost, before it is bought.
 *
 * Every call here is billed against a personal Claude subscription, and until
 * this existed the only description of the difference between the presets was
 * two adjectives - "cheaper models", "most thorough review" - with the answer
 * arriving on the receipt. It is free to show: nothing in the pipeline spends
 * a model call deciding what happens next, so the number of calls a run makes
 * follows from the preset and from how many emails the request asked for.
 *
 * A range, and labelled as one. The low end is the run where every email
 * lands first time; the high end buys every rewrite and rework it is allowed.
 * Quoting the middle as though it were the answer would be the same kind of
 * lie as a score nobody gave.
 *
 * The money beside it is not a price list. It is what this user's own past
 * runs on this preset actually came to, so it is absent until there are some
 * and it gets better the more they run.
 */
export function RunForecast({ campaignId, refreshKey }: { campaignId: string; refreshKey?: string }) {
  const [forecast, setForecast] = useState<Forecast | null>(null);

  useEffect(() => {
    let live = true;
    api
      .getCampaignForecast(campaignId)
      .then((result) => {
        if (live) setForecast(result);
      })
      .catch(() => undefined);
    return () => {
      live = false;
    };
  }, [campaignId, refreshKey]);

  if (!forecast) return null;

  return (
    <div className="space-y-1 text-sm text-muted-foreground">
      <p className="tabular-nums">
        <span className="text-foreground">
          {forecast.low === forecast.high
            ? `${forecast.low} model calls`
            : `${forecast.low}–${forecast.high} model calls`}
        </span>{" "}
        for {forecast.emails} email{forecast.emails === 1 ? "" : "s"}
        {forecast.count_is_explicit ? "" : " (you did not name a number, so this is the working assumption)"}
        {" — "}
        {forecast.low} if every email lands first time, {forecast.high} if every rewrite is bought.
      </p>
      {forecast.knowledge_reused ? (
        <p>
          Your material has already been read and has not changed, so this run reads none of it
          again.
        </p>
      ) : (
        forecast.compile_high > 0 && (
          <p>
            {forecast.compile_high} of those read your material for the first time. Every later
            campaign for this business skips them.
          </p>
        )
      )}
      {forecast.observed_runs > 0 && (
        <p className="tabular-nums">
          {/* Per delivered email, and left unmultiplied on purpose: past runs
              were different lengths, and doing that arithmetic here would join
              two real measurements with an assumption and present the result
              as though the whole thing had been measured. */}
          Across your {forecast.observed_runs} finished run
          {forecast.observed_runs === 1 ? "" : "s"} on this preset, a delivered email has
          typically cost {formatCost(forecast.observed_cost_per_email)}.
        </p>
      )}
    </div>
  );
}
