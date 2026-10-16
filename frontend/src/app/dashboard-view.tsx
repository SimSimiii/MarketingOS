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
  ChevronRight,
  CloudOff,
  Mail,
  MailCheck,
  PlayCircle,
  RotateCcw,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

import { NewCampaignDialog } from "@/app/campaigns/new-campaign-dialog";
import { EmptyState } from "@/components/empty-state";
import { Notice } from "@/components/notice";
import { GroupLabel, PageHeader } from "@/components/page-header";
import { StatTile } from "@/components/stat-tile";
import { StatusBadge } from "@/components/status-badge";
import { buttonVariants } from "@/components/ui/button";
import { api } from "@/lib/api-client";
import { LOCALE, formatAbsolute, formatDuration, timeAgo } from "@/lib/format";
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
      cta: "Open run",
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
    .filter((campaign) => campaign.last_run_status === "failed" || campaign.last_run_needs_review)
    .slice(0, 3);
  for (const campaign of failed) {
    tasks.push({
      key: `failed-${campaign.id}`,
      icon: RotateCcw,
      tone: "attention",
      title: <>{campaign.name} {campaign.last_run_needs_review ? "needs review" : "stopped"}</>,
      detail: campaign.last_run_needs_review
        ? "Drafts are available, but the last run needs review. Open it to see the remaining issues."
        : campaign.last_run_at
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
  live: "bg-violet-500/15 text-violet-200 ring-violet-400/30",
  attention: "bg-amber-400/10 text-amber-300 ring-amber-400/25",
  default: "bg-white/[0.04] text-muted-foreground ring-white/[0.08]",
};

/** "Good evening" - the page is rendered in the reader's browser, so this is
 * their clock, not a server's. */
function greeting(at: number): string {
  const hour = new Date(at).getHours();
  if (hour < 5) return "Working late";
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

const today = new Intl.DateTimeFormat(LOCALE, { weekday: "long", day: "numeric", month: "long" });

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
          <div className="space-y-10">
            <PageHeader
              eyebrow={today.format(loadedAt)}
              title={greeting(loadedAt)}
              documentTitle="Overview"
              description={
                firstVisit
                  ? "Three steps from your own material to emails worth sending."
                  : tasks.length > 0
                    ? `${tasks.length} thing${tasks.length === 1 ? "" : "s"} waiting on you, most urgent first.`
                    : "Everything is up to date. Start something new whenever you are ready."
              }
              actions={<>
                <Link href="/brands?new=1" className={buttonVariants({ variant: "outline" })}>
                  <Building2 aria-hidden="true" />
                  New brand
                </Link>
                <NewCampaignDialog />
              </>}
            />

            {(campaigns === null || brands === null) && (
              <Notice tone="warning" title="Some workspace data could not be loaded">
                Refresh to try again. Unavailable counts are shown as a dash.
              </Notice>
            )}

            {firstVisit ? (
              <section className="studio-hero rise overflow-hidden rounded-3xl p-6 sm:p-10">
                <div aria-hidden="true" className="bg-grid pointer-events-none absolute inset-0 -z-10" />
                <p className="mb-5 flex items-center gap-2 text-[0.6875rem] font-medium uppercase tracking-[0.2em] text-violet-300">
                  <Sparkles className="size-4" aria-hidden="true" /> Grounded in your business
                </p>
                <h2 className="max-w-2xl font-display text-[2.5rem] leading-[1.05] sm:text-[3.25rem]">
                  Your expertise.{" "}
                  <span className="text-gradient-accent italic">Ready for their inbox.</span>
                </h2>
                <ol className="rise-stagger mt-10 grid gap-4 md:grid-cols-3">
                  {STEPS.map(({ title, body, href, icon: Icon }, index) => (
                    <li key={title}>
                      <Link
                        href={href}
                        className={cn(
                          "group surface surface-interactive flex h-full flex-col gap-3 rounded-2xl p-5",
                          index === 0 && "shadow-[var(--shadow-surface),0_0_0_1px_oklch(0.7_0.16_293/40%),0_18px_40px_-20px_oklch(0.55_0.2_293/55%)]",
                        )}
                      >
                        <span className="flex items-center justify-between gap-3">
                          <span className="icon-tile flex size-9 items-center justify-center rounded-xl">
                            <Icon className="size-4" aria-hidden="true" />
                          </span>
                          <span className="font-display text-2xl text-muted-foreground/60 tabular-nums">
                            0{index + 1}
                          </span>
                        </span>
                        <span className="mt-2 text-[0.9375rem] font-semibold">{title}</span>
                        <span className="text-sm leading-relaxed text-muted-foreground">{body}</span>
                        {index === 0 && (
                          <span className="mt-auto inline-flex items-center gap-1.5 pt-3 text-sm font-medium text-violet-200">
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
              <>
                <div className="rise-stagger grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-4">
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
                    hint="From your brief to finished copy"
                    href="/campaigns"
                    icon={Mail}
                  />
                  <StatTile
                    label="With finished emails"
                    value={delivered ?? "—"}
                    hint="Read cold before you see them"
                    href="/campaigns"
                    icon={MailCheck}
                  />
                  <StatTile
                    label="Running now"
                    value={runningResult.status === "fulfilled" ? running.length : "—"}
                    hint={running.length > 0 ? "Follow them as they write" : "Runs, research and compilation"}
                    href="/live"
                    icon={AudioLines}
                  />
                </div>

                <div className="grid items-start gap-6 xl:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)]">
                  <section aria-labelledby="waiting-title" className="min-w-0 space-y-3">
                    <GroupLabel id="waiting-title" live={running.length > 0} count={tasks.length || undefined}>
                      Waiting on you
                    </GroupLabel>
                    {tasks.length === 0 ? (
                      <div className="surface flex items-center gap-4 rounded-2xl p-5">
                        <span className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-emerald-400/10 text-emerald-300 ring-1 ring-emerald-400/25">
                          <CheckCircle2 className="size-5" aria-hidden="true" />
                        </span>
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-semibold">All clear</p>
                          <p className="mt-0.5 text-xs text-muted-foreground">
                            No run in progress, nothing to review, nothing stopped.
                          </p>
                        </div>
                      </div>
                    ) : (
                      <ul className="surface rise-stagger divide-y divide-hairline overflow-hidden rounded-2xl">
                        {tasks.slice(0, 6).map((task) => (
                          <li key={task.key} className="min-w-0">
                            <Link
                              href={task.href}
                              className="group flex items-center gap-4 px-4 py-4 transition-colors hover:bg-white/[0.03] sm:px-5"
                            >
                              <span className={cn("flex size-10 shrink-0 items-center justify-center rounded-xl ring-1", TONE[task.tone])}>
                                {task.tone === "live" ? (
                                  <span className="live-dot" aria-hidden="true" />
                                ) : (
                                  <task.icon className="size-[1.125rem]" aria-hidden="true" />
                                )}
                              </span>
                              <span className="min-w-0 flex-1">
                                <span className="block truncate text-sm font-medium">{task.title}</span>
                                <span className="mt-0.5 line-clamp-2 block text-xs leading-relaxed text-muted-foreground">{task.detail}</span>
                              </span>
                              <span className="inline-flex shrink-0 items-center gap-1 text-xs font-medium text-muted-foreground transition-colors group-hover:text-violet-200">
                                <span className="hidden sm:inline">{task.cta}</span>
                                <ChevronRight className="size-4 transition-transform group-hover:translate-x-0.5" aria-hidden="true" />
                              </span>
                            </Link>
                          </li>
                        ))}
                      </ul>
                    )}
                    {tasks.length > 6 && (
                      <p className="px-1 text-xs text-muted-foreground">
                        And {tasks.length - 6} more - see{" "}
                        <Link href="/campaigns" className="text-violet-300 hover:underline">campaigns</Link> and{" "}
                        <Link href="/brands" className="text-violet-300 hover:underline">brands</Link>.
                      </p>
                    )}
                  </section>

                  <section aria-labelledby="recent-title" className="min-w-0 space-y-3">
                    <div className="flex items-center gap-4">
                      <div className="flex-1">
                        <GroupLabel id="recent-title">Recent campaigns</GroupLabel>
                      </div>
                      <Link
                        href="/campaigns"
                        className="inline-flex shrink-0 items-center gap-1 text-xs font-medium text-muted-foreground transition-colors hover:text-violet-200"
                      >
                        View all
                        <ArrowRight className="size-3.5" aria-hidden="true" />
                      </Link>
                    </div>
                    <div className="surface overflow-hidden rounded-2xl">
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
                        <ul className="divide-y divide-hairline">
                          {campaigns.slice(0, 6).map((campaign) => (
                            <li key={campaign.id}>
                              <Link
                                href={`/campaigns/${campaign.id}`}
                                className="group/row flex items-center gap-3.5 px-4 py-3.5 transition-colors hover:bg-white/[0.03] sm:px-5"
                              >
                                <span className="hidden size-9 shrink-0 items-center justify-center rounded-xl border border-white/[0.07] bg-white/[0.03] text-violet-300 transition-colors group-hover/row:border-violet-400/30 sm:flex">
                                  <Mail className="size-4" aria-hidden="true" />
                                </span>
                                <div className="min-w-0 flex-1">
                                  <p className="truncate text-sm font-medium transition-colors group-hover/row:text-violet-100">{campaign.name}</p>
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
                                {campaign.last_run_status ? (
                                  <StatusBadge status={campaign.last_run_status} warning={campaign.last_run_needs_review} />
                                ) : (
                                  <span className="text-[0.6875rem] text-muted-foreground">Draft</span>
                                )}
                              </Link>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  </section>
                </div>
              </>
            )}
          </div>
        );
      }}
    </PageData>
  );
}
