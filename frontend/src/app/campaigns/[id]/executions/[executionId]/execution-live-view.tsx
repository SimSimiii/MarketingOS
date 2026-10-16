"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { CheckCircle2, Mail, RefreshCw, TriangleAlert } from "lucide-react";
import { toast } from "sonner";

import { AnswerQuestionsCard } from "@/components/answer-questions-card";
import { AssetCard } from "@/components/asset-card";
import { ConfirmDialog, useConfirm } from "@/components/confirm-dialog";
import { CopyAllButton } from "@/components/copy-all-button";
import { Disclosure } from "@/components/disclosure";
import { ExportAllButton } from "@/components/export-all-button";
import { Notice } from "@/components/notice";
import { PageHeader } from "@/components/page-header";
import { RunTimeline } from "@/components/run-timeline";
import { ScoreRing } from "@/components/score-ring";
import { useRunLauncher } from "@/components/run-launcher";
import { StatusBadge } from "@/components/status-badge";
import { ReaderVerdictCard } from "@/components/reader-verdict-card";
import type { ReaderVerdict } from "@/components/reader-verdict-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useExecutionStream } from "@/hooks/use-execution-stream";
import { api } from "@/lib/api-client";
import { formatDuration } from "@/lib/format";
import { reduceRun, runsPerRole } from "@/lib/run-timeline";
import { ROLE_CATALOG } from "@/lib/specialists";
import { cn } from "@/lib/utils";
import type { ExecutionStatus, GeneratedAsset } from "@/lib/types";
import { refreshPage } from "@/lib/page-data";
import { activityLabel, problemText } from "@/lib/product-progress";

const TERMINAL: ExecutionStatus[] = ["completed", "failed", "cancelled"];

/** How the run scored itself, as stored on a finished execution. Read from
 * the result rather than the event stream so a page opened long afterwards
 * shows the same numbers the live view did. */
interface StoredReport {
  delivered: number;
  promised: number;
  contract_violations: string[];
  limiting_gaps: string[];
  what_would_help_most?: string;
  /** Only filled on a run that stopped before spending anything because the
   * material could not carry a campaign. Answering them is worth more than
   * any rewrite - see AnswerQuestionsCard. */
  questions?: string[];
  /** Anything the run wants to say about itself - why it stopped, and when
   * a low score is a verdict on what the run was allowed to buy rather than
   * on the copy. */
  notes?: string[];
  /** False on a channel no cold reader grades - a LinkedIn message. The pull
   * column is then a placeholder everywhere it appears, and showing it as a
   * score would invent one. */
  reads_expected?: boolean;
  emails: {
    position: number;
    subject: string;
    pull: number;
    revisions: number;
    clean: boolean;
    /** Ledger ids the strategist said this email is built on. */
    evidence_assigned?: string[];
    /** Of those, the ones whose figure, name or quotation actually reached
     * the page - checked in code on the version that shipped. */
    evidence_spent?: string[];
    /** Whether a cold reader would actually have clicked. False means the
     * loop stopped rewriting, not that it judged this ready. */
    landed?: boolean;
    /** True when the loop stopped because rewriting had stopped improving the
     * draft, rather than because it ran out of attempts. */
    rewrites_stopped_helping?: boolean;
    /** False when no cold reader came back, which makes `pull` a placeholder
     * rather than a score. */
    read_reported?: boolean;
    relevant?: boolean | null;
    /** What the cold readers actually said about the version that shipped -
     * the only output in the system that says what to write instead, rather
     * than passing verdict on what was written. */
    reader_verdicts?: ReaderVerdict[];
    /** Interchangeable openings and category boilerplate the free
     * differentiation check found in the shipped copy. */
    sameness?: string[];
  }[];
}

function reportFromResult(result: Record<string, unknown> | null): StoredReport | null {
  return (result?.report as StoredReport | undefined) ?? null;
}

/** Averaged over the emails somebody actually read. A missing read is not a
 * zero and not a pass, and folding it in either way reports a number no
 * reader gave. Mirrors CampaignReport.average_pull. */
function averagePull(report: StoredReport): number {
  const scored = report.emails.filter((line) => line.read_reported !== false);
  if (scored.length === 0) return 0;
  return scored.reduce((total, line) => total + line.pull, 0) / scored.length;
}

function belowFloor(report: StoredReport): number[] {
  return report.emails
    .filter((line) => line.read_reported !== false && line.landed === false)
    .map((line) => line.position);
}

