import Link from "next/link";
import { Archive, ChevronLeft, ChevronRight, Mail } from "lucide-react";

import { NewCampaignDialog } from "@/app/campaigns/new-campaign-dialog";
import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";
import { CampaignActions } from "@/components/campaign-actions";
import { StatusBadge } from "@/components/status-badge";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { api } from "@/lib/api-server";
import { formatAbsolute, timeAgo } from "@/lib/format";

export default async function CampaignsPage({
  searchParams,
}: {
  searchParams: Promise<{
    archived?: string;
    page?: string;
    brand?: string;
    linkedin_name?: string;
    linkedin_url?: string;
    linkedin_headline?: string;
  }>;
}) {
  const {
    archived,
    page: requestedPage,
    brand: brandId,
    linkedin_name: linkedinName,
    linkedin_url: linkedinUrl,
    linkedin_headline: linkedinHeadline,
  } = await searchParams;
  const includeArchived = archived === "1";
  const page = Math.max(1, Math.min(100000, Number.parseInt(requestedPage ?? "1", 10) || 1));
  const pageSize = 50;
  const [all, brands] = await Promise.all([
    api.listCampaigns(includeArchived, { limit: pageSize + 1, offset: (page - 1) * pageSize, brandId }),
    api.listBrands().catch(() => []),
  ]);
  // A campaign belongs to a business, so this list can be read as one
  // business's work rather than as everything the account has ever run.
  const brand = brands.find((item) => item.id === brandId) ?? null;
  const campaigns = all.slice(0, pageSize);
  const pageHref = (target: number) => {
    const query = new URLSearchParams({ page: String(target) });
    if (includeArchived) query.set("archived", "1");
    if (brandId) query.set("brand", brandId);
    return `/campaigns?${query}`;
  };
  const brandNames = new Map(brands.map((item) => [item.id, item.name]));
  //: Arriving from a LinkedIn search result: the campaign form opens on the
  //: profile they just read, so the one thing they would have retyped is
  //: already in it. A recipient without a brand is not a campaign this
  //: product can plan, so the brand has to come along too.
  const linkedinPrefill =
    brandId && linkedinUrl
      ? {
          brandId,
          linkedinName: linkedinName ?? "",
          linkedinUrl,
          linkedinHeadline: linkedinHeadline ?? "",
        }
      : undefined;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Email studio"
        title={`Campaigns${brand ? ` — ${brand.name}` : ""}`}
        description={brand ? "Everything this business has asked for, written from its own knowledge base." : "From the first brief to the final email. Manage your work here."}
        backTo={brand ? { href: `/brands/${brand.id}`, label: brand.name } : undefined}
        actions={<>
          {brand && (
            <Link
              href={`/campaigns${includeArchived ? "?archived=1" : ""}`}
              className={buttonVariants({ variant: "ghost", size: "sm" })}
            >
              All brands
            </Link>
          )}
          <Link
            href={
              includeArchived
                ? `/campaigns${brand ? `?brand=${brand.id}` : ""}`
                : `/campaigns?${brand ? `brand=${brand.id}&` : ""}archived=1`
            }
            aria-pressed={includeArchived}
            className={buttonVariants({ variant: includeArchived ? "secondary" : "outline", size: "sm" })}
          >
            <Archive className="size-3.5" aria-hidden="true" />
            {includeArchived ? "Hide archived" : "Show archived"}
          </Link>
          <NewCampaignDialog prefill={linkedinPrefill} autoOpen={Boolean(linkedinPrefill)} />
        </>}
      />

      <Card className="gap-0 py-0">
        <CardContent className="p-0">
          {campaigns.length === 0 ? (
            <EmptyState
              variant="inline"
              icon={Mail}
              title={includeArchived ? "Nothing here yet" : "No campaigns yet"}
              description={<>
                Describe your product once, then ask in your own words — “write me 3 emails
                that make people buy”. You get finished copy, reviewed for conversion before you
                see it.
              </>}
              action={<NewCampaignDialog />}
            />
          ) : (
            <Table className="campaign-table">
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Brand</TableHead>
                  <TableHead>What was asked</TableHead>
                  <TableHead>Last run</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead><span className="sr-only">Actions</span></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {campaigns.map((campaign) => (
                  <TableRow key={campaign.id}>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Link
                          href={`/campaigns/${campaign.id}`}
                          className="font-medium text-violet-300 underline-offset-4 hover:underline"
                        >
                          {campaign.name}
                        </Link>
                        {campaign.status === "archived" && (
                          <Badge variant="secondary">archived</Badge>
                        )}
                      </div>
                    </TableCell>
                    <TableCell data-label="Brand" className="text-muted-foreground">
                      {campaign.brand_id ? (
                        <Link
                          href={`/brands/${campaign.brand_id}`}
                          className="hover:text-foreground hover:underline"
                        >
                          {brandNames.get(campaign.brand_id) ?? "Unknown brand"}
                        </Link>
                      ) : (
                        <span title="Knowledge for this run was read once, then kept to the campaign">
                          One-off
                        </span>
                      )}
                    </TableCell>
                    <TableCell data-label="Brief" className="max-w-xs truncate text-muted-foreground lg:max-w-sm">
                      {campaign.request}
                    </TableCell>
                    <TableCell data-label="Last run">
                      {campaign.last_run_status ? (
                        <span
                          className="flex items-center gap-2"
                          title={
                            campaign.last_run_at ? formatAbsolute(campaign.last_run_at) : undefined
                          }
                        >
                          <StatusBadge status={campaign.last_run_status} />
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
                    <TableCell>
                      <CampaignActions campaign={campaign} />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
      {(page > 1 || all.length > pageSize) && (
        <nav
          aria-label="Campaign pages"
          className="flex items-center justify-between gap-3 text-sm"
        >
          {page > 1 ? (
            <Link href={pageHref(page - 1)} className={buttonVariants({ variant: "outline", size: "sm" })}>
              <ChevronLeft className="size-3.5" aria-hidden="true" />
              Previous
            </Link>
          ) : (
            <span />
          )}
          <span className="text-xs text-muted-foreground tabular-nums">Page {page}</span>
          {all.length > pageSize ? (
            <Link href={pageHref(page + 1)} className={buttonVariants({ variant: "outline", size: "sm" })}>
              Next
              <ChevronRight className="size-3.5" aria-hidden="true" />
            </Link>
          ) : (
            <span />
          )}
        </nav>
      )}
    </div>
  );
}
