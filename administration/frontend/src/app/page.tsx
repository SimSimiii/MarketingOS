"use client";

import { useEffect, useState } from "react";

import { api, type Overview, type TimeseriesPoint } from "@/lib/api";
import { compact, money } from "@/lib/format";
import { PageHeader, Shell } from "@/components/shell";
import { Card, Empty, Notice, Stat } from "@/components/ui";

export default function OverviewPage() {
  return (
    <Shell>
      <OverviewBody />
    </Shell>
  );
}

function OverviewBody() {
  const [data, setData] = useState<Overview | null>(null);
  const [signups, setSignups] = useState<TimeseriesPoint[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    Promise.all([api.overview(), api.timeseries("signups", 30)])
      .then(([overview, series]) => {
        if (cancelled) return;
        setData(overview);
        setSignups(series.series);
      })
      .catch((exception: unknown) => {
        if (!cancelled) {
          setError(exception instanceof Error ? exception.message : "Could not load.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (error) return <Notice>{error}</Notice>;
  if (data === null) return <Empty>Loading…</Empty>;

  const plans = Object.entries(data.users_by_plan).sort((a, b) => b[1] - a[1]);

  return (
    <>
      <PageHeader
        title="Overview"
        description="Who is on the platform, what they are spending, and what broke this week."
      />

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Stat
          label="Accounts"
          value={data.users_total}
          hint={`${data.users_active} active · ${data.users_suspended} suspended`}
        />
        <Stat
          label="New this week"
          value={data.signups_last_7_days}
          hint={`${data.signups_last_30_days} in the last 30 days`}
        />
        <Stat
          label="Runs this week"
          value={data.runs_last_7_days}
          hint={
            data.runs_failed_last_7_days > 0
              ? `${data.runs_failed_last_7_days} failed`
              : "none failed"
          }
        />
        <Stat
          label="Model spend"
          value={money(data.model_spend_usd)}
          hint={`${compact(data.tokens_total)} tokens, all time`}
        />
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-[1.4fr_1fr]">
        <Card title="Signups, last 30 days">
          <Sparkline points={signups} />
        </Card>

        <Card title="Plan mix">
          {plans.length === 0 ? (
            <Empty>No accounts yet.</Empty>
          ) : (
            <ul className="space-y-3">
              {plans.map(([plan, count]) => {
                const share = data.users_total > 0 ? (count / data.users_total) * 100 : 0;
                return (
                  <li key={plan}>
                    <div className="flex items-baseline justify-between text-sm">
                      <span className="capitalize">{plan}</span>
                      <span className="tabular-nums text-muted">{count}</span>
                    </div>
                    <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-white/8">
                      <div
                        className="h-full rounded-full bg-violet"
                        style={{ width: `${share}%` }}
                      />
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
          <p className="mt-5 border-t border-line pt-4 text-sm">
            <span className="text-muted">Implied MRR </span>
            <strong className="tabular-nums">{money(data.estimated_mrr_usd)}</strong>
          </p>
          <p className="mt-1 text-xs text-muted">
            Plan mix × the price map in ADMIN_PLAN_PRICES. An estimate: nothing here has
            been through a payment processor.
          </p>
        </Card>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        <Stat label="Brands" value={data.brands_total} />
        <Stat label="Campaigns" value={data.campaigns_total} />
        <Stat label="Runs, all time" value={data.runs_total} />
      </div>
    </>
  );
}

/**
 * Thirty bars, no charting library.
 *
 * The alternative was a 50 kB dependency to draw a shape whose only job is to
 * answer "is anybody signing up". Bars in a flex row do that.
 */
function Sparkline({ points }: { points: TimeseriesPoint[] }) {
  if (points.length === 0) return <Empty>No data yet.</Empty>;
  const peak = Math.max(...points.map((point) => point.value), 1);

  return (
    <div>
      <div className="flex h-28 items-end gap-[3px]" role="img" aria-label="Signups per day">
        {points.map((point) => (
          <div
            key={point.day}
            title={`${point.day}: ${point.value}`}
            className="flex-1 rounded-t-sm bg-violet/70 transition-colors hover:bg-violet"
            // A day with nothing in it still gets a sliver, so the axis reads
            // as thirty days rather than as however many had a signup.
            style={{ height: `${Math.max((point.value / peak) * 100, 3)}%` }}
          />
        ))}
      </div>
      <div className="mt-2 flex justify-between text-xs text-muted">
        <span>{points[0]?.day}</span>
        <span>peak {peak}</span>
        <span>{points[points.length - 1]?.day}</span>
      </div>
    </div>
  );
}
