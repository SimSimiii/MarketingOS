import type { ReactNode } from "react";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowRight, ExternalLink, PlayCircle, Quote } from "lucide-react";

import { StartCampaignButton } from "@/app/campaigns/[id]/start-campaign-button";
import { NewCampaignDialog } from "@/app/campaigns/new-campaign-dialog";
import { CampaignActions } from "@/components/campaign-actions";
import { EmptyState } from "@/components/empty-state";
import { Notice } from "@/components/notice";
import { PageHeader } from "@/components/page-header";
import { CampaignPolicySelect } from "@/components/campaign-policy-select";
import { ExecutionRowActions } from "@/components/execution-row-actions";
import { StatusBadge } from "@/components/status-badge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { api } from "@/lib/api-server";
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

  const [executions, campaignKnowledge, brandKnowledge, generationAdvice] = await Promise.all([
    api.listCampaignExecutions(id),
    api.listKnowledgeDocuments({ campaignId: id }).catch(() => []),
    campaign.brand_id
      ? api.listKnowledgeDocuments({ brandId: campaign.brand_id }).catch(() => [])
      : Promise.resolve([]),
    api.getCampaignGenerationAdvice(id).catch(() => null),
  ]);
  const knowledge = [...campaignKnowledge, ...brandKnowledge];

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Campaign"
        title={campaign.name}
        description={campaign.product_description}
        backTo={{ href: "/campaigns", label: "Campaigns" }}
        actions={<>
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
          <StartCampaignButton campaignId={campaign.id} advice={generationAdvice} />
        </>}
      />

      {generationAdvice?.recommendation && (
        <Notice
          tone={generationAdvice.override_required ? "warning" : "info"}
          title={<span className="flex flex-wrap items-baseline gap-2">
            <span className="capitalize">
              {generationAdvice.recommendation.state.replaceAll("_", " ")}
            </span>
            <span className="text-xs font-normal opacity-70">
              {generationAdvice.readiness.replaceAll("_", " ")}
            </span>
          </span>}
        >
          <p>{generationAdvice.user_message}</p>
          {generationAdvice.reasons.length > 0 && (
            <ul className="mt-1.5 space-y-1 text-xs opacity-80">
              {generationAdvice.reasons.map((reason) => (
                <li key={reason}>— {reason}</li>
              ))}
            </ul>
          )}
          {generationAdvice.override_required && (
            <p className="mt-1.5 text-xs opacity-80">
              Running is still available. “Generate anyway” records this recommendation and
              your explicit override with the execution.
            </p>
          )}
        </Notice>
      )}

      {/* The brief is what every other panel on this page is downstream of, so
          it is quoted rather than filed in a card the same size as "Website". */}
      <section className="studio-hero relative overflow-hidden rounded-2xl border border-violet-400/15 p-6 sm:p-7">
        <p className="mb-3 flex items-center gap-2 text-[10px] font-medium uppercase tracking-[0.18em] text-violet-300">
          <Quote className="size-3.5" aria-hidden="true" /> What you asked for
        </p>
        <p className="max-w-3xl text-lg leading-relaxed">{campaign.request}</p>
      </section>

      {/* Four short answers about one campaign, in one panel. As four cards
          they took a screenful apiece and claimed the same weight as the brief
          above and the runs below, neither of which is a one-line fact. */}
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_18rem]">
        <dl className="grid gap-x-6 gap-y-5 self-start rounded-xl border border-border bg-card p-5 sm:grid-cols-3">
          <Fact label="Website">
            {campaign.product_url ? (
              <a
                href={campaign.product_url}
                target="_blank"
                rel="noreferrer noopener"
                className="inline-flex max-w-full items-center gap-1 text-violet-300 hover:underline"
              >
                <span className="truncate">
                  {campaign.product_url.replace(/^https?:\/\//, "").replace(/\/$/, "")}
                </span>
                <ExternalLink className="size-3 shrink-0" aria-hidden="true" />
              </a>
            ) : (
              <span className="text-muted-foreground">Not set</span>
            )}
          </Fact>
          {/* One field for one question, matching the form: a campaign either
              names a segment somebody mapped or describes its buyer in the
              user's own words, and showing only the second reads as "no
              audience" for every campaign that used the first. */}
          <Fact
            label="Audience"
            hint={campaign.audience_segment ? "from this brand's audience map" : undefined}
          >
            {campaign.audience_segment ?? campaign.target_market ?? (
              <span className="text-muted-foreground">Not set</span>
            )}
          </Fact>
          <Fact label="Product knowledge">
            {knowledge.length === 0 ? (
              <span className="text-muted-foreground">None attached</span>
            ) : (
              `${knowledge.length} source${knowledge.length === 1 ? "" : "s"} read`
            )}
          </Fact>
        </dl>
        <div className="rounded-xl border border-border bg-card p-5">
          <p className="mb-2.5 text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Execution preset
          </p>
          <CampaignPolicySelect campaign={campaign} />
        </div>
      </div>

      <Card className="gap-0 py-0">
        <CardHeader className="border-b p-5">
          <CardTitle>Runs</CardTitle>
          <CardDescription>
            Every time this brief was sent through the pipeline, and what it produced.
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {executions.length === 0 ? (
            <EmptyState
              variant="inline"
              icon={PlayCircle}
              title="Nothing produced yet"
              description={<>
                Hit &ldquo;Run campaign&rdquo; and the Marketing Director will research, write and
                review your material.
              </>}
            />
          ) : (
            <Table className="stacked-table">
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
                      {execution.generated_despite_recommendation && (
                        <Badge variant="outline" className="ml-2 border-amber-500/50 text-amber-300">
                          recommendation overridden
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell
                      data-label="Started"
                      className="text-muted-foreground"
                      title={
                        execution.started_at ? formatAbsolute(execution.started_at) : undefined
                      }
                    >
                      {execution.started_at ? timeAgo(execution.started_at) : "—"}
                    </TableCell>
                    <TableCell
                      data-label="Completed"
                      className="text-muted-foreground"
                      title={
                        execution.completed_at ? formatAbsolute(execution.completed_at) : undefined
                      }
                    >
                      {execution.completed_at ? timeAgo(execution.completed_at) : "—"}
                    </TableCell>
                    <TableCell data-label="Cost" className="text-muted-foreground tabular-nums">
                      {formatCost(execution.estimated_cost_usd)}
                    </TableCell>
                    <TableCell>
                      <ExecutionRowActions execution={execution} campaignId={campaign.id} />
                    </TableCell>
                    <TableCell>
                      <Link
                        href={`/campaigns/${campaign.id}/executions/${execution.id}`}
                        className="inline-flex items-center gap-1 text-sm font-medium text-violet-300 hover:underline"
                      >
                        View material
                        <ArrowRight className="size-3.5" aria-hidden="true" />
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

/** One labelled answer in the campaign's fact panel. */
function Fact({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <div className="min-w-0">
      <dt className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
        {label}
      </dt>
      <dd className="mt-1.5 text-sm leading-relaxed">{children}</dd>
      {hint && <dd className="mt-0.5 text-xs text-muted-foreground">{hint}</dd>}
    </div>
  );
}
