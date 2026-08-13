export type ExecutionStatus = "pending" | "running" | "completed" | "failed" | "cancelled";
export type CampaignStatus = "active" | "archived";
export type PolicyPreset = "fast" | "balanced" | "maximum";
export type SourceType =
  | "website"
  | "markdown"
  | "plain_text"
  | "pdf"
  | "docx"
  | "json"
  | "image"
  | "video"
  | "audio";
export type AssetType = "email" | "social_post" | "ad" | "blog" | "landing_page";
export type LogLevel = "debug" | "info" | "warning" | "error";

export interface Campaign {
  id: string;
  name: string;
  /** What the user asked for, in their own words. */
  request: string;
  product_description: string;
  product_url: string | null;
  target_market: string | null;
  goals: string | null;
  /** The business this campaign belongs to. Set => knowledge is compiled once
   * for the brand and reused by every campaign attached to it. */
  brand_id: string | null;
  status: CampaignStatus;
  archived_at: string | null;
  /** {"preset": "fast" | "balanced" | "maximum", ...field overrides} or null. */
  policy: Record<string, unknown> | null;
  model_overrides: Record<string, string> | null;
  created_at: string;
  updated_at: string;
  /** Status of the most recent run; null when the campaign never ran. */
  last_run_status: ExecutionStatus | null;
  last_run_at: string | null;
}

export interface CampaignCreateRequest {
  name: string;
  request: string;
  product_description: string;
  product_url?: string | null;
  target_market?: string | null;
  goals?: string | null;
  brand_id?: string | null;
  policy_preset?: PolicyPreset | null;
  model_overrides?: Record<string, string> | null;
}

/** A business whose knowledge is compiled once and reused by every campaign
 * attached to it, instead of being recompiled (and re-billed) per campaign. */
export interface Brand {
  id: string;
  name: string;
  website_url: string | null;
  /** How this brand's emails look once rendered. All optional - a brand with
   * none of it set still renders, in the typographic tier. */
  logo_url: string | null;
  primary_color: string | null;
  footer_lines: string[] | null;
  created_at: string;
  updated_at: string;
}

export interface BrandCreateRequest {
  name: string;
  website_url?: string | null;
}

export interface BrandStyleUpdate {
  logo_url?: string | null;
  primary_color?: string | null;
  footer_lines?: string[] | null;
}

export type Grounding = "grounded" | "inferred" | "user_stated";
export type EvidenceStrength = "strong" | "moderate" | "weak";

/** One thing established about the business, with where it came from. */
export interface KnowledgeFact {
  statement: string;
  grounding: Grounding;
  provenance: { source: string; quote: string; document_id: string | null } | null;
}

/** One thing the copy is allowed to assert, and the text that proves it. */
export interface EvidenceEntry {
  id: string;
  kind: string;
  claim: string;
  verbatim: string;
  source: string;
  strength: EvidenceStrength;
  user_attested: boolean;
}

export interface AudienceSegment {
  name: string;
  situation: string;
  job_to_be_done: string;
  trigger: string;
  sophistication: string;
  pains: KnowledgeFact[];
}

export interface AudienceObjection {
  objection: string;
  severity: string;
  answer: string;
  grounding: Grounding;
  evidence_ids: string[];
}

export interface KnowledgeGap {
  id: string;
  missing: string;
  impact: string;
  question: string;
  severity: string;
  answer: string;
}

/** The full compiled bundle for one brand - what every campaign for it is
 * actually written from. Mirrors app.knowledge.artifacts.KnowledgeArtifacts. */
export interface KnowledgeArtifactsDetail {
  business: {
    company_name: string;
    what_it_does: string;
    category: string;
    business_model: string;
    facts: KnowledgeFact[];
    vocabulary: string[];
  };
  offer: {
    plans: { name: string; price: string; includes: string[] }[];
    free_entry: string;
    guarantees: string[];
    calls_to_action: { label: string; intent: string; url: string | null }[];
    purchase_motion: string;
  };
  evidence: { entries: EvidenceEntry[] };
  voice: {
    learned: boolean;
    tone: string;
    rhythm: string;
    person: string;
    greetings: string[];
    sign_offs: string[];
    exemplars: string[];
    prefer_words: string[];
    avoid_words: string[];
  };
  audience: { segments: AudienceSegment[]; objections: AudienceObjection[] };
  gaps: { gaps: KnowledgeGap[] };
}

