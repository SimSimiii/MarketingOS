"use client";

import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { formatTime } from "@/lib/format";
import { activityLabel, activityMessage, problemText, progressText } from "@/lib/product-progress";
import type { StepState, TimelineStep } from "@/lib/run-timeline";
import type { LiveExecutionEvent } from "@/lib/types";
import { cn } from "@/lib/utils";

const STEP_STYLES: Record<StepState, { dot: string; label: string; badge: string }> = {
  running: { dot: "live-dot", label: "working", badge: "border-violet-400/30 bg-violet-500/15 text-violet-200" },
  completed: { dot: "bg-emerald-400 shadow-[0_0_8px_oklch(0.8_0.17_160/70%)]", label: "done", badge: "border-emerald-400/20 bg-emerald-400/10 text-emerald-300" },
  failed: { dot: "bg-red-400 shadow-[0_0_8px_oklch(0.7_0.2_25/70%)]", label: "failed", badge: "border-red-400/25 bg-red-500/10 text-red-300" },
};

/** Every turn a reasoning role took, in order, and what each one produced.
 *
 * A turn is the unit here rather than a phase: writing email 2 a second time
 * is its own row, because the rework loop is what the user is paying for and
 * it used to be invisible. Every row opens onto that role's own log lines -
 * the answer to "what is it actually doing right now", which a status badge
 * alone never gives. */
export function RunTimeline({
  steps,
  events,
  now,
}: {
  steps: TimelineStep[];
  events: LiveExecutionEvent[];
  now: number;
}) {
  const [openStep, setOpenStep] = useState<number | null>(null);

  if (steps.length === 0) {
    return (
      <p className="surface flex items-center gap-3 rounded-xl px-4 py-3.5 text-sm text-muted-foreground">
        <span className="live-dot" aria-hidden="true" />
        Reading everything you provided before anything gets written…
      </p>
    );
  }

  return (
    // The rail behind the cards joins the turns into one sequence; it shows
    // only in the gaps between them, which is where the eye reads "then".
    <ol className="relative space-y-2.5 before:absolute before:top-4 before:bottom-4 before:left-[1.3rem] before:w-px before:bg-gradient-to-b before:from-violet-400/50 before:via-white/10 before:to-transparent">
      {steps.map((step) => (
        <li key={step.step}>
          <StepRow
            step={step}
            events={events}
            now={now}
            open={openStep === step.step}
            onToggle={() => setOpenStep(openStep === step.step ? null : step.step)}
          />
        </li>
      ))}
    </ol>
  );
}

function StepRow({
  step,
  events,
  now,
  open,
  onToggle,
}: {
  step: TimelineStep;
  events: LiveExecutionEvent[];
  now: number;
  open: boolean;
  onToggle: () => void;
}) {
  const style = STEP_STYLES[step.state];
  const lines = events.filter((event) => event.step === step.step && activityMessage(event) !== null);
  // A finished step reports what it took; a running one has to keep moving,
  // or the page reads as frozen through a 40-second model call.
  const elapsedMs =
    step.state === "running" && step.startedAt
      ? now - new Date(step.startedAt).getTime()
      : step.durationMs;

  return (
    <Card
      size="sm"
      className={cn(
        "relative",
        open && "ring-violet-400/30",
        step.state === "running" && "ring-violet-400/30 shadow-[var(--shadow-surface),0_0_24px_-8px_oklch(0.6_0.22_293/50%)]",
      )}
    >
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={open}
        className="flex w-full cursor-pointer items-start gap-3 px-(--card-spacing) text-left"
      >
        <span className="mt-1 flex size-3.5 shrink-0 items-center justify-center rounded-full bg-card ring-4 ring-card">
          <span className={cn("size-2 rounded-full", style.dot)} />
        </span>
        <span className="min-w-0 flex-1 space-y-1">
          <span className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-semibold">
              {activityLabel(step.agentId)}
            </span>
            <Badge variant="outline" className={style.badge}>
              {style.label}
            </Badge>
            <span className="text-[0.6875rem] text-muted-foreground tabular-nums">step {step.step}</span>
            {step.attempt > 1 && (
              <Badge variant="outline" className="border-amber-400/25 bg-amber-400/10 text-amber-300">
                rework - attempt {step.attempt}
              </Badge>
            )}
          </span>

          {step.label && (
            <span className="block text-sm text-muted-foreground">{progressText(step.label)}</span>
          )}

          {step.progress && (
            <span className="block text-xs text-violet-300">{progressText(step.progress, `${activityLabel(step.agentId)}…`)}</span>
          )}

          {step.error && <span className="block text-xs text-destructive">{problemText(step.error)}</span>}

          {step.summary && (
            <span className="block text-xs text-emerald-300">{progressText(step.summary, "Review complete.")}</span>
          )}

          <span className="flex flex-wrap gap-x-3 text-xs text-muted-foreground tabular-nums">
            {elapsedMs > 0 && <span>{(elapsedMs / 1000).toFixed(1)}s</span>}
            <span className="text-muted-foreground/70">
              {lines.length} update{lines.length === 1 ? "" : "s"}
            </span>
          </span>
        </span>
        <span className="mt-0.5 shrink-0 rounded-full border border-white/[0.08] bg-white/[0.03] px-2 py-0.5 text-[0.6875rem] text-muted-foreground transition-colors hover:text-foreground">
          {open ? "Hide" : "Details"}
        </span>
      </button>

      {open && <StepLog lines={lines} />}
    </Card>
  );
}

