"use client";

import Link from "next/link";
import { positioningSentence } from "./market/positioning-map";
import { ArrowRight, BookOpen, Compass, Files, Mail, Megaphone, Users } from "lucide-react";

import { BrandKnowledgeDialog } from "./brand-knowledge-dialog";
import { BrandSectionHeader } from "../brand-ui";
import { StatusBadge } from "@/components/status-badge";
import { StatFigure, StatTile } from "@/components/stat-tile";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api, nullIfMissing } from "@/lib/api-client";
import { timeAgo } from "@/lib/format";

/** What this business can prove, who it is up against, and what it has shipped.
 *
 * The three answers a person opening a brand actually wants, each linking to
 * the section that changes it. Everything on this page is read for this brand
 * alone - there is no account-wide version of any of it. */
import { PageData, usePageData, useRouteIds } from "@/lib/page-data";

export function BrandOverviewView() {
  const { brandId } = useRouteIds();
  const state = usePageData(async () => {

  const [documents, base, market, campaigns] = await Promise.all([
    api.listKnowledgeDocuments({ brandId }),
    api.getKnowledgeBase({ brandId }).catch(nullIfMissing),
    api.getMarket(brandId).catch(nullIfMissing),
    api.listBrandCampaigns(brandId),
  ]);
  return { documents, base, market, campaigns };
  }, [brandId]);

  return (
    <PageData state={state}>
      {({ documents, base, market, campaigns }) => {

  // The API already filtered by brand; the check stays so a stale or
  // unfiltered answer can never show another business's work here.
  const ours = campaigns.filter((campaign) => campaign.brand_id === brandId);
  const rivals = market?.rivals.filter((rival) => !rival.muted) ?? [];

  return (
    <div className="space-y-6">
      <BrandSectionHeader title="Overview" description="Your brand at a glance. Build your knowledge, understand your buyers and turn it into campaigns." />
      <div className="rise-stagger grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-4">
        {[
          { label: "Sources", value: documents.length, href: `/brands/${brandId}/knowledge`, hint: "Manage your material", icon: Files },
          { label: "Established facts", value: base?.total ?? "—", href: `/brands/${brandId}/knowledge/base`, hint: "Explore your evidence", icon: BookOpen },
          { label: "Audiences", value: market?.audience_segments ?? 0, href: `/brands/${brandId}/market?tab=audience`, hint: "Find your next buyers", icon: Users },
          { label: "Campaigns", value: ours.length, href: `/campaigns?brand=${brandId}`, hint: "See your work", icon: Megaphone },
        ].map(({ icon, ...item }) => <StatTile key={item.label} {...item} icon={icon} />)}
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-2 pb-1">
            <CardTitle className="flex items-center gap-3 text-base">
              <span className="icon-tile flex size-8 items-center justify-center rounded-lg">
                <BookOpen className="size-4" aria-hidden="true" />
              </span>
              Knowledge & evidence
            </CardTitle>
            <Link
              href={`/brands/${brandId}/knowledge/base`}
              className="inline-flex items-center gap-1 text-xs font-medium text-muted-foreground transition-colors hover:text-violet-200"
            >
              Knowledge base <ArrowRight className="size-3.5" aria-hidden="true" />
            </Link>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            {base === null ? (
              <p className="text-muted-foreground">
                Nothing compiled yet. Your material is prepared when you first run a campaign
                for this business and reused until its sources change.{" "}
                {documents.length === 0
                  ? "Add this brand's website first."
                  : `${documents.length} source${documents.length === 1 ? " is" : "s are"} waiting to be read.`}
              </p>
            ) : (
              <>
                <div className="grid grid-cols-3 gap-3 rounded-xl bg-black/20 p-4 ring-1 ring-white/[0.05]">
                  <StatFigure label="Facts established" value={base.total} />
                  <StatFigure label="Citable in copy" value={base.citable_total} />
                  <StatFigure label="Strong enough to lead" value={base.headline_total} />
                </div>
                <p className="text-muted-foreground">
                  Compiled v{base.version}
                  {base.compiled_at ? ` — ${timeAgo(base.compiled_at)}` : ""} from{" "}
                  {documents.length} source{documents.length === 1 ? "" : "s"}.
                </p>
                {base.open_questions.length > 0 && (
                  <p className="rounded-xl border border-amber-400/20 bg-amber-400/[0.05] px-3.5 py-2.5 text-amber-100/85">
                    {base.open_questions.length} question
                    {base.open_questions.length === 1 ? "" : "s"}{" "}
                    still unanswered &mdash; each is a sentence this brand&rsquo;s copy currently
                    cannot write.
                  </p>
                )}
              </>
            )}
            <div className="flex flex-wrap gap-2 pt-1">
              <Link
                href={`/brands/${brandId}/knowledge`}
                className={buttonVariants({ variant: "outline", size: "sm" })}
              >
                Manage sources
              </Link>
              {base !== null && <BrandKnowledgeDialog brandId={brandId} />}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-2 pb-1">
            <CardTitle className="flex items-center gap-3 text-base">
              <span className="icon-tile flex size-8 items-center justify-center rounded-lg">
                <Compass className="size-4" aria-hidden="true" />
              </span>
              Market intelligence
            </CardTitle>
            <Link
              href={`/brands/${brandId}/market`}
              className="inline-flex items-center gap-1 text-xs font-medium text-muted-foreground transition-colors hover:text-violet-200"
            >
              Market <ArrowRight className="size-3.5" aria-hidden="true" />
            </Link>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            {market?.positioning ? (
              <>
                <p>{positioningSentence(market.positioning)}</p>
                <div className="grid grid-cols-3 gap-3 rounded-xl bg-black/20 p-4 ring-1 ring-white/[0.05]">
                  <StatFigure label="Competitors" value={rivals.length} />
                  <StatFigure label="Proof waiting" value={market.pending_proof} />
                  <StatFigure label="Changes to act on" value={market.unseen_alerts} />
                </div>
                <p className="text-muted-foreground">
                  Last read {market.scanned_at ? timeAgo(market.scanned_at) : "—"}.
                </p>
              </>
            ) : (
              <p className="text-muted-foreground">
                {market?.note ??
                  "Nothing scanned yet. A scan finds who this buyer is really deciding between, reads their pages, and works out which of this brand's claims are its alone."}
              </p>
            )}
            <div className="flex flex-wrap items-center gap-2 pt-1">
              <Link
                href={`/brands/${brandId}/market`}
                className={buttonVariants({ variant: "outline", size: "sm" })}
              >
                {market?.positioning ? "Open the map" : "Scan this market"}
              </Link>
              {market !== null && market.pending_proof > 0 && (
                <Badge variant="default">
                  {market.pending_proof} proof point{market.pending_proof === 1 ? "" : "s"}{" "}
                  waiting for you
                </Badge>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="gap-0 py-0">
        <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-2 border-b py-4">
          <CardTitle className="flex items-center gap-3 text-base">
            <span className="icon-tile flex size-8 items-center justify-center rounded-lg">
              <Megaphone className="size-4" aria-hidden="true" />
            </span>
            Campaigns for this brand
          </CardTitle>
          <Link
            href={`/campaigns?brand=${brandId}`}
            className="inline-flex items-center gap-1 text-xs font-medium text-muted-foreground transition-colors hover:text-violet-200"
          >
            All {ours.length} <ArrowRight className="size-3.5" aria-hidden="true" />
          </Link>
        </CardHeader>
        <CardContent className="p-0">
          {ours.length === 0 ? (
            <p className="p-5 text-sm leading-relaxed text-muted-foreground">
              Nothing run for this brand yet. Its knowledge is compiled on the first run, and
              every campaign after that reuses it instead of paying to read the same pages again.
            </p>
          ) : (
            <div className="divide-y divide-hairline">
            {ours.slice(0, 5).map((campaign) => (
              <Link
                key={campaign.id}
                href={`/campaigns/${campaign.id}`}
                className="group/row flex items-center justify-between gap-4 px-5 py-3.5 transition-colors hover:bg-white/[0.03]"
              >
                <span className="hidden size-9 shrink-0 items-center justify-center rounded-xl border border-white/[0.07] bg-white/[0.03] text-violet-300 transition-colors group-hover/row:border-violet-400/30 sm:flex">
                  <Mail className="size-4" aria-hidden="true" />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium transition-colors group-hover/row:text-violet-100">{campaign.name}</p>
                  <p className="mt-0.5 truncate text-xs text-muted-foreground">{campaign.request}</p>
                </div>
                <div className="flex shrink-0 items-center gap-2 text-xs text-muted-foreground">
                  {campaign.last_run_status && <StatusBadge status={campaign.last_run_status} warning={campaign.last_run_needs_review} />}
                  {campaign.last_run_at && <span className="hidden sm:inline">{timeAgo(campaign.last_run_at)}</span>}
                </div>
              </Link>
            ))}
            </div>
          )}
        </CardContent>
      </Card>


    </div>
  );
      }}
    </PageData>
  );
}
