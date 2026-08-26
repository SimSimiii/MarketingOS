import type { ExecutionStatus, LiveExecutionEvent } from "@/lib/types";

/** One role's turn is the unit of the story: a writer draft, a cold read, a
 * critique. An email that gets rewritten appears as several steps, which is
 * the point - the rework loop is what the user is paying for and it used to be
 * invisible. */
export type StepState = "running" | "completed" | "failed";

export interface TimelineStep {
  step: number;
  /** What this role was asked to do - "Email 2 · rewrite 1". */
  label: string | null;
  agentId: string | null;
  agentName: string | null;
  state: StepState;
  attempt: number;
  model: string | null;
  inputTokens: number;
  outputTokens: number;
  durationMs: number;
  error: string | null;
  /** What the role produced, once it is done. */
  summary: string | null;
  /** The most recent progress line, shown while the step is still running -
   * this is what fills the half-minute a single model call takes. */
  progress: string | null;
  startedAt: string | null;
  endedAt: string | null;
}

/** A cold reader's reaction to one draft. */
export interface ReadVerdict {
  position: number;
  attempt: number;
  pull: number;
  landed: boolean;
  whatItSells: string;
  biggestDoubt: string;
  fixes: string[];
}

/** One finished email, as the run reported it. */
export interface EmailReady {
  position: number;
  subject: string;
  pull: number;
  attempts: number;
  clean: boolean;
}

export interface RunState {
  steps: TimelineStep[];
  /** Every cold read in the run, in order. The last one per position is the
   * verdict that shipped. */
  reads: ReadVerdict[];
  emails: EmailReady[];
  /** What the system knows about this business, once the knowledge phase is
   * done - null while it is still working. */
  knowledge: {
    reused: boolean;
    version: number;
    evidenceCount: number;
    segments: string[];
    gaps: string[];
    voiceLearned: boolean;
    /** What the compile read but could not use. */
    notes: string[];
  } | null;
  /** Who this campaign decided to write to, once the brief exists. The
   * compiled segment list is who *could* be written to, which is a different
   * question and reads as a hedge when shown in its place. */
  reader: { description: string; segment: string } | null;
  /** Set once the run reaches a terminal state; null while it is still going. */
  finalStatus: ExecutionStatus | null;
  inputTokens: number;
  outputTokens: number;
}

const EMPTY_STEP = (step: number, at: string): TimelineStep => ({
  step,
  label: null,
  agentId: null,
  agentName: null,
  state: "running",
  attempt: 1,
  model: null,
  inputTokens: 0,
  outputTokens: 0,
  durationMs: 0,
  error: null,
  summary: null,
  progress: null,
  startedAt: at,
  endedAt: null,
});

/** Fold the event stream into what the page renders.
 *
 * Pure and order-dependent but not order-*sensitive* in the harmful sense:
 * replaying the same events from the timeline endpoint and receiving them
 * live produce the same result, which is what lets a reload be seamless.
 */
export function reduceRun(events: LiveExecutionEvent[]): RunState {
  const steps = new Map<number, TimelineStep>();
  const reads: ReadVerdict[] = [];
  const emails = new Map<number, EmailReady>();
  let knowledge: RunState["knowledge"] = null;
  let reader: RunState["reader"] = null;
  let finalStatus: ExecutionStatus | null = null;
  let inputTokens = 0;
  let outputTokens = 0;

  const stepFor = (event: LiveExecutionEvent): TimelineStep | null => {
    if (event.step === null) return null;
    const existing = steps.get(event.step);
    if (existing) return existing;
    const created = EMPTY_STEP(event.step, event.at);
    steps.set(event.step, created);
    return created;
  };

  for (const event of events) {
    const current = stepFor(event);

    switch (event.type) {
      case "agent_started":
        if (!current) break;
        current.agentId = event.agent_id;
        current.agentName = event.agent_name;
        current.label = event.label;
        current.state = "running";
        break;

      case "phase":
      case "model_call_started":
        if (!current) break;
        current.progress = event.message;
        if (event.type === "model_call_started") current.model = event.model;
        break;

      case "model_call_finished":
        if (!current) break;
        current.progress = event.message;
        current.model = event.model;
        break;

      case "agent_completed":
        if (!current) break;
        current.state = "completed";
        current.agentName = event.agent_name;
        current.attempt = event.attempt;
        current.model = event.model;
        current.inputTokens = event.input_tokens;
        current.outputTokens = event.output_tokens;
        current.durationMs = event.duration_ms;
        current.summary = event.summary ?? null;
        current.progress = null;
        current.endedAt = event.at;
        break;

      case "agent_failed":
        if (!current) break;
        current.state = "failed";
        current.agentName = event.agent_name;
        current.attempt = event.attempt;
        current.error = event.error;
        current.progress = null;
        current.endedAt = event.at;
        break;

      case "knowledge_ready":
        knowledge = {
          reused: event.reused,
          version: event.version,
          evidenceCount: event.evidence_count,
          segments: event.segments,
          gaps: event.gaps,
          voiceLearned: event.voice_learned,
          notes: event.notes ?? [],
        };
        break;

      case "brief_ready":
        reader = { description: event.reader, segment: event.reader_segment };
        break;

      case "review":
        reads.push({
          position: event.position,
          attempt: event.attempt,
          pull: event.conversion_score,
          landed: event.approved,
          whatItSells: event.summary,
          biggestDoubt: event.biggest_doubt,
          fixes: event.issues,
        });
        break;

      case "email_ready":
        emails.set(event.position, {
          position: event.position,
          subject: event.subject,
          pull: event.pull,
          attempts: event.attempts,
          clean: event.clean,
        });
        break;

      case "execution_finished":
        finalStatus = event.status;
        break;
    }

    // Token spend is counted from the model calls themselves rather than the
    // agent rows, so a step that is still in flight already contributes.
    if (event.type === "model_call_finished") {
      inputTokens += event.input_tokens;
      outputTokens += event.output_tokens;
    }
  }

  return {
    steps: [...steps.values()].sort((a, b) => a.step - b.step),
    reads,
    emails: [...emails.values()].sort((a, b) => a.position - b.position),
    knowledge,
    reader,
    finalStatus,
    inputTokens,
    outputTokens,
  };
}

/** Prices mirror backend/app/ai/models.py - an estimate for the user's own
 * budgeting while the run is live, not an invoice. */
const COST_PER_1K: Record<string, [input: number, output: number]> = {
  haiku: [0.001, 0.005],
  sonnet: [0.003, 0.015],
  opus: [0.015, 0.075],
  fable5: [0.003, 0.015],
};

export function estimateCost(steps: TimelineStep[]): number {
  return steps.reduce((total, step) => {
    const [input, output] = COST_PER_1K[step.model ?? "sonnet"] ?? COST_PER_1K.sonnet;
    return total + (step.inputTokens / 1000) * input + (step.outputTokens / 1000) * output;
  }, 0);
}

/** How many turns each role has taken so far. Feeds the "attempt 2" line - a
 * rewrite is the normal path here, not an error. */
export function runsPerRole(steps: TimelineStep[]): Map<string, number> {
  const counts = new Map<string, number>();
  for (const step of steps) {
    if (!step.agentId) continue;
    counts.set(step.agentId, (counts.get(step.agentId) ?? 0) + 1);
  }
  return counts;
}
