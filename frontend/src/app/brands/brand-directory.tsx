"use client";

import Link from "next/link";
import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { ArrowUpRight, BellRing, Building2, Megaphone, SearchX } from "lucide-react";
import type { BrandOverview } from "@/lib/types";

import { NewBrandDialog } from "@/app/brands/new-brand-dialog";
import { BrandMonogram } from "@/components/brand-monogram";
import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";
import { StatFigure, StatTile } from "@/components/stat-tile";
import { FilterPills, SearchField, Toolbar } from "@/components/toolbar";
import { buttonVariants } from "@/components/ui/button";
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
  const arrivedToCreate = useSearchParams().get("new") === "1";
  const visible = brands.filter((brand) => `${brand.name} ${brand.website_url ?? ""}`.toLowerCase().includes(query.trim().toLowerCase()) && (!attention || brand.unseen_alerts > 0 || brand.pending_proof > 0));
  const needingAttention = brands.filter((brand) => brand.unseen_alerts > 0 || brand.pending_proof > 0).length;

  return (
    <div className="space-y-8">
      <PageHeader eyebrow="Your businesses" title="Brand workspaces" description="The knowledge, market context and proof behind every campaign. A dedicated home for each business." actions={<NewBrandDialog primary autoOpen={arrivedToCreate} />} />

      <div className="rise-stagger grid grid-cols-2 gap-3 sm:grid-cols-3 sm:gap-4 [&>:nth-child(3)]:col-span-2 sm:[&>:nth-child(3)]:col-span-1">
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
      {brands.length > 0 && (
        <Toolbar>
          <SearchField label="Search brands" placeholder="Search by brand or website…" value={query} onChange={setQuery} />
          <FilterPills
            label="Filter brands"
            value={attention ? "review" : "all"}
            onChange={(value) => setAttention(value === "review")}
            options={[
              { value: "all", label: "All", count: brands.length },
              { value: "review", label: "Needs review", count: needingAttention },
            ]}
          />
        </Toolbar>
      )}
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
          action={<NewBrandDialog primary />}
        />
      ) : (
        <div className="rise-stagger grid gap-5 lg:grid-cols-2">
          {visible.map((brand) => (
            <article
              key={brand.id}
              className="group/brand surface surface-interactive relative isolate flex flex-col overflow-hidden rounded-2xl"
            >
              <span
                aria-hidden="true"
                className="pointer-events-none absolute -top-24 -right-24 -z-10 size-64 rounded-full bg-violet-500/10 opacity-60 blur-3xl transition-opacity duration-300 group-hover/brand:opacity-100"
              />
              <div className="flex items-start gap-4 p-5 pb-4 sm:p-6 sm:pb-5">
                <BrandMonogram name={brand.name} />
                <div className="min-w-0 flex-1">
                  <h2 className="text-lg leading-snug font-semibold tracking-tight">
                    {/* The whole card is the target; the name is the link a
                        screen reader announces. */}
                    <Link
                      href={`/brands/${brand.id}`}
                      className="after:absolute after:inset-0 after:z-0 focus-visible:outline-none focus-visible:after:rounded-2xl focus-visible:after:ring-2 focus-visible:after:ring-ring"
                    >
                      {brand.name}
                    </Link>
                  </h2>
                  {brand.website_url ? (
                    <p className="mt-0.5 truncate text-sm text-muted-foreground">
                      {brand.website_url.replace(/^https?:\/\//, "").replace(/\/$/, "")}
                    </p>
                  ) : (
                    <p className="mt-0.5 text-sm text-muted-foreground/70">No website yet</p>
                  )}
                </div>
                <div className="flex shrink-0 flex-wrap justify-end gap-1.5">
                  {brand.unseen_alerts > 0 && (
                    <span className="rounded-full bg-amber-400/10 px-2 py-0.5 text-[0.6875rem] font-medium text-amber-200 ring-1 ring-amber-400/25">
                      {brand.unseen_alerts} to act on
                    </span>
                  )}
                  {brand.pending_proof > 0 && (
                    <span className="rounded-full bg-violet-500/15 px-2 py-0.5 text-[0.6875rem] font-medium text-violet-200 ring-1 ring-violet-400/25">
                      {brand.pending_proof} proof waiting
                    </span>
                  )}
                  <ArrowUpRight
                    className="size-4 text-muted-foreground transition-all group-hover/brand:translate-x-0.5 group-hover/brand:-translate-y-0.5 group-hover/brand:text-violet-200"
                    aria-hidden="true"
                  />
                </div>
              </div>
              <dl className="mx-5 grid grid-cols-2 gap-4 rounded-xl bg-black/20 p-4 ring-1 ring-white/[0.05] sm:mx-6 sm:grid-cols-4">
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
              {/* Above the card-wide link, so each one goes where it says. */}
              <div className="relative z-10 mt-auto flex flex-wrap gap-2 p-5 pt-4 sm:px-6 sm:pb-6">
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
                <Link
                  href={`/campaigns?brand=${brand.id}`}
                  className={buttonVariants({ variant: "ghost", size: "sm" })}
                >
                  Campaigns
                </Link>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