function StepLog({ lines }: { lines: LiveExecutionEvent[] }) {
  const [expanded, setExpanded] = useState<Set<number>>(() => new Set());
  // Keep event indices stable when non-customer diagnostics are omitted.
  const visible = lines
    .map((line, index) => ({ line, index }))
    .filter(({ line }) => activityMessage(line) !== null);
  const expandable = visible.filter(({ line }) => hasDetail(line));

  const toggle = (index: number) =>
    setExpanded((current) => {
      const next = new Set(current);
      if (!next.delete(index)) next.add(index);
      return next;
    });

  return (
    <div className="mt-2 border-t border-hairline bg-black/15 pt-2">
      <div className="flex items-center justify-between gap-3 px-(--card-spacing) pb-1">
        <span className="text-xs font-medium text-muted-foreground">Progress and feedback</span>
        <span className="flex items-center gap-3">
          {expandable.length > 0 && (
            <button
              type="button"
              onClick={() =>
                setExpanded((current) =>
                  current.size > 0
                    ? new Set()
                    : new Set(expandable.map(({ index }) => index)),
                )
              }
              className="text-xs text-muted-foreground hover:text-foreground"
            >
              {expanded.size > 0 ? "collapse all" : `expand all (${expandable.length})`}
            </button>
          )}
        </span>
      </div>
      <div className="max-h-[32rem] overflow-y-auto px-(--card-spacing)">
        {visible.length === 0 ? (
          <p className="py-2 text-xs text-muted-foreground">No progress updates for this step yet.</p>
        ) : (
          <ul className="space-y-1 text-xs">
            {visible.map(({ line, index }) => {
              const detailed = hasDetail(line);
              const open = expanded.has(index);
              return (
                <li key={index}>
                  <div
                    className={cn(
                      "flex gap-2",
                      detailed && "cursor-pointer rounded hover:bg-muted/50",
                    )}
                    onClick={detailed ? () => toggle(index) : undefined}
                  >
                    <span className="shrink-0 text-muted-foreground/60 tabular-nums">
                      {formatTime(line.at)}
                    </span>
                    <span className={cn("min-w-0 flex-1", LEVEL_TEXT[line.level])}>
                      {activityMessage(line)}
                    </span>
                    {detailed && (
                      <span className="shrink-0 text-muted-foreground/60">{open ? "−" : "+"}</span>
                    )}
                  </div>
                  {detailed && open && <LineDetail line={line} />}
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}

/** Event types that carry more than their sentence.
 *
 * Everything here was already on the wire and already typed - it was being
 * dropped at render, which is why a step could report "10 edit(s) requested"
 * and give no way to read the ten edits. */
const DETAILED = new Set([
  "draft",
  "review",
  "critique",
  "gates",
  "brief_ready",
  "knowledge_ready",
  "sequence_review",
  "campaign_report",
]);

function hasDetail(line: LiveExecutionEvent): boolean {
  if (!DETAILED.has(line.type)) return false;
  // A passing gate check has nothing to open; a failing one has the issues.
  if (line.type === "gates") return (line.issues?.length ?? 0) > 0;
  return true;
}

/** The structured payload of one log line, laid out to be read. */
function LineDetail({ line }: { line: LiveExecutionEvent }) {
  return (
    <div className="mt-1 mb-2 ml-[4.5rem] space-y-2 border-l border-border pl-3 text-xs">
      {line.type === "draft" && (
        <>
          <Field label="Subject" value={line.subject} />
          <Field label="Preview" value={line.preview_text} />
          <div className="whitespace-pre-wrap text-muted-foreground">
            {line.greeting}
            {"\n\n"}
            {line.body}
          </div>
          <Field label="Button" value={line.call_to_action} />
          {line.postscript && <Field label="P.S." value={line.postscript} />}
          <p className="text-muted-foreground/70 tabular-nums">{line.word_count} words of body</p>
        </>
      )}

      {line.type === "review" &&
        (line.readers ?? []).map((reader, index) => (
          <div key={index} className="space-y-0.5">
            <p className="font-medium">
              {reader.persona || `Reader ${index + 1}`}
              {!reader.reported ? (
                <span className="ml-2 text-amber-400">did not report back</span>
              ) : (
                <span className="ml-2 tabular-nums text-muted-foreground">
                  {reader.pull}/10 · {reader.opened ? "would open" : "would not open"} ·{" "}
                  {reader.would_act ? "would click today" : "would not click"}
                </span>
              )}
              {reader.reported && reader.understood === false && (
                /* Ahead of the score, not beside it. A reader who could not
                   decode the email did not decline the offer, so their click
                   estimate answers a question they were never able to reach. */
                <span className="ml-2 text-destructive">could not say what it is</span>
              )}
            </p>
            {reader.reported && (
              <ul className="space-y-0.5 text-muted-foreground">
                <li>
                  {reader.understood === false ? "Guessed it sells" : "Thinks it sells"}:{" "}
                  {reader.what_it_sells || "they could not say"}
                </li>
                <li>Stopped at: {reader.stopped_at || "they read to the end"}</li>
                <li>Biggest doubt: {reader.biggest_doubt || "nothing they named"}</li>
                {reader.fixes.map((fix, fixIndex) => (
                  <li key={fixIndex}>Would cut or change: {fix}</li>
                ))}
              </ul>
            )}
          </div>
        ))}

      {line.type === "critique" && (
        <>
          {line.critique_summary && <p>{line.critique_summary}</p>}
          {line.strategy_gap && (
            <p className="text-amber-400">
              {line.failure_mode === "missing_material" ? "Missing material" : "Argument gap"}: {line.strategy_gap}
            </p>
          )}
          {line.brief_drift && (
            <p className="text-amber-400">Brief drift: {line.brief_drift}</p>
          )}
          {(line.unspent_evidence ?? []).length > 0 && (
            <p className="text-muted-foreground">
              Evidence assigned and unused: {line.unspent_evidence.join(", ")}
            </p>
          )}
          <ol className="space-y-1.5">
            {(line.edits ?? []).map((edit, index) => (
              <li key={index} className="space-y-0.5">
                <span className={cn("font-medium", SEVERITY_TEXT[edit.severity])}>
                  {edit.severity}
                </span>
                {edit.line && (
                  <span className="ml-2 text-muted-foreground">&ldquo;{edit.line}&rdquo;</span>
                )}
                <p className="text-muted-foreground">{edit.problem}</p>
                <p>→ {edit.fix}</p>
              </li>
            ))}
          </ol>
        </>
      )}

      {line.type === "gates" && (
        <ul className="space-y-1">
          {(line.issues ?? []).map((issue, index) => (
            <li key={index}>
              <span
                className={cn(
                  "font-medium",
                  issue.severity === "blocking" ? "text-destructive" : "text-amber-400",
                )}
              >
                {issue.gate}
              </span>
              <span className="ml-2 text-muted-foreground">{issue.detail}</span>
            </li>
          ))}
        </ul>
      )}

      {line.type === "brief_ready" && (
        <>
          <Field label="Writing to" value={line.reader} />
          <Field label="Promise" value={line.promise} />
          <Field label="Arc" value={line.arc} />
          <ol className="space-y-1">
            {line.emails.map((email) => (
              <li key={email.position}>
                <span className="font-medium">Email {email.position}</span>
                <p className="text-muted-foreground">{email.single_idea || email.job}</p>
                <p className="text-muted-foreground/70">
                  Kills: {email.objection || "no objection assigned"} · Spends:{" "}
                  {email.evidence_ids.join(", ") || "nothing assigned"}
                </p>
                {(email.must_not_say ?? []).length > 0 && (
                  <p className="text-muted-foreground/70">
                    Leaves out on purpose: {email.must_not_say?.join("; ")}
                  </p>
                )}
                <EmailArgument email={email} />
              </li>
            ))}
          </ol>
        </>
      )}

      {line.type === "knowledge_ready" && (
        <>
          <Field label="Segments" value={line.segments.join("; ") || "none found"} />
          {line.gaps.length > 0 && (
            <ul className="space-y-0.5 text-muted-foreground">
              {line.gaps.map((gap, index) => (
                <li key={index}>Missing: {gap}</li>
              ))}
            </ul>
          )}
        </>
      )}

      {line.type === "sequence_review" && (
        <ul className="space-y-0.5 text-muted-foreground">
          {Object.entries(line.rework).map(([position, notes]) => (
            <li key={position}>
              Email {position}: {notes.join("; ")}
            </li>
          ))}
        </ul>
      )}

      {line.type === "campaign_report" && (
        <>
          {line.below_floor.length > 0 && (
            <p className="text-amber-400">
              Below the floor after every rewrite: email {line.below_floor.join(", ")}
            </p>
          )}
          {line.contract_violations.map((violation, index) => (
            <p key={index} className="text-amber-400">
              {violation}
            </p>
          ))}
          {line.limiting_gaps.map((gap, index) => (
            <p key={index} className="text-muted-foreground">
              Held the copy back: {gap}
            </p>
          ))}
          {line.what_would_help_most && <p>Would help most: {line.what_would_help_most}</p>}
        </>
      )}
    </div>
  );
}

/** The four beats of one email's argument, when the strategist wrote them.
 *
 * `single_idea` above is the claim; this is the reasoning that makes the claim
 * worth reading, and beat three - why the reader's current approach keeps
 * falling short - is the one that most often decides whether the copy lands.
 * Shown here because a brief is the only place it can be checked before an
 * email has been written from it. Beats the strategist left empty are left
 * out rather than rendered as blanks: an unfilled beat is a decision not to
 * invent one, not a missing value. */
function EmailArgument({
  email,
}: {
  email: {
    felt_need?: string;
    selection_reason?: string;
    next_step_url?: string;
    argument_issue?: string;
    status_quo?: string;
    why_it_fails?: string;
    mechanism?: string;
    next_step_decision?: string;
    next_step_value?: string;
    next_step_limit?: string;
  };
}) {
  const beats = [
    ["Why this proposition", email.selection_reason],
    ["Living with", email.felt_need],
    ["Does today", email.status_quo],
    ["Why that fails", email.why_it_fails],
    ["This instead", email.mechanism],
    ["CTA helps decide", email.next_step_decision],
    ["CTA delivers", email.next_step_value],
    ["CTA does not prove", email.next_step_limit],
    ["Destination", email.next_step_url],
    ["Needs review", email.argument_issue],
  ].filter(([, value]) => value) as [string, string][];
  if (beats.length === 0) return null;
  return (
    <ol className="mt-1 space-y-0.5 border-l border-border/60 pl-3 text-muted-foreground/70">
      {beats.map(([label, value]) => (
        <li key={label}>
          <span className="text-muted-foreground">{label}: </span>
          {value}
        </li>
      ))}
    </ol>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  if (!value) return null;
  return (
    <p>
      <span className="text-muted-foreground">{label}: </span>
      {value}
    </p>
  );
}

const SEVERITY_TEXT: Record<string, string> = {
  blocking: "text-destructive",
  major: "text-amber-400",
  minor: "text-muted-foreground",
};

const LEVEL_TEXT: Record<string, string> = {
  debug: "text-muted-foreground",
  info: "text-foreground",
  warning: "text-amber-400",
  error: "text-destructive",
};
