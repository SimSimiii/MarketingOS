import Link from "next/link";

import { NewCampaignDialog } from "@/app/campaigns/new-campaign-dialog";
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
  searchParams: Promise<{ archived?: string }>;
}) {
  const { archived } = await searchParams;
  const includeArchived = archived === "1";
  const campaigns = await api.listCampaigns(includeArchived);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Campaigns</h1>
          <p className="text-sm text-muted-foreground">
            Describe your product, say what you need, get material you can send.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link
            href={includeArchived ? "/campaigns" : "/campaigns?archived=1"}
            className="text-sm text-muted-foreground hover:text-foreground hover:underline"
          >
            {includeArchived ? "Hide archived" : "Show archived"}
          </Link>
          <NewCampaignDialog />
        </div>
      </div>

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
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>What was asked</TableHead>
                  <TableHead>Last run</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead />
                </TableRow>
              </TableHeader>
              <TableBody>
                {campaigns.map((campaign) => (
                  <TableRow key={campaign.id}>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Link
                          href={`/campaigns/${campaign.id}`}
                          className="font-medium text-primary hover:underline"
                        >
                          {campaign.name}
                        </Link>
                        {campaign.status === "archived" && (
                          <Badge variant="secondary">archived</Badge>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="max-w-md truncate text-muted-foreground">
                      {campaign.request}
                    </TableCell>
                    <TableCell>
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
