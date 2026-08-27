import Link from "next/link";
import { notFound } from "next/navigation";

import { StartCampaignButton } from "@/app/campaigns/[id]/start-campaign-button";
import { NewCampaignDialog } from "@/app/campaigns/new-campaign-dialog";
import { CampaignActions } from "@/components/campaign-actions";
import { CampaignPolicySelect } from "@/components/campaign-policy-select";
import { ExecutionRowActions } from "@/components/execution-row-actions";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { api } from "@/lib/api-client";
import { formatAbsolute, formatCost, timeAgo } from "@/lib/format";

export default async function CampaignDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  const campaign = await api.getCampaign(id).catch(() => null);
  if (!campaign) {
    notFound();
  }

  const [executions, campaignKnowledge, brandKnowledge] = await Promise.all([
    api.listCampaignExecutions(id),
    api.listKnowledgeDocuments({ campaignId: id }).catch(() => []),
    campaign.brand_id
      ? api.listKnowledgeDocuments({ brandId: campaign.brand_id }).catch(() => [])
      : Promise.resolve([]),
  ]);
  const knowledge = [...campaignKnowledge, ...brandKnowledge];

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{campaign.name}</h1>
          <p className="mt-1 text-sm text-muted-foreground">{campaign.product_description}</p>
        </div>
        <div className="flex items-center gap-2">
          <CampaignActions campaign={campaign} redirectOnDeleteTo="/campaigns" />
          {campaign.brand_id && (
            <NewCampaignDialog
              trigger={<Button variant="outline">Generate another type</Button>}
              prefill={{
                brandId: campaign.brand_id,
                productDescription: campaign.product_description,
                productUrl: campaign.product_url,
                targetMarket: campaign.target_market,
                goals: campaign.goals,
                senderName: campaign.sender_name,
                senderRole: campaign.sender_role,
              }}
            />
          )}
          <StartCampaignButton campaignId={campaign.id} />
        </div>
      </div>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            What you asked for
          </CardTitle>
        </CardHeader>
        <CardContent className="text-base">{campaign.request}</CardContent>
      </Card>

      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Website</CardTitle>
          </CardHeader>
          <CardContent className="truncate text-sm">
            {campaign.product_url ? (
              <a
                href={campaign.product_url}
                target="_blank"
                rel="noreferrer noopener"
                className="text-primary hover:underline"
              >
                {campaign.product_url}
              </a>
            ) : (
              "—"
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Audience</CardTitle>
          </CardHeader>
          {/* One card for one question, matching the form: a campaign either
              names a segment somebody mapped or describes its buyer in the
              user's own words, and showing only the second reads as "no
              audience" for every campaign that used the first. */}
          <CardContent className="space-y-1 text-sm">
            {campaign.audience_segment ? (
              <>
                <p>{campaign.audience_segment}</p>
                <p className="text-xs text-muted-foreground">
                  from this brand&rsquo;s audience map
                </p>
              </>
            ) : (
              (campaign.target_market ?? "—")
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Product knowledge
            </CardTitle>
          </CardHeader>
          <CardContent className="text-sm">
            {knowledge.length === 0
              ? "None attached"
              : `${knowledge.length} source${knowledge.length === 1 ? "" : "s"} read`}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Execution preset
          </CardTitle>
        </CardHeader>
        <CardContent>
          <CampaignPolicySelect campaign={campaign} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Runs</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {executions.length === 0 ? (
            <p className="p-6 text-sm text-muted-foreground">
              Nothing produced yet. Hit &ldquo;Run campaign&rdquo; and the Marketing Director will
              research, write and review your material.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Status</TableHead>
                  <TableHead>Started</TableHead>
                  <TableHead>Completed</TableHead>
                  <TableHead>Cost</TableHead>
                  <TableHead />
                  <TableHead />
                </TableRow>
              </TableHeader>
              <TableBody>
                {executions.map((execution) => (
                  <TableRow key={execution.id}>
                    <TableCell>
                      <StatusBadge status={execution.status} />
                    </TableCell>
                    <TableCell
                      className="text-muted-foreground"
                      title={
                        execution.started_at ? formatAbsolute(execution.started_at) : undefined
                      }
                    >
                      {execution.started_at ? timeAgo(execution.started_at) : "—"}
                    </TableCell>
                    <TableCell
                      className="text-muted-foreground"
                      title={
                        execution.completed_at ? formatAbsolute(execution.completed_at) : undefined
                      }
                    >
                      {execution.completed_at ? timeAgo(execution.completed_at) : "—"}
                    </TableCell>
                    <TableCell className="text-muted-foreground tabular-nums">
                      {formatCost(execution.estimated_cost_usd)}
                    </TableCell>
                    <TableCell>
                      <ExecutionRowActions execution={execution} campaignId={campaign.id} />
                    </TableCell>
                    <TableCell>
                      <Link
                        href={`/campaigns/${campaign.id}/executions/${execution.id}`}
                        className="text-sm text-primary hover:underline"
                      >
                        View material
                      </Link>
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
