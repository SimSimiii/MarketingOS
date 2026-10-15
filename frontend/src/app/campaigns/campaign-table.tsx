"use client";

import { useMemo, useState, type ReactNode } from "react";
import Link from "next/link";
import { Search, SearchX } from "lucide-react";

import { CampaignActions } from "@/components/campaign-actions";
import { EmptyState } from "@/components/empty-state";
import { StatusBadge } from "@/components/status-badge";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatAbsolute, timeAgo } from "@/lib/format";
import type { Campaign } from "@/lib/types";
import { cn } from "@/lib/utils";

type Filter = "all" | "completed" | "failed" | "never";

const FILTERS: { value: Filter; label: string; matches: (campaign: Campaign) => boolean }[] = [
  { value: "all", label: "All", matches: () => true },
  { value: "completed", label: "Completed", matches: (c) => c.last_run_status === "completed" && !c.last_run_needs_review },
  {
    value: "failed",
    label: "Needs attention",
    matches: (c) => c.last_run_needs_review === true || c.last_run_status === "failed" || c.last_run_status === "cancelled",
  },
  { value: "never", label: "Never run", matches: (c) => c.last_run_status === null },
];

/**
 * The campaigns on this page, with the two questions a list this long gets
 * asked: "where is the one about X" and "which ones went wrong".
 *
 * Filtering is over the page already loaded rather than the API: the list is
 * paged at fifty, and nobody who has fewer than fifty campaigns - everybody,
 * today - should wait on a round trip to narrow what is already on screen.
 */
export function CampaignTable({
  campaigns,
  brandNames,
  empty,
  paged,
}: {
  campaigns: Campaign[];
  brandNames: Map<string, string>;
  /** What to show when there are no campaigns at all. */
  empty: ReactNode;
  /** More than this page exists, so a filter only covers what is loaded. */
  paged: boolean;
}) {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<Filter>("all");

  const counts = useMemo(
    () => new Map(FILTERS.map((option) => [option.value, campaigns.filter(option.matches).length])),
    [campaigns],
  );
  const visible = useMemo(() => {
    const needle = query.trim().toLocaleLowerCase();
    const matches = FILTERS.find((option) => option.value === filter)?.matches ?? (() => true);
    return campaigns.filter((campaign) => {
      if (!matches(campaign)) return false;
      if (!needle) return true;
      const brand = campaign.brand_id ? brandNames.get(campaign.brand_id) ?? "" : "";
      return `${campaign.name} ${campaign.request} ${brand}`.toLocaleLowerCase().includes(needle);
    });
  }, [campaigns, brandNames, query, filter]);

  if (campaigns.length === 0) {
    return (
      <Card className="gap-0 py-0">
        <CardContent className="p-0">{empty}</CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-3 rounded-xl border border-border bg-card p-3">
        <div className="relative min-w-48 flex-1">
          <Search
            className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
            aria-hidden="true"
          />
          <Input
            type="search"
            aria-label="Search campaigns"
            placeholder={paged ? "Search this page by name, brief or brand…" : "Search by name, brief or brand…"}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            className="h-9 pl-9"
          />
        </div>
        <div role="group" aria-label="Filter by last run" className="flex flex-wrap gap-1.5">
          {FILTERS.map((option) => {
            const count = counts.get(option.value) ?? 0;
            if (option.value !== "all" && count === 0) return null;
            return (
              <button
                key={option.value}
                type="button"
                aria-pressed={filter === option.value}
                onClick={() => setFilter(option.value)}
                className={cn(
                  buttonVariants({ variant: filter === option.value ? "secondary" : "ghost", size: "sm" }),
                  filter === option.value && "ring-1 ring-violet-400/40",
                )}
              >
                {option.label}
                <span className="tabular-nums text-muted-foreground">{count}</span>
              </button>
            );
          })}
        </div>
      </div>

      <Card className="gap-0 py-0">
        <CardContent className="p-0">
          {visible.length === 0 ? (
            <EmptyState
              variant="inline"
              icon={SearchX}
              title="No matching campaigns"
              description="Nothing here answers to that search and filter together."
              action={
                <button
                  type="button"
                  className={buttonVariants({ variant: "outline", size: "sm" })}
                  onClick={() => {
                    setQuery("");
                    setFilter("all");
                  }}
                >
                  Clear filters
                </button>
              }
            />
          ) : (
            <Table className="campaign-table">
              <TableHeader>
                <TableRow>
                  <TableHead>Campaign</TableHead>
                  <TableHead>Brand</TableHead>
                  <TableHead>Last run</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead className="w-10">
                    <span className="sr-only">Actions</span>
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {visible.map((campaign) => (
                  <TableRow key={campaign.id} className="group/row relative">
                    {/* The brief under the name rather than in a column of its
                        own: truncated to a column it was a sentence cut at
                        the fifth word, and it took the width the actions
                        needed. Under the name it is the subtitle it is. */}
                    <TableCell className="max-w-0 whitespace-normal md:w-[55%]">
                      <div className="flex min-w-0 items-center gap-2">
                        <Link
                          href={`/campaigns/${campaign.id}`}
                          className="truncate font-medium text-foreground underline-offset-4 after:absolute after:inset-0 hover:text-violet-200 hover:underline focus-visible:outline-2 focus-visible:outline-ring"
                        >
                          {campaign.name}
                        </Link>
                        {campaign.status === "archived" && (
                          <Badge variant="secondary">archived</Badge>
                        )}
                      </div>
                      <p
                        className="mt-0.5 truncate text-xs text-muted-foreground"
                        title={campaign.request}
                      >
                        {campaign.request}
                      </p>
                    </TableCell>
                    <TableCell data-label="Brand" className="text-muted-foreground">
                      {campaign.brand_id ? (
                        <Link
                          href={`/brands/${campaign.brand_id}`}
                          className="relative z-10 hover:text-foreground hover:underline"
                        >
                          {brandNames.get(campaign.brand_id) ?? "Unknown brand"}
                        </Link>
                      ) : (
                        <span title="Knowledge for this run was read once, then kept to the campaign">
                          One-off
                        </span>
                      )}
                    </TableCell>
                    <TableCell data-label="Last run">
                      {campaign.last_run_status ? (
                        <span
                          className="flex items-center gap-2"
                          title={
                            campaign.last_run_at ? formatAbsolute(campaign.last_run_at) : undefined
                          }
                        >
                          <StatusBadge status={campaign.last_run_status} warning={campaign.last_run_needs_review} />
                          {campaign.last_run_at && (
                            <span className="text-xs text-muted-foreground">
                              {timeAgo(campaign.last_run_at)}
                            </span>
                          )}
                        </span>
                      ) : (
                        <span className="text-sm text-muted-foreground">Never run</span>
                      )}
                    </TableCell>
                    <TableCell
                      data-label="Created"
                      className="text-muted-foreground"
                      title={formatAbsolute(campaign.created_at)}
                    >
                      {timeAgo(campaign.created_at)}
                    </TableCell>
                    <TableCell className="relative z-10 text-right">
                      <CampaignActions campaign={campaign} />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
      {(query || filter !== "all") && visible.length > 0 && (
        <p role="status" className="text-xs text-muted-foreground">
          {visible.length} of {campaigns.length} campaigns{paged ? " on this page" : ""}
        </p>
      )}
    </div>
  );
}
