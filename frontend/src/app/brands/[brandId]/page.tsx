import Link from "next/link";
import { BookOpen, Files, Megaphone, Users } from "lucide-react";

import { BrandKnowledgeDialog } from "./brand-knowledge-dialog";
import { BrandSectionHeader } from "../brand-ui";
import { ExpandableText } from "@/components/expandable-text";
import { StatusBadge } from "@/components/status-badge";
import { StatFigure, StatTile } from "@/components/stat-tile";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api-server";
import { timeAgo } from "@/lib/format";

/** What this business can prove, who it is up against, and what it has shipped.
 *
 * The three answers a person opening a brand actually wants, each linking to
 * the section that changes it. Everything on this page is read for this brand
 * alone - there is no account-wide version of any of it. */
export default async function BrandOverviewPage({
  params,
}: {
  params: Promise<{ brandId: string }>;
}) {
  const { brandId } = await params;

  const [documents, base, market, campaigns] = await Promise.all([
    api.listKnowledgeDocuments({ brandId }).catch(() => []),
    api.getKnowledgeBase({ brandId }).catch(() => null),
    api.getMarket(brandId).catch(() => null),
    api.listCampaigns().catch(() => []),
  ]);
  const ours = campaigns.filter((campaign) => campaign.brand_id === brandId);
  const rivals = market?.rivals.filter((rival) => !rival.muted) ?? [];

  return (
    <div className="space-y-6">
      <BrandSectionHeader title="Overview" description="Your brand at a glance. Build your knowledge, understand your buyers and turn it into campaigns." />
      <div className="rise-stagger grid grid-cols-2 gap-3 xl:grid-cols-4">
        {[
          { label: "Sources", value: documents.length, href: `/brands/${brandId}/knowledge`, hint: "Manage your material", icon: Files },
          { label: "Established facts", value: base?.total ?? "—", href: `/brands/${brandId}/knowledge/base`, hint: "Explore your evidence", icon: BookOpen },
          { label: "Audiences", value: market?.audience_segments ?? 0, href: `/brands/${brandId}/market?tab=audience`, hint: "Find your next buyers", icon: Users },
          { label: "Campaigns", value: ours.length, href: `/campaigns?brand=${brandId}`, hint: "See your work", icon: Megaphone },
        ].map(({ icon, ...item }) => <StatTile key={item.label} {...item} icon={icon} />)}
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-2 pb-3">
            <CardTitle className="text-base">Knowledge & evidence</CardTitle>
            <Link
              href={`/brands/${brandId}/knowledge/base`}
              className="text-sm text-primary hover:underline"
            >
              Knowledge base
            </Link>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            {base === null ? (
              <p className="text-muted-foreground">
                Nothing compiled yet. Knowledge is compiled on the first campaign run for this
                business &mdash; reading the material costs a model call, so it is not paid for
                until something needs it.{" "}
                {documents.length === 0
                  ? "Add this brand's website first."
                  : `${documents.length} source${documents.length === 1 ? " is" : "s are"} waiting to be read.`}
              </p>
            ) : (
              <>
                <div className="grid grid-cols-3 gap-3 rounded-xl border border-hairline bg-background/40 p-4">
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
                  <p className="text-amber-300">
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
          <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-2 pb-3">
            <CardTitle className="text-base">Market intelligence</CardTitle>
            <Link
              href={`/brands/${brandId}/market`}
              className="text-sm text-primary hover:underline"
            >
              Market
            </Link>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            {market?.positioning ? (
              <>
                <ExpandableText text={market.positioning.summary} />
                <div className="grid grid-cols-3 gap-3 rounded-xl border border-hairline bg-background/40 p-4">
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

      <Card>
        <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-2 pb-3">
          <CardTitle className="text-base">Campaigns for this brand</CardTitle>
          <Link
            href={`/campaigns?brand=${brandId}`}
            className="text-sm text-primary hover:underline"
          >
            All {ours.length}
          </Link>
        </CardHeader>
        <CardContent className="space-y-2">
          {ours.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Nothing run for this brand yet. Its knowledge is compiled on the first run, and
              every campaign after that reuses it instead of paying to read the same pages again.
            </p>
          ) : (
            ours.slice(0, 5).map((campaign) => (
              <Link
                key={campaign.id}
                href={`/campaigns/${campaign.id}`}
                className="flex items-center justify-between gap-3 rounded-lg border border-border px-4 py-3 transition-colors hover:border-violet-400/30 hover:bg-accent/30"
              >
                <div className="min-w-0">
                  <p className="font-medium">{campaign.name}</p>
                  <p className="truncate text-sm text-muted-foreground">{campaign.request}</p>
                </div>
                <div className="flex shrink-0 items-center gap-2 text-xs text-muted-foreground">
                  {campaign.last_run_status && <StatusBadge status={campaign.last_run_status} />}
                  {campaign.last_run_at && <span>{timeAgo(campaign.last_run_at)}</span>}
                </div>
              </Link>
            ))
          )}
        </CardContent>
      </Card>


    </div>
  );
}
