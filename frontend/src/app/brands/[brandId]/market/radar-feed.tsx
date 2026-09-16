"use client";

import { useEffect, useState } from "react";

import { BrandSectionHeader } from "../../brand-ui";
import { ExpandableText } from "@/components/expandable-text";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { api } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import type { RadarEvent, RadarSeverity } from "@/lib/types";

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
  return date.toLocaleDateString();
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

  return (
    <div className="space-y-4">
      <BrandSectionHeader title="Market changes" description="See what changed between scans and what it means for your copy." />
      {rows.map((event) => {
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
    </div>
  );
}
