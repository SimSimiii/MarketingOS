"use client";

import type { ComponentType, ReactNode } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  ArrowRight,
  AudioLines,
  BookOpen,
  Building2,
  CheckCircle2,
  CloudOff,
  Mail,
  PlayCircle,
  RotateCcw,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

import { NewCampaignDialog } from "@/app/campaigns/new-campaign-dialog";
import { EmptyState } from "@/components/empty-state";
import { Notice } from "@/components/notice";
import { PageHeader } from "@/components/page-header";
import { StatTile } from "@/components/stat-tile";
import { StatusBadge } from "@/components/status-badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api-client";
import { formatAbsolute, formatDuration, timeAgo } from "@/lib/format";
import { PageData, usePageData } from "@/lib/page-data";
import type { BrandOverview, Campaign, RunningExecution } from "@/lib/types";
import { cn } from "@/lib/utils";

const STEPS = [
  { title: "Give it the facts", body: "Register your business and add your website, documents and product details.", href: "/brands", icon: Building2 },
  { title: "Set the direction", body: "Describe who you are writing to and what the emails should achieve.", href: "/campaigns", icon: Mail },
  { title: "Make it yours", body: "Read the finished emails, copy them, and send from the tool you already use.", href: "/campaigns", icon: Sparkles },
];

/** One thing on the overview that is waiting on the reader. */
interface Task {
  key: string;
  icon: ComponentType<{ className?: string }>;
  tone: "live" | "attention" | "default";
  title: ReactNode;
  detail: ReactNode;
  href: string;
  cta: string;
}

/**
 * What needs the reader, most urgent first.
 *
 * The overview used to open on a brochure - "Your expertise. Ready for their
 * inbox." - above three counts, which is a page written for a first visit and
 * shown on every visit after it. A returning reader opens the overview to
 * find out what changed and what is waiting; this answers that from data the
 * page already loads, and falls back to the first-visit steps only when there
 * is nothing yet to act on.
 */
function tasksFrom(
  running: RunningExecution[],
  campaigns: Campaign[],
  brands: BrandOverview[],
  now: number,
): Task[] {
  const tasks: Task[] = [];
  for (const run of running) {
    tasks.push({
      key: `run-${run.id}`,
      icon: AudioLines,
      tone: "live",
      title: <>Writing <span className="text-violet-200">{run.campaign_name}</span></>,
      detail: run.started_at
        ? `Running for ${formatDuration(now - new Date(run.started_at).getTime())}`
        : "Starting",
      href: `/campaigns/${run.campaign_id}/executions/${run.id}`,
      cta: "Watch",
    });
  }
  for (const brand of brands) {
    const waiting = brand.pending_proof + brand.unseen_alerts;
    if (waiting > 0) {
      tasks.push({
        key: `brand-${brand.id}`,
        icon: ShieldCheck,
        tone: "attention",
        title: <>{brand.name}: {waiting} item{waiting === 1 ? "" : "s"} to review</>,
        detail: [
          brand.pending_proof > 0 && `${brand.pending_proof} proof point${brand.pending_proof === 1 ? "" : "s"} found`,
          brand.unseen_alerts > 0 && `${brand.unseen_alerts} market change${brand.unseen_alerts === 1 ? "" : "s"}`,
        ].filter(Boolean).join(" · ") + " - approved proof is what the copy may quote.",
        href: `/brands/${brand.id}/market`,
        cta: "Review",
      });
    }
    if (brand.sources === 0) {
      tasks.push({
        key: `sources-${brand.id}`,
        icon: BookOpen,
        tone: "default",
        title: <>{brand.name} has no sources yet</>,
        detail: "Every email is written only from what you give it. Add the website or a document first.",
        href: `/brands/${brand.id}/knowledge`,
        cta: "Add sources",
      });
    }
  }
  const failed = campaigns
    .filter((campaign) => campaign.last_run_status === "failed")
    .slice(0, 3);
  for (const campaign of failed) {
    tasks.push({
      key: `failed-${campaign.id}`,
      icon: RotateCcw,
      tone: "attention",
      title: <>{campaign.name} stopped</>,
      detail: campaign.last_run_at
        ? `Stopped ${timeAgo(campaign.last_run_at)} - open it to see why, or run it again.`
        : "Open it to see why, or run it again.",
      href: `/campaigns/${campaign.id}`,
      cta: "Open",
    });
  }
  const neverRun = campaigns.filter((campaign) => campaign.last_run_status === null).slice(0, 2);
  for (const campaign of neverRun) {
    tasks.push({
      key: `never-${campaign.id}`,
      icon: PlayCircle,
      tone: "default",
      title: <>{campaign.name} has never run</>,
      detail: "The brief is written. See what a run will cost, then start it.",
      href: `/campaigns/${campaign.id}`,
      cta: "Open",
    });
  }
  return tasks;
}