/** Emails that were built on assigned facts and put none of them on the page.
 * Nothing was invented - which is all the gates ever checked - and a stranger
 * still has no reason to believe a word of it. Mirrors
 * CampaignReport.unsubstantiated. */
function argueFromNothing(report: StoredReport): number[] {
  return report.emails
    .filter(
      (line) => (line.evidence_assigned?.length ?? 0) > 0 && !line.evidence_spent?.length,
    )
    .map((line) => line.position);
}

export function ExecutionLiveView({
  executionId,
  campaignId,
  brandId,
  campaignName,
  initialStatus,
  initialAssets,
  initialResult,
  initialErrorMessage,
  startedAt,
  completedAt,
}: {
  executionId: string;
  campaignId: string;
  brandId: string | null;
  /** Null when the campaign could not be read - the run still renders. */
  campaignName: string | null;
  initialStatus: ExecutionStatus;
  initialAssets: GeneratedAsset[];
  initialResult: Record<string, unknown> | null;
  initialErrorMessage: string | null;
  startedAt: string | null;
  completedAt: string | null;
}) {
  const router = useRouter();
  const [assets, setAssets] = useState<GeneratedAsset[]>(initialAssets);
  const [finalSnapshot, setFinalSnapshot] = useState<
    Awaited<ReturnType<typeof api.getExecutionResult>> | null
  >(null);
  const [errorMessage, setErrorMessage] = useState(initialErrorMessage);
  const [cancelling, setCancelling] = useState(false);
  const confirmStop = useConfirm();
  const restart = useRunLauncher(campaignId, "restart");
  const [now, setNow] = useState(() => Date.now());

  const { events, phase, refresh, updatedAt } = useExecutionStream(executionId);
  const run = useMemo(() => reduceRun(events), [events]);

  const status = run.finalStatus ?? initialStatus;
  const isLive = !TERMINAL.includes(status);
  const currentFinal = finalSnapshot?.id === executionId ? finalSnapshot : null;
  const currentResult = currentFinal?.result ?? initialResult;
  const needsReview = status === "completed" && (Boolean(errorMessage) ||
    ["degraded", "budget_exhausted", "cancelled", "failed"].includes(String(currentResult?.run_status)));
  const report = reportFromResult(currentResult);
  const questions = report?.questions ?? [];

  // Deliverables land mid-run: refetch whenever another email is accepted, and
  // once more when the run ends so the final rows are authoritative.
  const deliveredCount = run.emails.length;
  const lastFetched = useRef(-1);
  useEffect(() => {
    if (deliveredCount === lastFetched.current) return;
    lastFetched.current = deliveredCount;
    if (deliveredCount === 0) return;
    api.getExecutionAssets(executionId).then(setAssets).catch(() => undefined);
  }, [deliveredCount, executionId]);

  useEffect(() => {
    if (run.finalStatus === null) return;
    api
      .getExecutionResult(executionId)
      .then((result) => {
        setFinalSnapshot(result);
        setAssets(result.assets);
        setErrorMessage(result.error_message);
      })
      .catch(() => undefined);
    refreshPage();
  }, [run.finalStatus, executionId, router]);

  async function handleCancel() {
    setCancelling(true);
    try {
      await api.cancelExecution(executionId);
      confirmStop.setOpen(false);
      toast.success("Stopping after the current step. Finished drafts will be kept.");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not cancel");
    } finally {
      setCancelling(false);
    }
  }

  const elapsedMs = startedAt
    ? (isLive ? now : new Date(currentFinal?.completed_at ?? completedAt ?? startedAt).getTime()) - new Date(startedAt).getTime()
    : 0;

  const verdictsBelow = report ? belowFloor(report) : [];
  const unargued = report ? argueFromNothing(report) : [];
  const needsAttention =
    report !== null && (report.contract_violations.length > 0 || verdictsBelow.length > 0);
  const toLookAt = verdictsBelow.length + (report?.contract_violations.length ?? 0);

  const deliverables = (
    <section aria-labelledby="deliverables-title" className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 id="deliverables-title" className="font-display text-[1.875rem] leading-tight">
            {assets.length === 0
              ? "Your emails"
              : `Your ${assets.length === 1 ? "email" : `${assets.length} emails`}`}
          </h2>
          <p className="mt-0.5 text-sm text-muted-foreground">
            {isLive
              ? "Reviewed drafts appear here. Check their feedback before using them."
              : "Review the drafts, facts and links before copying them into your email tool."}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <CopyAllButton assets={assets} />
          <ExportAllButton assets={assets} />
        </div>
      </div>
      {assets.length === 0 ? (
        <div className="surface flex flex-col items-center rounded-2xl px-5 py-12 text-center">
          <span className="icon-tile mb-4 flex size-12 items-center justify-center rounded-2xl">
            {isLive ? <span className="live-dot" aria-hidden="true" /> : <Mail className="size-5" aria-hidden="true" />}
          </span>
          <p className="text-sm text-muted-foreground">
            {isLive
              ? "No drafts yet - each email appears after its review."
              : "Nothing was produced in this run."}
          </p>
        </div>
      ) : (
        assets.map((asset) => <AssetCard key={asset.id} asset={asset} />)
      )}
    </section>
  );

  const behindTheScenes = (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_280px]">
      <div className="min-w-0 space-y-3">
        <div className="flex items-center justify-between gap-4">
          <h3 className="flex items-center gap-2 text-[0.6875rem] font-medium uppercase tracking-[0.18em] text-muted-foreground">
            {isLive && <span className="live-dot" aria-hidden="true" />}
            Campaign progress{isLive ? " right now" : ""}
          </h3>
          <Link
            href={`/logs?execution=${executionId}`}
            className="text-xs font-medium text-muted-foreground transition-colors hover:text-violet-200"
          >
            All activity →
          </Link>
        </div>
        <RunTimeline steps={run.steps} events={events} now={now} />
      </div>
      <div className="space-y-2 lg:sticky lg:top-6 lg:self-start">
        <h3 className="text-[0.6875rem] font-medium uppercase tracking-[0.18em] text-muted-foreground">
          Campaign activities
        </h3>
        <Roster steps={run.steps} finished={!isLive} />
      </div>
    </div>
  );

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Run"
        title={campaignName ?? "Your material"}
        documentTitle={campaignName ? `Run · ${campaignName}` : "Run"}
        backTo={{ href: `/campaigns/${campaignId}`, label: campaignName ?? "Back to campaign" }}
        meta={<>
          {/* A run that stopped to ask a question lands on FAILED because the
              lifecycle has no status for "asked a question" - see
              CampaignOrchestrator._finalize. Showing it as a failure is a lie
              the user pays for twice: once by not answering, and once by
              distrusting the badge on a run that really did fail. */}
          {questions.length > 0 ? (
            <span className="inline-flex h-[1.375rem] items-center gap-1.5 rounded-full bg-amber-400/10 px-2.5 text-[0.6875rem] font-medium text-amber-300 ring-1 ring-amber-400/25 ring-inset">
              <span className="size-1.5 rounded-full bg-amber-400" aria-hidden="true" />
              Needs your answers
            </span>
          ) : (
            <StatusBadge status={status} warning={needsReview}
              label={status === "completed" && report && report.delivered < report.promised ? "Partial delivery" : undefined} />
          )}
          <span className="tabular-nums" title="Wall-clock time">
            {isLive ? "Running for" : "Took"} {formatDuration(elapsedMs)}
          </span>
          <span className="tabular-nums">
            {run.steps.length} step{run.steps.length === 1 ? "" : "s"}
          </span>
          <ConnectionIndicator phase={phase} updatedAt={updatedAt} />
        </>}
        actions={<>
          <Button variant="outline" size="sm" disabled={phase === "loading"} onClick={async () => {
            await refresh();
            setNow(Date.now());
            try {
              const result = await api.getExecutionResult(executionId);
              setFinalSnapshot(result);
              setAssets(result.assets);
              setErrorMessage(result.error_message);
            } catch (error) { toast.error(error instanceof Error ? error.message : "Could not refresh results"); }
            refreshPage();
          }}>
            <RefreshCw
              className={cn("size-3.5", phase === "loading" && "motion-safe:animate-spin")}
              aria-hidden="true"
            />
            {phase === "loading" ? "Refreshing…" : "Refresh"}
          </Button>
          {isLive && (
            <>
              <Button variant="outline" size="sm" onClick={confirmStop.ask}>
                Stop campaign
              </Button>
              <ConfirmDialog
                open={confirmStop.open}
                onOpenChange={confirmStop.setOpen}
                title="Stop this campaign?"
                description="It stops after the current step. Finished emails are kept, but nothing further is generated and the run cannot be resumed."
                confirmLabel="Stop campaign"
                pending={cancelling}
                onConfirm={handleCancel}
              />
            </>
          )}
          {(status === "failed" || status === "cancelled") && (
            <>
              <Button variant="outline" size="sm" disabled={restart.busy} onClick={restart.run}>
                {restart.busy ? "Restarting…" : "Restart"}
              </Button>
              {restart.dialog}
            </>
          )}
        </>}
      />

      {/* A run that stopped to ask is not a failure, and showing it as one -
          a red box with the questions crammed into an error string - is what
          made the questions unanswerable in practice. */}
      {questions.length > 0 ? (
        <AnswerQuestionsCard
          questions={questions}
          campaignId={campaignId}
          brandId={brandId}
        />
      ) : (
        errorMessage && (
          <Notice tone="danger" title="This run stopped">
            {problemText(errorMessage)}
          </Notice>
        )
      )}

      {/* The verdict in one strip: how many were delivered and how they read.
          The detail - every reader's words, every flag - is below the emails,
          because the emails are what the reader came to this page for. */}
      {report && (
        <div
          className={cn(
            "rise relative isolate flex flex-col items-stretch gap-x-8 gap-y-5 overflow-hidden rounded-2xl p-5 shadow-[var(--shadow-surface)] sm:flex-row sm:items-center sm:p-6",
            needsAttention
              ? "bg-card bg-[linear-gradient(110deg,oklch(0.8_0.15_80/9%),transparent_55%)] ring-1 ring-amber-400/25"
              : "bg-card bg-[linear-gradient(110deg,oklch(0.8_0.15_165/9%),transparent_55%)] ring-1 ring-emerald-400/20",
          )}
        >
          <span
            className={cn(
              "flex size-12 shrink-0 items-center justify-center rounded-2xl ring-1",
              needsAttention
                ? "bg-amber-400/10 text-amber-300 ring-amber-400/25"
                : "bg-emerald-400/10 text-emerald-300 ring-emerald-400/25",
            )}
          >
            {needsAttention ? (
              <TriangleAlert className="size-5" aria-hidden="true" />
            ) : (
              <CheckCircle2 className="size-5" aria-hidden="true" />
            )}
          </span>
          <div className="min-w-0 flex-1">
            <p className="text-[0.6875rem] font-medium uppercase tracking-[0.16em] text-muted-foreground">
              Delivery
            </p>
            <p className="mt-1 text-lg font-semibold tracking-tight">
              Delivered {report.delivered} of {report.promised}{" "}
              {report.reads_expected === false ? "LinkedIn message" : "email"}
              {report.promised === 1 ? "" : "s"}
            </p>
            <div
              className="mt-2.5 h-1.5 max-w-sm overflow-hidden rounded-full bg-white/[0.07]"
              role="presentation"
            >
              <div
                className={cn(
                  "h-full rounded-full",
                  needsAttention
                    ? "bg-gradient-to-r from-amber-300 to-amber-500"
                    : "bg-gradient-to-r from-emerald-300 to-violet-400",
                )}
                style={{ width: `${report.promised > 0 ? Math.min(100, (report.delivered / report.promised) * 100) : 0}%` }}
              />
            </div>
            <p className="mt-2.5 text-xs leading-relaxed text-muted-foreground">
              {report.reads_expected === false
                ? "Every claim passed the evidence gate; no cold-reader panel grades this channel."
                : needsAttention
                  ? `${toLookAt} thing${toLookAt === 1 ? "" : "s"} to look at before you send - see “How the copy tested” below.`
                  : "Every email passed its checks and its cold read."}
            </p>
          </div>
          {/* A channel no cold reader has ever read has no score, and a 0.0
              here would be read as one. */}
          {report.reads_expected !== false && (
            <div className="flex items-center gap-4 sm:shrink-0 sm:border-l sm:border-white/[0.07] sm:pl-8">
              <ScoreRing value={averagePull(report)} label="Average cold-read score" />
              <div>
                <p className="text-sm font-medium">Cold-read score</p>
                <p className="mt-0.5 max-w-[11rem] text-[0.6875rem] leading-relaxed text-muted-foreground">
                  AI simulation, uncalibrated - averaged over the emails a reader reported on.
                </p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* While a run is going, watching it work is the point and the emails
          arrive one by one underneath. Once it has finished, the emails are
          the point and the working is history - folded away below. */}
      {isLive ? (
        <>
          {behindTheScenes}
          {deliverables}
        </>
      ) : (
        deliverables
      )}

      {report && (
        <Disclosure
          title="How the copy tested"
          summary={
            needsAttention
              ? `${toLookAt} thing${toLookAt === 1 ? "" : "s"} to look at before you send`
              : "Scores, rewrites and checks for each email"
          }
          tone={needsAttention ? "attention" : "default"}
          defaultOpen={needsAttention}
        >
          <div className="space-y-2 text-sm">
            <ul className="space-y-1 text-muted-foreground">
              {report.emails.map((line) => (
                <li key={line.position} className="tabular-nums">
                  #{line.position} &ldquo;{line.subject}&rdquo; -{" "}
                  {line.read_reported === false
                    ? "no cold reader reported back"
                    : `${line.pull.toFixed(0)}/10`}{" "}
                  after {line.revisions} rewrite{line.revisions === 1 ? "" : "s"}
                  {line.clean ? "" : " (shipped with unresolved checks)"}
                  {line.relevant === false && <span className="text-amber-400"> · Unresolved audience mismatch</span>}
                </li>
              ))}
            </ul>
            {verdictsBelow.length > 0 && (
              <p className="text-amber-400">
                Email{verdictsBelow.length === 1 ? "" : "s"} {verdictsBelow.join(", ")}{" "}
                did not satisfy the simulated assessment criteria. The loop stopped rewriting them; it did not decide
                these were ready to send.
                {/* Only the emails actually below the floor may speak here: one
                    that stopped early and was later rescued by the sequence pass
                    still carries the flag, and would otherwise explain away a
                    different email's failure. */}
                {report.emails.some(
                  (line) =>
                    line.read_reported !== false &&
                    line.landed === false &&
                    line.rewrites_stopped_helping,
                ) &&
                  " Rewriting had stopped moving the score - more attempts would not have" +
                    " helped, but different material might."}
              </p>
            )}
            {unargued.length > 0 && (
              <p className="text-amber-400">
                The automatic check did not match email{unargued.length === 1 ? "" : "s"}{" "}
                {unargued.join(", ")} to the assigned evidence. Compare the claims with your
                sources before using the copy. This check can miss paraphrases; it does not
                establish whether a claim is true or invented.
              </p>
            )}
            {report.contract_violations.length > 0 && (
              <p className="text-amber-400">{report.contract_violations.join("; ")}</p>
            )}
            {(report.notes ?? []).map((note) => (
              <p key={note} className="text-muted-foreground">
                {note}
              </p>
            ))}
            {report.what_would_help_most && (
              <p className="rounded-xl border border-violet-400/20 bg-violet-500/[0.07] p-3.5 text-violet-100">
                <span className="font-medium">What would help most next time: </span>
                {report.what_would_help_most}
              </p>
            )}
          </div>
        </Disclosure>
      )}

      {/* The number above says something is wrong; this says what. Both come
          from the same already-paid-for cold read. */}
      {report && <ReaderVerdictCard emails={report.emails} />}

      {run.knowledge && (
        <Disclosure
          title="What we know about your business"
          summary={[
            `${run.knowledge.evidenceCount} fact${run.knowledge.evidenceCount === 1 ? "" : "s"} the copy may claim`,
            run.knowledge.gaps.length > 0 &&
              `${run.knowledge.gaps.length} gap${run.knowledge.gaps.length === 1 ? "" : "s"}`,
            run.knowledge.notes.length > 0 &&
              `${run.knowledge.notes.length} note${run.knowledge.notes.length === 1 ? "" : "s"} from compiling it`,
          ]
            .filter(Boolean)
            .join(" · ")}
        >
          <div className="space-y-2 text-sm">
            {run.reader ? (
              <p className="text-muted-foreground">
                Writing to: {run.reader.description}
                {run.reader.segment ? ` (read cold by: ${run.reader.segment})` : ""}
              </p>
            ) : (
              run.knowledge.segments.length > 0 && (
                <p className="text-muted-foreground">
                  Who could be written to: {run.knowledge.segments.join("; ")}
                </p>
              )
            )}
            {!run.knowledge.voiceLearned && (
              <p className="text-muted-foreground">
                No existing copy to learn your voice from - the emails will sound competent, but
                not like you.
              </p>
            )}
            {run.knowledge.gaps.length > 0 && (
              <>
                <p className="font-medium">What is missing, and what it costs:</p>
                <ul className="list-disc space-y-1 pl-5 text-muted-foreground">
                  {run.knowledge.gaps.map((gap, index) => (
                    <li key={index}>{gap}</li>
                  ))}
                </ul>
              </>
            )}
            {run.knowledge.notes.length > 0 && (
              <ul className="space-y-1.5 border-t border-hairline pt-3">
                {run.knowledge.notes.map((note, index) => (
                  <li key={index} className="text-amber-300/90">
                    {note}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </Disclosure>
      )}

      {!isLive && (
        <Disclosure
          title="Campaign progress"
          summary={`Every step the team took - ${run.steps.length} step${run.steps.length === 1 ? "" : "s"}`}
        >
          {behindTheScenes}
        </Disclosure>
      )}
    </div>
  );
}

function ConnectionIndicator({
  phase,
  updatedAt,
}: {
  phase: ReturnType<typeof useExecutionStream>["phase"];
  updatedAt: string | null;
}) {
  const failed = phase === "error";
  return (
    <span
      role="status"
      className={cn("flex items-center gap-1.5", failed ? "text-amber-300" : "text-muted-foreground")}
    >
      <span
        className={cn(
          "size-1.5 rounded-full",
          failed ? "bg-amber-400" : phase === "loading" ? "live-dot !size-1.5" : "bg-muted-foreground/50",
        )}
        aria-hidden="true"
      />
      {failed
        ? "Refresh failed — showing last snapshot"
        : phase === "loading"
          ? "Refreshing…"
          : updatedAt
            ? `Snapshot ${updatedAt}`
            : "Manual refresh"}
    </span>
  );
}

/** One card per reasoning role, showing how many turns it has taken. Unlike
 * the steps above, this answers "who has been involved at all" - the roster is
 * the cast, the timeline is the plot. */
function Roster({
  steps,
  finished,
}: {
  steps: ReturnType<typeof reduceRun>["steps"];
  /** Once the run is over, a role that never ran was not needed - material
   * already compiled, one email with no sequence to review - and "not
   * started" read as a role that was still waiting, or had hung. */
  finished: boolean;
}) {
  const runs = runsPerRole(steps);
  const latest = new Map(
    steps.filter((step) => step.agentId).map((step) => [step.agentId as string, step]),
  );

  return (
    <div className="surface divide-y divide-hairline overflow-hidden rounded-2xl">
      {ROLE_CATALOG.map((specialist) => {
        const step = latest.get(specialist.id);
        const dispatches = runs.get(specialist.id) ?? 0;
        return (
          <Card key={specialist.id} size="sm" className="rounded-none bg-transparent bg-none shadow-none ring-0">
            <CardContent className="space-y-1.5">
              <div className="flex items-center justify-between gap-2">
                <span className="flex min-w-0 items-center gap-2.5">
                  <span
                    className={cn(
                      "flex size-7 shrink-0 items-center justify-center rounded-lg text-[0.6875rem] font-semibold",
                      step?.state === "running"
                        ? "brand-mark text-white"
                        : step
                          ? "bg-white/[0.06] text-foreground/80 ring-1 ring-white/[0.08]"
                          : "bg-white/[0.03] text-muted-foreground/60 ring-1 ring-white/[0.05]",
                    )}
                    aria-hidden="true"
                  >
                    {activityLabel(specialist.id).slice(0, 1)}
                  </span>
                  <span className="text-sm font-medium">{activityLabel(specialist.id)}</span>
                </span>
                {step ? (
                  <Badge
                    variant="outline"
                    className={
                      step.state === "failed"
                        ? "border-red-400/25 bg-red-500/10 text-red-300"
                        : step.state === "running"
                          ? "border-violet-400/30 bg-violet-500/15 text-violet-200"
                          : "border-emerald-400/20 bg-emerald-400/10 text-emerald-300"
                    }
                  >
                    {step.state === "running" ? "working…" : step.state}
                  </Badge>
                ) : (
                  <Badge variant="outline" className="border-white/[0.07] bg-transparent text-muted-foreground">
                    {finished ? "not needed" : "not started"}
                  </Badge>
                )}
              </div>
              <p className="pl-[2.375rem] text-xs leading-relaxed text-muted-foreground">
                {specialist.role}
                {dispatches > 0 && (
                  <span className="text-muted-foreground/70 tabular-nums">
                    {" · "}
                    {dispatches} turn{dispatches === 1 ? "" : "s"}
                  </span>
                )}
              </p>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