/** What the system currently knows about a brand, and how confident it is. */
export interface BrandKnowledge {
  version: number;
  compiled_at: string;
  evidence_count: number;
  segments: string[];
  gaps: string[];
  voice_learned: boolean;
  artifacts: KnowledgeArtifactsDetail;
}

export interface CampaignPolicyUpdate {
  preset?: PolicyPreset | null;
  overrides?: Record<string, unknown> | null;
}

export interface AgentExecution {
  id: string;
  agent_id: string;
  agent_name: string;
  sequence_order: number;
  status: ExecutionStatus;
  input_data: Record<string, unknown> | null;
  output_data: Record<string, unknown> | null;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  model: string | null;
  input_tokens: number;
  output_tokens: number;
  /** Input written to and read from the prompt cache. With the Claude Code CLI
   * this is most of a step's input - `input_tokens` alone is the uncached
   * remainder and reads as single digits beside a 30,000-character prompt. */
  cache_creation_input_tokens: number;
  cache_read_input_tokens: number;
  /** What this step cost, provider-reported where the provider said. */
  cost_usd: number;
  duration_ms: number;
  attempt: number;
}

/** A finished deliverable, ready to copy and paste. */
export interface GeneratedAsset {
  id: string;
  asset_type: AssetType;
  title: string;
  content: string;
  /** The same deliverable rendered as HTML, or null for assets that are not
   * emails and for emails written before rendering existed. */
  content_html: string | null;
  position: number;
  asset_metadata: Record<string, unknown> | null;
  created_at: string;
}

export interface CampaignExecution {
  id: string;
  campaign_id: string;
  status: ExecutionStatus;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  /** Every input token the run consumed, cached input included - what quota
   * actually paid for. Runs recorded before true accounting landed carry only
   * the uncached fraction and will read implausibly low. */
  total_input_tokens: number;
  total_output_tokens: number;
  total_cache_read_tokens: number;
  estimated_cost_usd: number;
}

export interface CampaignExecutionDetail extends CampaignExecution {
  agent_executions: AgentExecution[];
  assets: GeneratedAsset[];
}

export interface CampaignResult extends CampaignExecutionDetail {
  result: Record<string, unknown> | null;
}

/** As returned by list endpoints - metadata only, no extracted text. An
 * ingested PDF or site can be hundreds of KB, so the API deliberately omits
 * `content` from lists (see KnowledgeDocumentSummary on the backend). */
export interface KnowledgeDocument {
  id: string;
  campaign_id: string | null;
  brand_id: string | null;
  title: string;
  source_type: SourceType;
  source_url: string | null;
  word_count: number;
  created_at: string;
}

/** A single document fetched by id, including the extracted text. */
export interface KnowledgeDocumentDetail extends KnowledgeDocument {
  content: string;
}

export interface KnowledgeSourceCreate {
  campaign_id?: string | null;
  brand_id?: string | null;
  title?: string | null;
  url?: string | null;
  content?: string | null;
  crawl?: boolean;
  max_pages?: number;
}

export interface UserSettings {
  id: string;
  company_name: string | null;
  brand_voice: string | null;
  default_ai_provider: string;
  default_model: string;
  updated_at: string;
}

export interface UserSettingsUpdate {
  company_name?: string | null;
  brand_voice?: string | null;
  default_ai_provider?: string | null;
  default_model?: string | null;
}

export interface ExecutionLog {
  id: string;
  campaign_execution_id: string | null;
  agent_execution_id: string | null;
  /** Which role emitted this line ("email_writer", "blind_reader", ...). */
  agent_id: string | null;
  /** The role turn it belongs to. */
  step: number | null;
  event_type: string | null;
  level: LogLevel;
  message: string;
  created_at: string;
}

/** A run currently in flight, named - what the live dashboard lists. */
export interface RunningExecution extends CampaignExecution {
  campaign_name: string;
  campaign_request: string;
}

/** Fields every live event carries, whatever its type. */
interface LiveEventBase {
  execution_id: string;
  /** Whose lane this belongs to; null for run-level events. */
  agent_id: string | null;
  /** Which role turn, so the UI can group a role's lines with its step. */
  step: number | null;
  level: LogLevel;
  /** Human sentence - always safe to render on its own. */
  message: string;
  /** ISO timestamp of the moment it happened. */
  at: string;
}

/** One event on the live execution stream (GET /executions/{id}/stream).
 *
 * The same payloads come back from GET /executions/{id}/timeline, which is
 * how a page that reloaded mid-run rebuilds what it missed. */
