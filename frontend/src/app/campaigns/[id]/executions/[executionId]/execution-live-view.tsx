"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { AnswerQuestionsCard } from "@/components/answer-questions-card";
import { AssetCard } from "@/components/asset-card";
import { ConfirmDialog, useConfirm } from "@/components/confirm-dialog";
import { CopyAllButton } from "@/components/copy-all-button";
import { RunTimeline } from "@/components/run-timeline";
import { StatusBadge } from "@/components/status-badge";
import { ReaderVerdictCard } from "@/components/reader-verdict-card";
import type { ReaderVerdict } from "@/components/reader-verdict-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useExecutionStream } from "@/hooks/use-execution-stream";
import { api } from "@/lib/api-client";
import { formatCost, formatDuration, formatTokens } from "@/lib/format";
import { estimateCost, reduceRun, runsPerRole } from "@/lib/run-timeline";
import { ROLE_CATALOG } from "@/lib/specialists";
import type { ExecutionStatus, GeneratedAsset } from "@/lib/types";

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
  initialStatus,
  initialAssets,
  initialResult,
  initialErrorMessage,
  startedAt,
  completedAt,
  finalCostUsd,
}: {
  executionId: string;
  campaignId: string;
  brandId: string | null;
  initialStatus: ExecutionStatus;
  initialAssets: GeneratedAsset[];
  initialResult: Record<string, unknown> | null;
  initialErrorMessage: string | null;
  startedAt: string | null;
  completedAt: string | null;
  finalCostUsd: number;
}) {
  const router = useRouter();
  const [assets, setAssets] = useState<GeneratedAsset[]>(initialAssets);
  const [errorMessage, setErrorMessage] = useState(initialErrorMessage);
  const [cancelling, setCancelling] = useState(false);
  const confirmStop = useConfirm();
  const [now, setNow] = useState(() => Date.now());

  const { events, phase } = useExecutionStream(executionId, !TERMINAL.includes(initialStatus));
  const run = useMemo(() => reduceRun(events), [events]);

  const status = run.finalStatus ?? initialStatus;
  const isLive = !TERMINAL.includes(status);
  const report = reportFromResult(initialResult);
  const questions = report?.questions ?? [];

  // A campaign can sit on one model call for half a minute; without a moving
  // clock the page reads as frozen.
  useEffect(() => {
    if (!isLive) return;
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [isLive]);

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
        setAssets(result.assets);
        setErrorMessage(result.error_message);
      })
      .catch(() => undefined);
    router.refresh();
  }, [run.finalStatus, executionId, router]);

  async function handleCancel() {
    setCancelling(true);
    try {
      await api.cancelExecution(executionId);
      confirmStop.setOpen(false);
      toast.success("Stopping - it finishes the model call it's on, then stops for good");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not cancel");
    } finally {
      setCancelling(false);
    }
  }

  async function handleRestart() {
    try {
      const execution = await api.restartCampaign(campaignId);
      router.push(`/campaigns/${campaignId}/executions/${execution.id}`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not restart");
    }
  }

  const totalTokens = run.inputTokens + run.outputTokens;
  const liveCost = estimateCost(run.steps);
  const cost = isLive ? liveCost : finalCostUsd || liveCost;
  const elapsedMs = startedAt
    ? (isLive ? now : new Date(completedAt ?? startedAt).getTime()) - new Date(startedAt).getTime()
    : 0;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-semibold tracking-tight">Your material</h1>
        {/* A run that stopped to ask a question lands on FAILED because the
            lifecycle has no status for "asked a question" - see
            CampaignOrchestrator._finalize. Showing it as a failure is a lie
            the user pays for twice: once by not answering, and once by
            distrusting the badge on a run that really did fail. */}
        {questions.length > 0 ? (
          <Badge variant="outline" className="border-transparent bg-amber-500/15 text-amber-400">
            needs your answers
          </Badge>
        ) : (
          <StatusBadge status={status} />
        )}
        <span className="text-sm text-muted-foreground">
          {assets.length} deliverable{assets.length === 1 ? "" : "s"}
        </span>
        <div className="ml-auto flex items-center gap-2">
          <CopyAllButton assets={assets} />
          {isLive && (
            <>
              <Button variant="outline" size="sm" onClick={confirmStop.ask}>
                Stop campaign
              </Button>
              <ConfirmDialog
                open={confirmStop.open}
                onOpenChange={confirmStop.setOpen}
                title="Stop this campaign?"
                description="It stops as soon as the model call currently in flight finishes - already-finished emails are kept, but nothing further is generated and the run cannot be resumed."
                confirmLabel="Stop campaign"
                pending={cancelling}
                onConfirm={handleCancel}
              />
            </>
          )}
          {(status === "failed" || status === "cancelled") && (
            <Button variant="outline" size="sm" onClick={handleRestart}>
              Restart
            </Button>
          )}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-x-6 gap-y-1 text-sm text-muted-foreground">
        <span className="tabular-nums">
          {isLive ? "Running for" : "Took"} {formatDuration(elapsedMs)}
        </span>
        <span className="tabular-nums">{formatTokens(totalTokens)} tokens</span>
        <span className="tabular-nums">{formatCost(cost)}</span>
        <span className="tabular-nums">
          {run.steps.length} step{run.steps.length === 1 ? "" : "s"}
        </span>
        {isLive && <ConnectionIndicator phase={phase} />}
      </div>

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
          <Card className="border-destructive/40">
            <CardContent className="pt-6 text-sm text-destructive">{errorMessage}</CardContent>
          </Card>
        )
      )}

      {run.knowledge && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-base">What we know about your business</CardTitle>
            <Badge variant="outline">
              {run.knowledge.evidenceCount} fact
              {run.knowledge.evidenceCount === 1 ? "" : "s"} the copy may claim
            </Badge>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
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
            {run.knowledge.notes.map((note, index) => (
              <p key={index} className="text-amber-400">
                {note}
              </p>
            ))}
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
          </CardContent>
        </Card>
      )}

      {report && (
        <Card
          className={
            report.contract_violations.length > 0 || belowFloor(report).length > 0
              ? "ring-amber-500/40"
              : "ring-emerald-500/40"
          }
        >
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-base">How the copy tested</CardTitle>
            <Badge
              variant={
                report.contract_violations.length > 0 || belowFloor(report).length > 0
                  ? "outline"
                  : "default"
              }
            >
              {averagePull(report).toFixed(1)}/10 with a cold reader
            </Badge>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <p className="text-muted-foreground">
              Delivered {report.delivered} of {report.promised} email
              {report.promised === 1 ? "" : "s"}.
            </p>
            <ul className="space-y-1 text-muted-foreground">
              {report.emails.map((line) => (
                <li key={line.position} className="tabular-nums">
                  #{line.position} &ldquo;{line.subject}&rdquo; -{" "}
                  {line.read_reported === false
                    ? "no cold reader reported back"
                    : `${line.pull.toFixed(0)}/10`}{" "}
                  after {line.revisions} rewrite{line.revisions === 1 ? "" : "s"}
                  {line.clean ? "" : " (shipped with unresolved checks)"}
                </li>
              ))}
            </ul>
            {belowFloor(report).length > 0 && (
              <p className="text-amber-400">
                Email{belowFloor(report).length === 1 ? "" : "s"} {belowFloor(report).join(", ")}{" "}
                never reached the 7/10 floor. The loop stopped rewriting them; it did not decide
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
            {argueFromNothing(report).length > 0 && (
              <p className="text-amber-400">
                Email{argueFromNothing(report).length === 1 ? "" : "s"}{" "}
                {argueFromNothing(report).join(", ")} made no use of the evidence they were built
                on. Nothing in them is invented - but nothing in them is checkable either, and a
                stranger has no reason to believe a company describing itself.
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
              <p className="text-muted-foreground">
                What would help most next time: {report.what_would_help_most}
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {/* The number above says something is wrong; this says what. Both come
          from the same already-paid-for cold read. */}
      {report && <ReaderVerdictCard emails={report.emails} />}

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="space-y-4">
          <div className="flex items-center justify-between gap-4">
            <h2 className="text-sm font-medium text-muted-foreground">
              What your team is doing{isLive ? " right now" : ""}
            </h2>
            <Link
              href={`/logs?execution=${executionId}`}
              className="text-xs text-muted-foreground hover:text-foreground"
            >
              Full log
            </Link>
          </div>
          <RunTimeline steps={run.steps} events={events} now={now} />

          <div className="space-y-4 pt-4">
            <h2 className="text-sm font-medium text-muted-foreground">Deliverables</h2>
            {assets.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                {isLive
                  ? "Nothing has landed yet - each email appears once it has passed a cold read."
                  : "Nothing was produced in this run."}
              </p>
            ) : (
              assets.map((asset) => <AssetCard key={asset.id} asset={asset} />)
            )}
          </div>
        </div>

        <div className="space-y-2">
          <h2 className="text-sm font-medium text-muted-foreground">The team</h2>
          <Roster steps={run.steps} />
        </div>
      </div>
    </div>
  );
}

function ConnectionIndicator({ phase }: { phase: ReturnType<typeof useExecutionStream>["phase"] }) {
  if (phase === "reconnecting") {
    return (
      <span className="flex items-center gap-1.5 text-amber-400">
        <span className="size-1.5 animate-pulse rounded-full bg-amber-400" />
        reconnecting
      </span>
    );
  }
  if (phase === "loading") {
    return <span className="text-muted-foreground">connecting...</span>;
  }
  return (
    <span className="flex items-center gap-1.5">
      <span className="size-1.5 animate-pulse rounded-full bg-primary" />
      live
    </span>
  );
}

/** One card per reasoning role, showing how many turns it has taken. Unlike
 * the steps above, this answers "who has been involved at all" - the roster is
 * the cast, the timeline is the plot. */
function Roster({ steps }: { steps: ReturnType<typeof reduceRun>["steps"] }) {
  const runs = runsPerRole(steps);
  const latest = new Map(
    steps.filter((step) => step.agentId).map((step) => [step.agentId as string, step]),
  );

  return (
    <div className="space-y-2">
      {ROLE_CATALOG.map((specialist) => {
        const step = latest.get(specialist.id);
        const dispatches = runs.get(specialist.id) ?? 0;
        return (
          <Card key={specialist.id} size="sm">
            <CardContent className="space-y-1.5">
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm font-medium">{specialist.name}</span>
                {step ? (
                  <Badge
                    variant="outline"
                    className={
                      step.state === "failed"
                        ? "border-transparent bg-destructive/15 text-destructive"
                        : step.state === "running"
                          ? "border-transparent bg-primary/20 text-primary"
                          : "border-transparent bg-emerald-500/15 text-emerald-400"
                    }
                  >
                    {step.state === "running" ? "working..." : step.state}
                  </Badge>
                ) : (
                  <Badge variant="outline" className="border-transparent bg-muted text-muted-foreground">
                    not started
                  </Badge>
                )}
              </div>
              <p className="text-xs text-muted-foreground">{specialist.role}</p>
              {dispatches > 0 && (
                <p className="text-xs text-muted-foreground tabular-nums">
                  {dispatches} turn{dispatches === 1 ? "" : "s"}
                  {step?.model ? ` - ${step.model}` : ""}
                </p>
              )}
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
