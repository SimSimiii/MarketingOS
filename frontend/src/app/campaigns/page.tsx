import Link from "next/link";

import { NewCampaignDialog } from "@/app/campaigns/new-campaign-dialog";
import { PageHeader } from "@/components/page-header";
import { CampaignActions } from "@/components/campaign-actions";
import { StatusBadge } from "@/components/status-badge";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { api } from "@/lib/api-client";
import { formatAbsolute, timeAgo } from "@/lib/format";

export default async function CampaignsPage({
  searchParams,
}: {
  searchParams: Promise<{ archived?: string; brand?: string }>;
}) {
  const { archived, brand: brandId } = await searchParams;
  const includeArchived = archived === "1";
  const [all, brands] = await Promise.all([
    api.listCampaigns(includeArchived),
    api.listBrands().catch(() => []),
  ]);
  // A campaign belongs to a business, so this list can be read as one
  // business's work rather than as everything the account has ever run.
  const brand = brands.find((item) => item.id === brandId) ?? null;
  const campaigns = brand ? all.filter((item) => item.brand_id === brand.id) : all;
  const brandNames = new Map(brands.map((item) => [item.id, item.name]));

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Email studio"
        title={`Campaigns${brand ? ` — ${brand.name}` : ""}`}
        description={brand ? "Everything this business has asked for, written from its own knowledge base." : "From the first brief to the final email. Manage your work here."}
        actions={<>
          {brand && (
            <Link
              href={`/campaigns${includeArchived ? "?archived=1" : ""}`}
              className="text-sm text-muted-foreground hover:text-foreground hover:underline"
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
            className="text-sm text-muted-foreground hover:text-foreground hover:underline"
          >
            {includeArchived ? "Hide archived" : "Show archived"}
          </Link>
          <NewCampaignDialog />
        </>}
      />

      <Card>
        <CardContent className="p-0">
          {campaigns.length === 0 ? (
            <div className="space-y-3 p-10 text-center">
              <p className="text-sm font-medium">
                {includeArchived ? "Nothing here yet." : "No campaigns yet."}
              </p>
              <p className="mx-auto max-w-md text-sm text-muted-foreground">
                Describe your product once, then ask in your own words — “write me 3 emails that
                make people buy”. You get finished copy, reviewed for conversion before you see it.
              </p>
              <div className="flex justify-center pt-1">
                <NewCampaignDialog />
              </div>
            </div>
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
                          className="font-medium text-violet-300 hover:underline"
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
                    <TableCell data-label="Brief" className="max-w-md truncate text-muted-foreground">
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
    </div>
  );
}
