/** Presentation only: keep diagnostics intact, but describe work in customer terms.
 * Used for both saved history and current progress, including older job receipts. */
export function executionReview(status: string, result: Record<string, unknown> | null, error: string | null) {
  const report = (result?.report ?? {}) as { delivered?: number; promised?: number; emails?: { clean?: boolean; landed?: boolean; understood?: boolean; unresolved?: unknown[] }[] };
  const reasons: string[] = [];
  const partial = (report.delivered ?? 0) < (report.promised ?? 0);
  if (status === "completed") {
    if (error) reasons.push("The run retained drafts after an interrupted step.");
    if (partial) reasons.push("Some requested deliverables are missing.");
    if (report.emails?.some((email) => email.clean === false)) reasons.push("Some drafts retain unresolved automatic checks.");
    else if (report.emails?.some((email) => email.unresolved?.length)) reasons.push("Some drafts retain unresolved strategy or review findings.");
    if (report.emails?.some((email) => email.landed === false || email.understood === false)) reasons.push("Some drafts still need editorial review.");
    if (["degraded", "budget_exhausted", "cancelled", "failed"].includes(String(result?.run_status)) && !reasons.length) reasons.push("The run finished with unresolved review requirements.");
  }
  return { needsReview: reasons.length > 0, label: reasons.length ? (partial ? "Partial delivery" : "Drafts need review") : undefined, reasons };
}

const ACTIVITIES: Record<string, string> = {
  knowledge_compiler: "Preparing brand knowledge",
  strategist: "Planning the campaign",
  email_writer: "Writing the email",
  conversion_critic: "Reviewing the argument",
  blind_reader: "Checking reader understanding",
  preference_judge: "Comparing drafts",
  sequence_reviewer: "Reviewing the sequence",
  subject_writer: "Writing subject lines",
  inbox_scanner: "Reviewing subject lines",
  proof_hunter: "Finding supporting evidence",
  rival_scout: "Finding competitors",
  rival_profiler: "Reviewing competitor offers",
  audience_cartographer: "Identifying potential buyers",
  audience_researcher: "Researching the audience",
  material_researcher: "Checking product information",
  prospect_researcher: "Researching potential customers",
  linkedin_writer: "Writing the message",
};

export function activityLabel(role?: string | null): string {
  return ACTIVITIES[role ?? ""] ?? "Campaign preparation";
}

// Match diagnostic formats, not isolated product words such as “tokens” or
// “Claude”: those may legitimately be part of the customer's own offering.
const RECEIPT = /[\d,]+ in \/ [\d,]+ out| · step completed$/i;
const DIAGNOSTIC = /\b(?:input_tokens|output_tokens|cache_read_tokens|prompt_chars|response_chars|ProviderError|ModelRuntimeError|Traceback|codex exec|web_fetch|API[- ]key)\b|\b(?:sent|received) [\d,]+ characters\b|\b(?:gpt-[\w.-]+|claude-[\w.-]+)\b|\b(?:model|provider|CLI|schema|transport) (?:call|error|failed|failure|unavailable|timeout|retry|retries)\b|\b[\d,]+ (?:input|output|cached) tokens\b/i;

export function progressText(message: string | null | undefined, fallback = "Preparing the next step…"): string {
  if (!message) return fallback;
  message = message.replace(/\s*[-–—]\s*\d+(?:[.,]\d+)?% of them are estimated to bite\b/gi,
    " — selected audience hypothesis; response is unmeasured");
  return RECEIPT.test(message) || DIAGNOSTIC.test(message) ? fallback : message;
}

export function problemText(message: string | null | undefined): string {
  if (message && /\b(?:sonnet|opus|haiku|fable5|anthropic|openai|codex|claude|gemini|validationerror|pydantic|stderr|stack trace)\b/i.test(message)) {
    return "This step could not finish. Please retry; if it keeps failing, contact support.";
  }
  return progressText(message, "This step could not finish. Please retry; if it keeps failing, contact support.");
}

export function jobProgress(lines: string[]): string[] {
  return lines.filter((line) => !RECEIPT.test(line)).map((line) =>
    /\b(?:failed|error|exception|timeout|timed out|unavailable|did not answer|retry)\b/i.test(line)
      ? problemText(line)
      : progressText(line),
  );
}

type ActivityEvent = {
  type?: string;
  event_type?: string | null;
  level: string;
  agent_id: string | null;
  message: string;
};

/** Transport chatter is omitted entirely; warnings still explain recovery. */
export function activityMessage(event: ActivityEvent): string | null {
  const type = event.type ?? event.event_type;
  if (type === "model_call_retried") return "This step was interrupted. Retrying automatically…";
  if (type === "agent_failed" || type === "run_error") return problemText(event.message);
  if (type === "model_call_started" || type === "model_call_finished" || event.level === "debug") return null;
  if (type === "agent_started") return `${activityLabel(event.agent_id)}…`;
  if (type === "agent_completed") return `${activityLabel(event.agent_id)} · complete`;
  if (event.level === "error" || event.level === "warning") return problemText(event.message);
  return progressText(event.message, "Campaign progress updated.");
}