export type LiveExecutionEvent = LiveEventBase &
  (
    | { type: "execution_started"; request: string }
    /** Where the run is, between and inside phases. Carries no step of its own
     * when it is about the run rather than about one role's turn. */
    | { type: "phase"; phase: string }
    | {
        type: "knowledge_ready";
        reused: boolean;
        version: number;
        evidence_count: number;
        segments: string[];
        gaps: string[];
        voice_learned: boolean;
      }
    | {
        type: "brief_ready";
        reader: string;
        /** The audience segment the brief chose, and therefore the person
         * every draft in this run is read cold by. */
        reader_segment: string;
        promise: string;
        arc: string;
        emails: {
          position: number;
          job: string;
          single_idea: string;
          objection: string;
          evidence_ids: string[];
          /** What this email deliberately leaves out, though it could say it. */
          must_not_say?: string[];
        }[];
      }
    /** One role's turn: a writer draft, a cold read, a critique. */
    | { type: "agent_started"; agent_name: string; label: string }
    | {
        type: "gates";
        position: number;
        attempt: number;
        passed: boolean;
        issues?: { gate: string; detail: string; severity: string }[];
      }
    /** One draft exactly as the writer emitted it, including the bake-off
     * candidates that lost. The body is what makes "rewrite 2" reviewable. */
    | {
        type: "draft";
        position: number;
        attempt: number;
        subject: string;
        preview_text: string;
        greeting: string;
        body: string;
        call_to_action: string;
        sign_off: string;
        postscript: string;
        word_count: number;
      }
    | {
        type: "critique";
        position: number;
        attempt: number;
        verdict: "ship" | "revise";
        brief_drift: string;
        /** Ledger ids this email was assigned and did not use. */
        unspent_evidence: string[];
        critique_summary: string;
        edits: {
          line: string;
          problem: string;
          fix: string;
          severity: "blocking" | "major" | "minor";
        }[];
      }
    | {
        type: "email_ready";
        position: number;
        subject: string;
        pull: number;
        attempts: number;
        clean: boolean;
      }
    | {
        type: "sequence_review";
        passed: boolean;
        rework: Record<string, string[]>;
        summary: string;
      }
    | {
        type: "campaign_report";
        delivered: number;
        promised: number;
        average_pull: number;
        contract_violations: string[];
        limiting_gaps: string[];
        /** Positions a cold reader would still not have clicked. */
        below_floor: number[];
        what_would_help_most: string;
      }
    | { type: "model_call_started"; model: string; prompt_chars: number }
    | {
        type: "model_call_finished";
        model: string;
        /** Billable input: uncached plus cache-write plus cache-read. */
        input_tokens: number;
        output_tokens: number;
        cache_read_input_tokens?: number;
        cost_usd?: number;
        duration_ms: number;
        response_chars: number;
      }
    | {
        type: "agent_completed";
        agent_name: string;
        agent_execution_id: string;
        model: string | null;
        /** Billable input for the whole step, cached input included. */
        input_tokens: number;
        output_tokens: number;
        cache_read_input_tokens?: number;
        cost_usd?: number;
        duration_ms: number;
        attempt: number;
        /** What this turn produced, in a phrase - "Pull 8/10 - would click today". */
        summary: string;
        assets_produced: { title: string; position: number }[];
      }
    | {
        type: "agent_failed";
        agent_name: string;
        agent_execution_id: string;
        error: string;
        attempt: number;
      }
    /** A cold reader's verdict on one draft. `conversion_score` is the panel's
     * pull (0-10) - how much the email made them want the thing.
     *
     * The flat fields are the first reader's answers; `readers` is everyone
     * who read it, which is the variance a panel is bought for. */
    | {
        type: "review";
        approved: boolean;
        conversion_score: number;
        summary: string;
        issues: string[];
        position: number;
        attempt: number;
        biggest_doubt: string;
        stopped_at: string;
        readers?: {
          persona: string;
          /** False when this reader never came back - no verdict, not a zero. */
          reported: boolean;
          opened: boolean;
          pull: number;
          would_act: boolean;
          what_it_sells: string;
          biggest_doubt: string;
          stopped_at: string;
          fixes: string[];
        }[];
      }
    | { type: "execution_finished"; status: ExecutionStatus }
    /** Anything the backend adds later still renders as its message. */
    | { type: "log" }
  );

/** Replay of a run plus the position to resume its live stream from. */
export interface ExecutionTimeline {
  execution_id: string;
  events: LiveExecutionEvent[];
  last_event_id: number;
  is_running: boolean;
}