const TONE: Record<Task["tone"], string> = {
  live: "border-violet-400/30 bg-violet-500/[0.08] text-violet-300",
  attention: "border-amber-400/25 bg-amber-400/[0.06] text-amber-300",
  default: "border-border bg-background/40 text-muted-foreground",
};

export function DashboardView() {
  const state = usePageData(async () => {
    const [campaignResult, brandResult, runningResult] = await Promise.allSettled([
      api.listCampaigns(),
      api.listBrandOverviews(),
      api.listRunningExecutions(),
    ]);
    return { campaignResult, brandResult, runningResult, loadedAt: Date.now() };
  }, []);

  return (
    <PageData state={state}>
      {({ campaignResult, brandResult, runningResult, loadedAt }) => {
        const campaigns = campaignResult.status === "fulfilled" ? campaignResult.value : null;
        const brands = brandResult.status === "fulfilled" ? brandResult.value : null;
        const running = runningResult.status === "fulfilled" ? runningResult.value : [];
        const brandNames = new Map((brands ?? []).map((brand) => [brand.id, brand.name]));
        const waiting = brands?.reduce(
          (total, brand) => total + brand.pending_proof + brand.unseen_alerts,
          0,
        );
        const delivered = campaigns?.filter((campaign) => campaign.last_run_status === "completed").length;
        const tasks = tasksFrom(running, campaigns ?? [], brands ?? [], loadedAt);
        const firstVisit = brands !== null && brands.length === 0;

        return (
          <div className="space-y-8">
            <PageHeader
              eyebrow="Your email studio"
              title="Overview"
              description={
                firstVisit
                  ? "Three steps from your own material to emails worth sending."
                  : tasks.length > 0
                    ? `${tasks.length} thing${tasks.length === 1 ? "" : "s"} waiting on you, most urgent first.`
                    : "Everything is up to date. Start something new whenever you are ready."
              }
              actions={<NewCampaignDialog />}
            />

            {(campaigns === null || brands === null) && (
              <Notice tone="warning" title="Some workspace data could not be loaded">
                Refresh to try again. Unavailable counts are shown as a dash.
              </Notice>
            )}

            {firstVisit ? (
              <section className="studio-hero overflow-hidden rounded-2xl border border-violet-400/15 p-6 sm:p-8">
                <p className="mb-4 flex items-center gap-2 text-xs font-medium uppercase tracking-[0.16em] text-violet-300">
                  <Sparkles className="size-4" aria-hidden="true" /> Grounded in your business
                </p>
                <h2 className="max-w-xl text-2xl font-medium leading-tight tracking-tight sm:text-3xl">
                  Your expertise.{" "}
                  <span className="text-muted-foreground">Ready for their inbox.</span>
                </h2>
                <ol className="mt-8 grid gap-4 md:grid-cols-3">
                  {STEPS.map(({ title, body, href, icon: Icon }, index) => (
                    <li key={title}>
                      <Link
                        href={href}
                        className={cn(
                          "group flex h-full flex-col gap-3 rounded-xl border p-5 transition-colors",
                          index === 0
                            ? "border-violet-400/40 bg-violet-500/10 hover:bg-violet-500/15"
                            : "border-border bg-background/40 hover:border-violet-400/30",
                        )}
                      >
                        <span className="flex items-center gap-3">
                          <span className="flex size-8 items-center justify-center rounded-lg border border-border text-violet-300">
                            <Icon className="size-4" aria-hidden="true" />
                          </span>
                          <span className="text-xs text-muted-foreground tabular-nums">Step {index + 1}</span>
                        </span>
                        <span className="text-sm font-medium">{title}</span>
                        <span className="text-xs leading-relaxed text-muted-foreground">{body}</span>
                        {index === 0 && (
                          <span className="mt-auto inline-flex items-center gap-1.5 pt-2 text-sm font-medium text-violet-200">
                            Register your business
                            <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" aria-hidden="true" />
                          </span>
                        )}
                      </Link>
                    </li>
                  ))}
                </ol>
              </section>
            ) : (
              <section aria-labelledby="waiting-title" className="space-y-3">
                <h2 id="waiting-title" className="text-xs font-medium uppercase tracking-widest text-muted-foreground">
                  Waiting on you
                </h2>
                {tasks.length === 0 ? (
                  <div className="flex items-center gap-4 rounded-xl border border-emerald-400/20 bg-emerald-400/[0.05] p-5">
                    <span className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-emerald-400/10 text-emerald-300">
                      <CheckCircle2 className="size-5" aria-hidden="true" />
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium">All clear</p>
                      <p className="mt-0.5 text-xs text-muted-foreground">
                        No run in progress, nothing to review, nothing stopped.
                      </p>
                    </div>
                  </div>
                ) : (
                  <ul className="rise-stagger grid gap-3 lg:grid-cols-2">
                    {tasks.slice(0, 6).map((task) => (
                      <li key={task.key} className="min-w-0">
                        <Link
                          href={task.href}
                          className="group flex h-full items-start gap-4 rounded-xl border border-border bg-card p-4 transition-colors hover:border-violet-400/35 hover:bg-accent/15"
                        >
                          <span className={cn("flex size-9 shrink-0 items-center justify-center rounded-lg border", TONE[task.tone])}>
                            {task.tone === "live" ? (
                              <span className="size-2 rounded-full bg-violet-400 motion-safe:animate-pulse" aria-hidden="true" />
                            ) : (
                              <task.icon className="size-4" aria-hidden="true" />
                            )}
                          </span>
                          <span className="min-w-0 flex-1">
                            <span className="block truncate text-sm font-medium">{task.title}</span>
                            <span className="mt-1 block text-xs leading-relaxed text-muted-foreground">{task.detail}</span>
                          </span>
                          <span className="inline-flex shrink-0 items-center gap-1 self-center text-xs font-medium text-violet-300">
                            <span className="hidden sm:inline">{task.cta}</span>
                            <ArrowRight className="size-3.5 transition-transform group-hover:translate-x-0.5" aria-hidden="true" />
                          </span>
                        </Link>
                      </li>
                    ))}
                  </ul>
                )}
                {tasks.length > 6 && (
                  <p className="text-xs text-muted-foreground">
                    And {tasks.length - 6} more - see{" "}
                    <Link href="/campaigns" className="text-violet-300 hover:underline">campaigns</Link> and{" "}
                    <Link href="/brands" className="text-violet-300 hover:underline">brands</Link>.
                  </p>
                )}
              </section>
            )}

            <div className="rise-stagger grid gap-4 sm:grid-cols-3">
              <StatTile
                label="Brand workspaces"
                value={brands?.length ?? "—"}
                hint={waiting ? `${waiting} item${waiting === 1 ? "" : "s"} to review` : "Knowledge, positioning and proof"}
                href="/brands"
                icon={waiting ? AlertTriangle : Building2}
                tone={waiting ? "attention" : "default"}
              />
              <StatTile
                label="Campaigns"
                value={campaigns?.length ?? "—"}
                hint={delivered !== undefined ? `${delivered} with finished emails` : "From your brief to finished copy"}
                href="/campaigns"
                icon={Mail}
              />
              <StatTile
                label="Running now"
                value={runningResult.status === "fulfilled" ? running.length : "—"}
                hint={running.length > 0 ? "Follow them as they write" : "Runs, research and compilation"}
                href="/live"
                icon={AudioLines}
              />
            </div>

            <Card className="gap-0 py-0">
              <CardHeader className="flex flex-row items-center justify-between border-b p-5">
                <CardTitle>Recent campaigns</CardTitle>
                <Link href="/campaigns" className="flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground">
                  View all<ArrowRight className="size-3.5" aria-hidden="true" />
                </Link>
              </CardHeader>
              <CardContent className="p-0">
                {campaigns === null ? (
                  <EmptyState
                    variant="inline"
                    icon={CloudOff}
                    title="Campaigns are temporarily unavailable"
                    description="The API did not answer. Nothing has been lost — reload the page to try again."
                  />
                ) : campaigns.length === 0 ? (
                  <EmptyState
                    variant="inline"
                    icon={Mail}
                    title="Your next campaign starts here"
                    description="Start with a simple brief. A welcome sequence, a product launch, a reason to come back."
                    action={<NewCampaignDialog />}
                  />
                ) : (
                  <div className="divide-y divide-border">
                    {campaigns.slice(0, 5).map((campaign) => (
                      <Link
                        key={campaign.id}
                        href={`/campaigns/${campaign.id}`}
                        className="group/row flex items-center gap-4 p-4 transition-colors hover:bg-accent/20 sm:px-5"
                      >
                        <span className="hidden size-9 shrink-0 items-center justify-center rounded-lg border border-border bg-background/40 text-violet-300 sm:flex">
                          <Mail className="size-4" aria-hidden="true" />
                        </span>
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-medium">{campaign.name}</p>
                          <p className="mt-0.5 truncate text-xs text-muted-foreground">
                            <span className="text-foreground/70">
                              {campaign.brand_id ? brandNames.get(campaign.brand_id) ?? "Brand" : "One-off"}
                            </span>
                            {" · "}
                            <span title={formatAbsolute(campaign.last_run_at ?? campaign.created_at)}>
                              {campaign.last_run_at
                                ? `ran ${timeAgo(campaign.last_run_at)}`
                                : `created ${timeAgo(campaign.created_at)}`}
                            </span>
                          </p>
                        </div>
                        {campaign.last_run_status && <StatusBadge status={campaign.last_run_status} />}
                        <ArrowRight
                          className="size-4 shrink-0 text-muted-foreground transition-transform group-hover/row:translate-x-0.5 group-hover/row:text-violet-300"
                          aria-hidden="true"
                        />
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
