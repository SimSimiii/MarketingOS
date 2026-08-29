"use client";

import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { formatTokens } from "@/lib/format";
import type { StepState, TimelineStep } from "@/lib/run-timeline";
import type { LiveExecutionEvent } from "@/lib/types";
import { cn } from "@/lib/utils";

const STEP_STYLES: Record<StepState, { dot: string; label: string; badge: string }> = {
  running: { dot: "bg-primary animate-pulse", label: "working", badge: "bg-primary/20 text-primary" },
  completed: { dot: "bg-emerald-500", label: "done", badge: "bg-emerald-500/15 text-emerald-400" },
  failed: { dot: "bg-destructive", label: "failed", badge: "bg-destructive/15 text-destructive" },
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
      <p className="text-sm text-muted-foreground">
        Reading everything you provided before anything gets written...
      </p>
    );
  }

  return (
    <ol className="space-y-2">
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
  const lines = events.filter((event) => event.step === step.step);
  const tokens = step.inputTokens + step.outputTokens;
  // A finished step reports what it took; a running one has to keep moving,
  // or the page reads as frozen through a 40-second model call.
  const elapsedMs =
    step.state === "running" && step.startedAt
      ? now - new Date(step.startedAt).getTime()
      : step.durationMs;

  return (
    <Card size="sm" className={cn(open && "ring-foreground/20")}>
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={open}
        className="flex w-full items-start gap-3 px-(--card-spacing) text-left"
      >
        <span className={cn("mt-1.5 size-2 shrink-0 rounded-full", style.dot)} />
        <span className="min-w-0 flex-1 space-y-1">
          <span className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-medium">
              {step.agentName ?? step.agentId ?? "Working"}
            </span>
            <Badge variant="outline" className={cn("border-transparent", style.badge)}>
              {style.label}
            </Badge>
            <span className="text-xs text-muted-foreground">step {step.step}</span>
            {step.attempt > 1 && (
              <Badge variant="outline" className="border-transparent bg-amber-500/15 text-amber-400">
                rework - attempt {step.attempt}
              </Badge>
            )}
          </span>

          {step.label && (
            <span className="block text-sm text-muted-foreground">{step.label}</span>
          )}

          {step.progress && (
            <span className="block text-xs text-primary">{step.progress}</span>
          )}

          {step.error && <span className="block text-xs text-destructive">{step.error}</span>}

          {step.summary && (
            <span className="block text-xs text-emerald-400">{step.summary}</span>
          )}

          <span className="flex flex-wrap gap-x-3 text-xs text-muted-foreground tabular-nums">
            {step.model && <span>{step.model}</span>}
            {tokens > 0 && <span>{formatTokens(tokens)} tokens</span>}
            {elapsedMs > 0 && <span>{(elapsedMs / 1000).toFixed(1)}s</span>}
            <span className="text-muted-foreground/70">
              {lines.length} log line{lines.length === 1 ? "" : "s"}
            </span>
          </span>
        </span>
        <span className="mt-0.5 shrink-0 text-xs text-muted-foreground">{open ? "hide" : "logs"}</span>
      </button>

      {open && <StepLog lines={lines} />}
    </Card>
  );
}

function StepLog({ lines }: { lines: LiveExecutionEvent[] }) {
  const [showDebug, setShowDebug] = useState(true);
  const [expanded, setExpanded] = useState<Set<number>>(() => new Set());
  // Indices into `lines`, not into the filtered view: hiding the debug lines
  // must not silently re-point what is open at a different event.
  const visible = lines
    .map((line, index) => ({ line, index }))
    .filter(({ line }) => showDebug || line.level !== "debug");
  const expandable = visible.filter(({ line }) => hasDetail(line));

  const toggle = (index: number) =>
    setExpanded((current) => {
      const next = new Set(current);
      if (!next.delete(index)) next.add(index);
      return next;
    });

  return (
    <div className="mt-2 border-t border-border pt-2">
      <div className="flex items-center justify-between gap-3 px-(--card-spacing) pb-1">
        <span className="text-xs font-medium text-muted-foreground">Log</span>
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
          <button
            type="button"
            onClick={() => setShowDebug(!showDebug)}
            className="text-xs text-muted-foreground hover:text-foreground"
          >
            {showDebug ? "hide debug lines" : "show debug lines"}
          </button>
        </span>
      </div>
      <div className="max-h-[32rem] overflow-y-auto px-(--card-spacing)">
        {visible.length === 0 ? (
          <p className="py-2 text-xs text-muted-foreground">Nothing logged for this step yet.</p>
        ) : (
          <ul className="space-y-1 text-xs">
            {visible.map(({ line, index }) => {
              const detailed = hasDetail(line);
              const open = expanded.has(index);
              return (
                <li key={index}>
                  <div
                    className={cn(
                      "flex gap-2 font-mono",
                      detailed && "cursor-pointer rounded hover:bg-muted/50",
                    )}
                    onClick={detailed ? () => toggle(index) : undefined}
                  >
                    <span className="shrink-0 text-muted-foreground/60 tabular-nums">
                      {new Date(line.at).toLocaleTimeString()}
                    </span>
                    <span className={cn("min-w-0 flex-1", LEVEL_TEXT[line.level])}>
                      {line.message}
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
  email: { felt_need?: string; status_quo?: string; why_it_fails?: string; mechanism?: string };
}) {
  const beats = [
    ["Living with", email.felt_need],
    ["Does today", email.status_quo],
    ["Why that fails", email.why_it_fails],
    ["This instead", email.mechanism],
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
