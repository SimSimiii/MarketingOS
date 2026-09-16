"use client";

import Link from "next/link";
import { useState } from "react";
import { BellRing, Building2, Megaphone, Search, SearchX } from "lucide-react";
import { Input } from "@/components/ui/input";
import type { BrandOverview } from "@/lib/types";

import { NewBrandDialog } from "@/app/brands/new-brand-dialog";
import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";
import { StatFigure, StatTile } from "@/components/stat-tile";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { timeAgo } from "@/lib/format";

/** The businesses this account works for.
 *
 * The entry point to everything scoped to one of them: its sources, its
 * compiled knowledge base, its market. None of those are account-wide - two
 * businesses have different competitors, different proof and different gaps,
 * and a page that averages them describes nobody.
 */
export function BrandDirectory({ brands }: { brands: BrandOverview[] }) {
  const [query, setQuery] = useState("");
  const [attention, setAttention] = useState(false);
  const visible = brands.filter((brand) => `${brand.name} ${brand.website_url ?? ""}`.toLowerCase().includes(query.trim().toLowerCase()) && (!attention || brand.unseen_alerts > 0 || brand.pending_proof > 0));
  const needingAttention = brands.filter((brand) => brand.unseen_alerts > 0 || brand.pending_proof > 0).length;

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Your businesses" title="Brand workspaces" description="The knowledge, market context and proof behind every campaign. A dedicated home for each business." actions={<NewBrandDialog />} />

      <div className="rise-stagger grid gap-3 sm:grid-cols-3">
        <StatTile label="Workspaces" value={brands.length} icon={Building2} hint="Businesses you write for" />
        <StatTile
          label="Campaigns"
          value={brands.reduce((sum, brand) => sum + brand.campaigns, 0)}
          icon={Megaphone}
          hint="Written across every brand"
        />
        <StatTile
          label="Need review"
          value={needingAttention}
          icon={BellRing}
          tone={needingAttention > 0 ? "attention" : "default"}
          hint={needingAttention > 0 ? "Alerts and proof waiting on you" : "Nothing waiting"}
        />
      </div>
      {brands.length > 0 && <div className="flex flex-wrap items-center gap-3 rounded-xl border border-border bg-card p-3">
        <div className="relative min-w-48 flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
          <Input aria-label="Search brands" placeholder="Search by brand or website…" value={query} onChange={(event) => setQuery(event.target.value)} className="h-9 pl-9" />
        </div>
        <button type="button" aria-pressed={attention} onClick={() => setAttention(!attention)} className={buttonVariants({ variant: attention ? "default" : "outline", size: "sm" })}>Needs review · {needingAttention}</button>
        <span role="status" className="text-xs text-muted-foreground">{visible.length} of {brands.length} brands</span>
      </div>}
      {brands.length > 0 && visible.length === 0 && (
        <EmptyState
          icon={SearchX}
          title="No matching brands"
          description="Nothing here answers to that search and filter together."
          action={
            <button
              type="button"
              className={buttonVariants({ variant: "outline", size: "sm" })}
              onClick={() => { setQuery(""); setAttention(false); }}
            >
              Clear filters
            </button>
          }
        />
      )}
      {brands.length === 0 ? (
        <EmptyState
          icon={Building2}
          title="Register your first business"
          description={<>
            Create a workspace to keep your sources, audiences and market research together —
            every campaign for this brand reuses that knowledge. A one-off campaign can still run
            without one; it just keeps everything it learns to itself.
          </>}
          action={<NewBrandDialog />}
        />
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {visible.map((brand) => (
            <Card key={brand.id} className="transition-all hover:ring-violet-400/40 hover:ring-2">
              <CardHeader className="studio-hero pb-3">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <CardTitle className="flex items-center gap-2 text-lg">
                      <Building2 className="size-5 shrink-0 text-violet-300" /><Link href={`/brands/${brand.id}`} className="hover:underline">
                        {brand.name}
                      </Link>
                    </CardTitle>
                    {brand.website_url && (
                      <p className="truncate text-sm text-muted-foreground">
                        {brand.website_url}
                      </p>
                    )}
                  </div>
                  <div className="flex shrink-0 gap-1">
                    {brand.unseen_alerts > 0 && (
                      <Badge variant="default">{brand.unseen_alerts} to act on</Badge>
                    )}
                    {brand.pending_proof > 0 && (
                      <Badge variant="outline">{brand.pending_proof} proof waiting</Badge>
                    )}
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <dl className="grid grid-cols-2 gap-4 rounded-xl border border-hairline bg-background/40 p-4 text-sm sm:grid-cols-4">
                  <StatFigure label="Sources" value={brand.sources} />
                  <StatFigure
                    label="Knowledge"
                    value={brand.knowledge_version ? `v${brand.knowledge_version}` : "—"}
                    hint={
                      brand.compiled_at
                        ? `compiled ${timeAgo(brand.compiled_at)}`
                        : "compiles on the first run"
                    }
                  />
                  <StatFigure
                    label="Competitors"
                    value={brand.rivals}
                    hint={brand.scanned_at ? `scanned ${timeAgo(brand.scanned_at)}` : "never scanned"}
                  />
                  <StatFigure label="Campaigns" value={brand.campaigns} />
                </dl>
                <div className="flex flex-wrap gap-2">
                  <Link
                    href={`/brands/${brand.id}`}
                    className={buttonVariants({ size: "sm" })}
                  >
                    Open workspace
                  </Link>
                  <Link
                    href={`/brands/${brand.id}/knowledge/base`}
                    className={buttonVariants({ variant: "outline", size: "sm" })}
                  >
                    Knowledge base
                  </Link>
                  <Link
                    href={`/brands/${brand.id}/market`}
                    className={buttonVariants({ variant: "outline", size: "sm" })}
                  >
                    Market
                  </Link>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
