"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { ArrowRight, ExternalLink, MailCheck, PlayCircle, Quote } from "lucide-react";

import { StartCampaignButton } from "@/app/campaigns/[id]/start-campaign-button";
import { EditBriefDialog } from "@/app/campaigns/[id]/edit-brief-dialog";
import { NewCampaignDialog } from "@/app/campaigns/new-campaign-dialog";
import { CampaignActions } from "@/components/campaign-actions";
import { EmptyState } from "@/components/empty-state";
import { Notice } from "@/components/notice";
import { PageHeader } from "@/components/page-header";
import { CampaignPolicySelect } from "@/components/campaign-policy-select";
import { ExecutionRowActions } from "@/components/execution-row-actions";
import { adviceHeadline } from "@/components/run-launcher";
import { StatusBadge } from "@/components/status-badge";
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
import { ApiError, api } from "@/lib/api-client";
import { formatAbsolute, timeAgo } from "@/lib/format";
import { PageData, notFound, usePageData, useRouteIds } from "@/lib/page-data";

export function CampaignDetailView() {
  const { campaignId: id } = useRouteIds();
  const state = usePageData(async () => {

  const campaign = await api.getCampaign(id).catch((error) => {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  });
  if (!campaign) {
    notFound();
  }

  const [executions, campaignKnowledge, brandKnowledge, generationAdvice] = await Promise.all([
    api.listCampaignExecutions(id),
    api.listKnowledgeDocuments({ campaignId: id }),
    campaign.brand_id
      ? api.listKnowledgeDocuments({ brandId: campaign.brand_id })
      : Promise.resolve([]),
    api.getCampaignGenerationAdvice(id).catch(() => null),
  ]);
  return { campaign, executions, campaignKnowledge, brandKnowledge, generationAdvice };
  }, [id]);

  return (
    <PageData state={state}>
      {({ campaign, executions, campaignKnowledge, brandKnowledge, generationAdvice }) => {

  const knowledge = [...campaignKnowledge, ...brandKnowledge];
  // Runs arrive newest first. The one a returning reader wants is the newest
  // that produced something - or the one still going.
  const live = executions.find((run) => run.status === "running" || run.status === "pending");
  const latest = executions.find((run) => run.status === "completed");

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Campaign"
        title={campaign.name}
        description={campaign.product_description}
        backTo={{ href: "/campaigns", label: "Campaigns" }}
        actions={<>
          <CampaignActions campaign={campaign} redirectOnDeleteTo="/campaigns" />
          {executions.length === 0 && <EditBriefDialog key={campaign.updated_at} campaign={campaign} />}
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
          <StartCampaignButton campaignId={campaign.id} advice={generationAdvice} hasActiveRun={Boolean(live)} />
        </>}
      />

      {generationAdvice?.recommendation && (
        <Notice
          tone={generationAdvice.override_required ? "warning" : "info"}
          title={<span className="flex flex-wrap items-baseline gap-2">
            <span className="capitalize">{adviceHeadline(generationAdvice).state}</span>
            {adviceHeadline(generationAdvice).readiness && (
              <span className="text-xs font-normal opacity-70">
                {adviceHeadline(generationAdvice).readiness}
              </span>
            )}
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

      {(live ?? latest) && (
        <Link
          href={`/campaigns/${campaign.id}/executions/${(live ?? latest)!.id}`}
          className="group rise ring-gradient surface-interactive flex flex-wrap items-center gap-4 overflow-hidden rounded-2xl bg-[linear-gradient(100deg,oklch(0.55_0.2_293/16%),oklch(0.55_0.2_293/4%)_60%,transparent)] p-4 shadow-[var(--shadow-surface)] sm:p-5"
        >
          <span className="brand-mark flex size-11 shrink-0 items-center justify-center rounded-xl text-white">
            {live ? (
              <span className="live-dot !bg-white" aria-hidden="true" />
            ) : (
              <MailCheck className="size-5" aria-hidden="true" />
            )}
          </span>
          <span className="min-w-0 flex-1 basis-56">
            <span className="block text-[0.9375rem] font-semibold">
              {live ? "A run is in progress" : (latest?.needs_review || latest?.error_message) ? "Your latest run needs review" : "Your latest drafts are ready for review"}
            </span>
            <span className="mt-0.5 block text-xs text-muted-foreground">
              {live
                ? `Started ${live.started_at ? timeAgo(live.started_at) : "just now"} — open the run and refresh to see its progress.`
                : `Finished ${latest!.completed_at ? timeAgo(latest!.completed_at) : ""} — ${(latest!.needs_review || latest!.error_message) ? "review the stop reason and any delivered drafts." : "read the drafts and review them before use."}`}
            </span>
          </span>
          <span className="inline-flex w-full items-center justify-center gap-2 rounded-full bg-white/[0.06] px-3.5 py-1.5 text-sm font-medium text-violet-100 ring-1 ring-white/10 transition-colors group-hover:bg-white/[0.1] sm:w-auto">
            {live ? "Open the run" : "Open the emails"}
            <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" aria-hidden="true" />
          </span>
        </Link>
      )}

      {/* The brief is what every other panel on this page is downstream of, so
          it is quoted rather than filed in a card the same size as "Website". */}
      <section className="studio-hero relative overflow-hidden rounded-3xl p-6 sm:p-9">
        {/* The quotation mark as an ornament, set in the display face so the
            brief reads as something the reader said rather than a form field. */}
        <span
          aria-hidden="true"
          className="pointer-events-none absolute -top-6 right-6 font-display text-[11rem] leading-none text-violet-400/10 select-none sm:right-10"
        >
          &rdquo;
        </span>
        <p className="mb-4 flex items-center gap-2 text-[0.6875rem] font-medium uppercase tracking-[0.2em] text-violet-300">
          <Quote className="size-3.5" aria-hidden="true" /> What you asked for
        </p>
        <p className="relative max-w-3xl whitespace-pre-line text-[1.0625rem] leading-[1.75] text-foreground/95 sm:text-lg">{campaign.request}</p>
        {executions.length > 0 && <p className="relative mt-5 border-t border-white/[0.07] pt-4 text-xs leading-relaxed text-muted-foreground">To change this brief, choose Duplicate in the campaign menu. Previous runs keep their original campaign context.</p>}
      </section>

      {/* Four short answers about one campaign, in one panel. As four cards
          they took a screenful apiece and claimed the same weight as the brief
          above and the runs below, neither of which is a one-line fact. */}
      {/* Runs sit under the facts rather than below the whole grid: the preset
          column is tall, and beside a two-line fact panel it left a screen of
          empty space above the one table this page exists to show. */}
      <div className="grid grid-cols-1 items-start gap-4 lg:grid-cols-[minmax(0,1fr)_18rem]">
        <div className="min-w-0 space-y-4">
        <dl className="surface grid gap-x-6 gap-y-5 rounded-2xl p-5 sm:grid-cols-3 sm:p-6">
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
        <Card className="gap-0 py-0">
          <CardHeader className="border-b p-5 sm:px-6">
            <CardTitle className="flex items-center gap-2.5">
              Runs
              {executions.length > 0 && (
                <span className="rounded-full bg-white/[0.06] px-2 py-px text-[0.6875rem] font-medium tabular-nums text-muted-foreground">
                  {executions.length}
                </span>
              )}
            </CardTitle>
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
                  Run the campaign to prepare your material and generate drafts for review.
                </>}
              />
            ) : (
              <Table className="stacked-table">
                <TableHeader>
                  <TableRow>
                    <TableHead>Status</TableHead>
                    <TableHead>Started</TableHead>
                    <TableHead>Completed</TableHead>
                    <TableHead />
                    <TableHead />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {executions.map((execution, index) => (
                    <TableRow key={execution.id} className="relative">
                      <TableCell>
                        <span className="flex flex-wrap items-center gap-2">
                          <span className="flex size-7 items-center justify-center rounded-lg bg-white/[0.04] text-[0.6875rem] font-medium text-muted-foreground tabular-nums ring-1 ring-white/[0.06]">
                            {executions.length - index}
                          </span>
                          <StatusBadge status={execution.status} warning={execution.needs_review || (execution.status === "completed" && Boolean(execution.error_message))} />
                          {/* Once per run it is a note, not an alarm - an amber
                              badge on every row turned the table orange. */}
                          {execution.generated_despite_recommendation && (
                            <span
                              className="text-xs text-amber-300/80"
                              title="Run with “Generate anyway”, against the recommendation"
                            >
                              overridden
                            </span>
                          )}
                        </span>
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
                      <TableCell className="relative z-10">
                        <ExecutionRowActions execution={execution} campaignId={campaign.id} />
                      </TableCell>
                      <TableCell className="text-right">
                        <Link
                          href={`/campaigns/${campaign.id}/executions/${execution.id}`}
                          className="inline-flex items-center gap-1 text-sm font-medium text-violet-300 after:absolute after:inset-0 hover:text-violet-200"
                        >
                          Open
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
        <div className="surface rounded-2xl p-5 lg:sticky lg:top-6">
          <p className="mb-3 text-[0.6875rem] font-medium uppercase tracking-[0.16em] text-muted-foreground">
            Execution preset
          </p>
          <CampaignPolicySelect campaign={campaign} />
        </div>
      </div>

    </div>
  );
      }}
    </PageData>
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
      <dt className="text-[0.6875rem] font-medium uppercase tracking-[0.16em] text-muted-foreground">
        {label}
      </dt>
      <dd className="mt-1.5 text-sm leading-relaxed">{children}</dd>
      {hint && <dd className="mt-0.5 text-xs text-muted-foreground">{hint}</dd>}
    </div>
  );
}
