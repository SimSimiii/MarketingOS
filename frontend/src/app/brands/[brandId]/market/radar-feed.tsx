"use client";

import { useEffect, useState } from "react";

import { BrandSectionHeader } from "../../brand-ui";
import { Disclosure } from "@/components/disclosure";
import { ExpandableText } from "@/components/expandable-text";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { api } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import type { RadarEvent, RadarSeverity } from "@/lib/types";
import { formatDate } from "@/lib/format";

/** Three levels, and the top one is rare on purpose: a feed where everything
 * is urgent is a feed nobody reads. */
const SEVERITY: Record<RadarSeverity, { label: string; tone: string }> = {
  acts_on_copy: {
    label: "Makes your copy worse",
    tone: "border-l-amber-500 bg-amber-500/5",
  },
  notable: { label: "Worth knowing", tone: "border-l-sky-500/60" },
  routine: { label: "On the record", tone: "border-l-border" },
};

function when(iso: string) {
  const date = new Date(iso);
  const days = Math.floor((Date.now() - date.getTime()) / 86_400_000);
  if (days === 0) return "today";
  if (days === 1) return "yesterday";
  if (days < 30) return `${days} days ago`;
  return formatDate(iso);
}

export function RadarFeed({
  brandId,
  events,
}: {
  brandId: string;
  events: RadarEvent[];
}) {
  const [rows] = useState(events);

  // Marked read on open rather than on a button: the badge counts changes the
  // user has not seen, and they have now seen them. A badge that stays lit
  // after you have read the thing is furniture.
  useEffect(() => {
    if (rows.some((row) => row.seen_at === null)) {
      api.markRadarSeen(brandId).catch(() => undefined);
    }
  }, [brandId, rows]);

  if (rows.length === 0) {
    return (
      <Card>
        <CardContent className="space-y-2 p-6 text-sm text-muted-foreground">
          <p className="font-medium text-foreground">No market changes yet</p>
          <p>Changes appear after your second scan. Update your competitors to compare their latest claims, prices and proof.</p>
        </CardContent>
      </Card>
    );
  }

  const important = rows.filter((row) => row.severity !== "routine");
  const routine = rows.filter((row) => row.severity === "routine");

  return (
    <div className="space-y-4">
      <BrandSectionHeader title="Market changes" description="See what changed between scans and what it means for your copy." />
      {important.length === 0 && (
        <p className="rounded-xl border border-border bg-card p-4 text-sm text-muted-foreground">
          Nothing since the last scan touches your copy - only the routine changes below.
        </p>
      )}
      {important.map((event) => {
        const severity = SEVERITY[event.severity] ?? SEVERITY.routine;
        return (
          <div
            key={event.id}
            className={cn("rounded-xl border border-border border-l-2 bg-card p-4", severity.tone)}
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-sm font-medium">{event.headline}</p>
              <div className="flex items-center gap-2">
                {event.severity === "acts_on_copy" && (
                  <Badge variant="outline" className="text-amber-400">
                    {severity.label}
                  </Badge>
                )}
                <span className="text-xs text-muted-foreground">{when(event.created_at)}</span>
              </div>
            </div>
            {event.detail && (
              <ExpandableText text={event.detail} className="mt-2 text-muted-foreground" />
            )}
            {event.what_to_do && (
              <p className="mt-1.5 text-xs text-foreground/70">{event.what_to_do}</p>
            )}
          </div>
        );
      })}
      {/* Routine changes are kept - they are the record - but one line each
          and folded. Sixty of them printed as cards made the three that act
          on the copy the first screen of seven. */}
      {routine.length > 0 && (
        <Disclosure
          title={`${routine.length} routine change${routine.length === 1 ? "" : "s"} on the record`}
          summary="New claims and new names in the market that do not, on their own, change what your copy should say."
        >
          <ul className="divide-y divide-hairline">
            {routine.map((event) => (
              <li key={event.id} className="flex items-baseline gap-3 py-2 first:pt-0 last:pb-0">
                <div className="min-w-0 flex-1">
                  <p className="text-sm">{event.headline}</p>
                  {event.detail && (
                    <p className="truncate text-xs text-muted-foreground" title={event.detail}>
                      {event.detail}
                    </p>
                  )}
                </div>
                <span className="shrink-0 text-xs text-muted-foreground">{when(event.created_at)}</span>
              </li>
            ))}
          </ul>
        </Disclosure>
      )}
    </div>
  );
}
