export type ExecutionStatus = "pending" | "running" | "completed" | "failed" | "cancelled";
export type CampaignStatus = "active" | "archived";
export type PolicyPreset = "fast" | "balanced" | "maximum";
/** How designed a finished email looks.
 *
 * "plain" is typography only and is the right answer for cold outreach — a
 * branded template reads as a mailshot and converts worse there. "branded"
 * adds the logo, the accent colour, a real button and a footer, which is the
 * honest signal for mail a reader expects to come from a company. */
export type EmailTier = "plain" | "branded";
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
  /** Who the emails are from. Without it the writer signs off as the company,
   * which reads as a broadcast because it is one. */
  sender_name: string | null;
  sender_role: string | null;
  /** The business this campaign belongs to. Set => knowledge is compiled once
   * for the brand and reused by every campaign attached to it. */
  brand_id: string | null;
  /** The audience segment from the brand's map this campaign is written to,
   * or null for "whoever the company's own site describes". The one field on
   * the form that changes who the emails are for. */
  audience_segment: string | null;
  /** Where the call to action points. Falls back to the brand's website; with
   * neither, the CTA renders as a marked slot rather than a dead button. */
  cta_url: string | null;
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
  sender_name?: string | null;
  sender_role?: string | null;
  brand_id?: string | null;
  audience_segment?: string | null;
  cta_url?: string | null;
  /** Omitted/null takes the system default, which is "plain". */
  email_tier?: EmailTier | null;
  policy_preset?: PolicyPreset | null;
  model_overrides?: Record<string, string> | null;
  /** Re-read and recompile the brand's knowledge even if nothing has changed
   * since the last compile. Omitted/null defers to the pipeline's default
   * (reuse what's already compiled). */
  force_recompile?: boolean | null;
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
  /** Where the branded footer's "Unsubscribe" points. The line renders only
   * when this is set — a dead unsubscribe link is what turns an unsubscribe
   * into a spam report. */
  unsubscribe_url: string | null;
  created_at: string;
  updated_at: string;
}

/** One brand as the brand list shows it: the state of its own workspace.
 *
 * Counts rather than payloads, so a list of businesses costs one request
 * instead of three per card. Everything here is scoped to the brand - there is
 * no source, competitor or alert that belongs to all of them. */
export interface BrandOverview extends Brand {
  sources: number;
  campaigns: number;
  /** Latest compiled knowledge version, or null when nothing was compiled yet
   * - which happens on the first campaign run, not on registration. */
  knowledge_version: number | null;
  compiled_at: string | null;
  /** Competitors the user has not muted. */
  rivals: number;
  scanned_at: string | null;
  pending_proof: number;
  unseen_alerts: number;
}

export interface BrandCreateRequest {
  name: string;
  website_url?: string | null;
}

export interface BrandStyleUpdate {
  logo_url?: string | null;
  primary_color?: string | null;
  footer_lines?: string[] | null;
  unsubscribe_url?: string | null;
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

/** Which shelf of the knowledge base a fact sits on - the department of the
 * business it belongs to, and so the buyer question it answers. Mirrors
 * app.knowledge.taxonomy.FactCategory. */
export type FactCategory =
  | "proof"
  | "commercial"
  | "product"
  | "technical"
  | "trust"
  | "market"
  | "operations"
  | "company"
  | "brand";

/** What a fact is for in a campaign. Coarser than the score on purpose: the
 * difference between 71 and 68 is noise, the difference between "lead an email
 * with this" and "supporting line" is a decision. */
export type ValueBand = "headline" | "supporting" | "background";

/** Which compiled artifact a fact was lifted out of. Only `evidence` entries
 * carry an id a copywriter may cite; everything else is context. */
export type EntryOrigin = "evidence" | "profile" | "offer" | "audience" | "voice";

/** One thing known about the business, on a shelf, with a price on it. */
export interface KnowledgeEntry {
  id: string;
  category: FactCategory;
  statement: string;
  /** The text from the user's own material that supports this. Empty for
   * inferred entries - which is what `grounding` is next to it for. */
  verbatim: string;
  source: string;
  document_id: string | null;
  origin: EntryOrigin;
  kind: string;
  grounding: Grounding;
  strength: string;
  /** 0-100. See app.knowledge.taxonomy.assess_value. */
  value: number;
  band: ValueBand;
  /** Why it scored that, in plain sentences - a ranking nobody can
   * interrogate is a ranking nobody believes. */
  why: string[];
  /** Whether a writer may cite this id in copy. True only for evidence. */
  citable: boolean;
  tags: string[];
}

export interface KnowledgeShelf {
  category: FactCategory;
  label: string;
  blurb: string;
  buyer_question: string;
  sells_by: string;
  /** What it costs this business that the shelf is empty. The most useful
   * line on the page when it is. */
  when_empty: string;
  count: number;
  headline_count: number;
  entries: KnowledgeEntry[];
}

/** Everything compiled about one business, classified onto shelves. */
export interface KnowledgeBase {
  brand_id: string | null;
  campaign_id: string | null;
  version: number;
  compiled_at: string | null;
  total: number;
  citable_total: number;
  headline_total: number;
  shelves: KnowledgeShelf[];
  open_questions: string[];
}

export interface CampaignPolicyUpdate {
  preset?: PolicyPreset | null;
  overrides?: Record<string, unknown> | null;
  /** How designed the finished emails look. Accepted here as well as on
   * creation because it is the one presentation decision a user changes their
   * mind about after seeing a run, and re-running is cheap where re-creating
   * the campaign is not. Omit to leave the stored tier alone. */
  email_tier?: EmailTier | null;
  /** Per-agent model pins, `{role_id: model}`. Omit to leave the stored pins
   * alone; send `{}` to clear them and hand every agent back to the preset. */
  model_overrides?: Record<string, string> | null;
}

export type ModelVendor = "anthropic" | "openai";
export type ModelTier = "fast" | "balanced" | "deep";
export type RolePhase = "knowledge" | "campaign" | "market";

/** One model the picker can offer. Served by the backend rather than listed
 * here: a copy in TypeScript is a copy that disagrees with the router. */
export interface ModelOption {
  id: string;
  vendor: ModelVendor;
  label: string;
  blurb: string;
  /** The tier this model is the automatic choice for, if any. */
  default_for: ModelTier | null;
  /** Capability names (`web_search`, `web_fetch`). */
  tools: string[];
  /** A plan or install this model needs, when it needs one. */
  requires: string | null;
}

/** One agent a model can be pinned to. */
export interface AgentOption {
  id: string;
  label: string;
  blurb: string;
  phase: RolePhase;
  /** What this agent resolves to when nothing is pinned. */
  tier: ModelTier;
  /** Non-empty means the agent reads the open web, which narrows the models
   * that can run it. */
  tools: string[];
}

export interface ModelCatalog {
  models: ModelOption[];
  agents: AgentOption[];
  tier_defaults: Record<ModelTier, string>;
  /** The role id meaning "every agent" - the blanket override. */
  wildcard: string;
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

/** What a run will cost, before it is bought. The call count is arithmetic -
 * nothing in the pipeline spends a model call deciding what happens next - and
 * the money is what this user's own past runs on this preset actually came to,
 * never a price list. */
export interface RunForecast {
  preset: string;
  emails: number;
  /** False when the user named no number, so `emails` is the working
   * assumption rather than a promise. */
  count_is_explicit: boolean;
  /** The run where every email lands first time. */
  low: number;
  /** The run that buys every rewrite and rework it is allowed. */
  high: number;
  compile_low: number;
  compile_high: number;
  /** True when nothing attached has changed since the last compile, so this
   * run reads none of it again. */
  knowledge_reused: boolean;
  /** Finished runs on this preset that actually delivered. Zero means no
   * figure is offered, not a figure of zero - a run that died on its first
   * call is not counted. */
  observed_runs: number;
  /** What one delivered email cost on the middle run. Per email because past
   * runs were different lengths; the median because a run that died two calls
   * in and one that bought every rewrite are both real and neither is what to
   * plan around. */
  observed_cost_per_email: number;
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
        /** What the compile could not use - candidate facts whose quote was
         * not really in the source, readings that never came back, material
         * past the reading budget. A thin ledger has two very different
         * causes and only one of them is the business's fault. */
        notes?: string[];
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

// --------------------------------------------------------------------- market

/** The dimension a claim competes on. A closed list on the backend - see
 * app.market.claims.ClaimAxis - because positioning is arithmetic over these
 * and an open taxonomy is one nothing can compare across. */
export type ClaimAxis =
  | "speed"
  | "price"
  | "breadth"
  | "quality"
  | "effort"
  | "control"
  | "security"
  | "proof"
  | "support"
  | "other";

/** Who holds an axis. The whole strategic payload of a scan. */
export type Territory = "open" | "contested" | "table_stakes" | "exposed";

export type RivalKind = "alternative" | "incumbent" | "status_quo";
export type ProofStatus = "pending" | "approved" | "rejected";
export type RadarSeverity = "acts_on_copy" | "notable" | "routine";

/** One competitor on the brand's list. Editable by the user, and the edits
 * survive every rescan. */
export interface Rival {
  id: string;
  name: string;
  url: string;
  kind: RivalKind;
  why: string;
  /** "user" or "scout" - "you told us this" and "we found this" are different
   * claims and the page says which. */
  added_by: string;
  muted: boolean;
  created_at: string;
}

export interface RivalCreateRequest {
  name: string;
  url?: string;
  kind?: RivalKind;
  why?: string;
}

export interface Claim {
  text: string;
  verbatim: string;
  source: string;
  axis: ClaimAxis;
  /** Whether there is a figure, a limit or a name in it a reader could check.
   * The difference between "25 models across 9 providers" and "the broadest
   * coverage available". */
  specific: boolean;
}

/** One competitor as read from their own pages. */
export interface RivalProfile {
  name: string;
  url: string;
  kind: RivalKind;
  why: string;
  one_liner: string;
  promise: string;
  pricing: string;
  free_entry: string;
  icp: string;
  /** False when their site could not be read - everything else is empty by
   * construction and the page must say so rather than show a blank profile. */
  verified: boolean;
  pages_read: number;
  /** Claims the extractor produced that were not really on the page, and were
   * discarded. A profile that lost several is one to distrust. */
  unverified_claims: number;
  note: string;
  checked_at: string;
  claims: Claim[];
  proof_shown: Claim[];
}

export interface AxisReading {
  axis: ClaimAxis;
  territory: Territory;
  /** True when we are the only one on this axis carrying a checkable figure,
   * which is what makes a crowded axis ours anyway. */
  only_specific: boolean;
  ours: Claim[];
  theirs: Record<string, Claim[]>;
}

export interface Positioning {
  summary: string;
  rivals_profiled: number;
  rivals_with_proof: number;
  we_have_proof: boolean;
  /** Every competitor shows a named customer and we show none. The most
   * expensive asymmetry in cold email, and the one a user can fix in an
   * afternoon. */
  proof_deficit: boolean;
  crowd_words: string[];
  readings: AxisReading[];
  /** The section the strategist is actually planned against, rendered. Shown
   * verbatim: the point is that the user can read what the machine was told. */
  brief_for_strategy: string;
}

export interface MarketRead {
  brand_id: string;
  scanned_at: string | null;
  positioning: Positioning | null;
  profiles: RivalProfile[];
  rivals: Rival[];
  pending_proof: number;
  unseen_alerts: number;
  /** How much of the demand side exists. Counts rather than payloads, so the
   * brand shell can badge a tab without fetching the map. */
  audience_segments: number;
  prospects: number;
  /** Why the page is empty, when it is. */
  note: string;
}

/** Something the web says about this brand, waiting for a human to confirm it. */
export interface ProofCandidate {
  id: string;
  kind: string;
  claim: string;
  /** The exact sentence on the page. Approving it licenses these words in a
   * finished email, which is why a person decides and not a score. */
  verbatim: string;
  url: string;
  attributed_to: string;
  venue: string;
  confidence: number;
  /** Why this might not be what it looks like. What makes the decision take
   * ten seconds instead of ten minutes. */
  caveat: string;
  status: ProofStatus;
  /** The ledger id it became when approved (P1, P2, ...). */
  evidence_id: string;
  found_at: string;
  decided_at: string | null;
}

export interface RadarEvent {
  id: string;
  headline: string;
  detail: string;
  severity: RadarSeverity;
  rival: string;
  axis: string;
  what_to_do: string;
  created_at: string;
  seen_at: string | null;
}


/** How a mapped buyer was arrived at.
 *
 * Everything except `core` is a buyer the company's own material would never
 * have produced, which is the entire reason to map demand: a list the user
 * recognises in full cost them a search to restate their own homepage. */
export type SegmentKind =
  | "core"
  | "adjacent"
  | "influencer"
  | "channel"
  | "triggered"
  | "unintended";

export type ContactKind = "email" | "phone" | "form" | "social";
export type ProspectStatus = "new" | "kept" | "dismissed";

/** One kind of buyer, described well enough to write to and to go and find.
 *
 * Distinct from `AudienceSegment` above, which is what the knowledge compiler
 * distilled from the company's own material. This one was read off the open
 * market, which is why it carries a rate, the reasoning behind it, and the
 * signals that make it findable - none of which a company's own site contains. */
export interface MappedSegment {
  name: string;
  kind: SegmentKind;
  /** One person in a situation, not a category. */
  who: string;
  why_them: string;
  trigger: string;
  pains: string[];
  objection: string;
  /** The one line to open an email to them on. A segment nobody can write a
   * first sentence for is research, not an audience. */
  angle: string;
  /** Where an email to them is allowed to start. Same vocabulary the
   * compiled audience model uses, because a chosen segment becomes one. */
  sophistication: string;
  /** Roughly what share of the people matching `who` would be interested.
   * **An estimate, never a measurement** - nobody has sent these emails yet,
   * so it is only worth what `basis` beside it is worth. */
  fit: number;
  basis: string;
  population: string;
  /** Observable markers that identify one from the outside. What makes the
   * segment findable by name - and a segment with none cannot be prospected,
   * advertised to, or targeted by any other means either. */
  signals: string[];
  /** Named places they are findable in bulk. */
  where: string[];
  /** True for every kind except `core`. */
  unobvious: boolean;
}

export interface DemandMap {
  summary: string;
  /** One paragraph on where the demand in this market really is. */
  reading: string;
  note: string;
  searched: string[];
  mapped_at: string;
  /** Best fit first. The order is the recommendation. */
  segments: MappedSegment[];
}

/** One published way to reach an organisation.
 *
 * Everything that reaches this client was found, character for character, on
 * a page the server fetched. Unverified values are dropped server-side rather
 * than shipped marked, because a list where some rows are real and some are
 * invented is one whose rows get told apart by sending mail to them. */
export interface Contact {
  kind: ContactKind;
  value: string;
  label: string;
  source: string;
  verified: boolean;
}

/** One named organisation that could buy this, read from its own pages. */
export interface Prospect {
  id: string;
  segment: string;
  name: string;
  url: string;
  what_they_do: string;
  why_them: string;
  /** The sentence on their page that supports `why_them`. Empty when the
   * extractor's reason was not actually there. */
  verbatim: string;
  fit: number;
  caveat: string;
  /** False when their site could not be read; everything above is then a lead
   * nobody confirmed, and the card has to say so. */
  verified: boolean;
  pages_read: number;
  /** Contact details the extractor reported that were nowhere on their site.
   * A row that had to discard several is one whose other claims deserve the
   * same suspicion. */
  invented_contacts: number;
  note: string;
  status: ProspectStatus;
  found_at: string;
  decided_at: string | null;
  contacts: Contact[];
}

export interface AudienceRead {
  brand_id: string;
  map: DemandMap | null;
  prospects: Prospect[];
  note: string;
}

export interface ProspectSearchRequest {
  segment: string;
  limit?: number;
  /** Read each organisation's own pages for a published way in. Off returns
   * names only, at one call instead of one per company. */
  with_contacts?: boolean;
}

/** Where a running (or last finished) scan or proof hunt got to. Polled -
 * a scan is a handful of calls, not a run with a timeline. */
export interface MarketJob {
  /** "scan" | "proof" | "audience" | "prospects". */
  kind: string;
  state: "running" | "done" | "failed";
  /** The stage the job is at, in the user's language. */
  message: string;
  /** Every line so far — progress lines and one row per finished model call,
   * so a page that opens late is not blank and the trace explains the spend. */
  log: string[];
  started_at: string;
  finished_at: string | null;
  error: string;
  summary: string;
  found: number;
  /** Present on the /market/jobs board so a row can name and link its brand
   * without a lookup per row; null on the per-brand endpoint. */
  brand_id: string | null;
  brand_name: string;
  /** What this job has spent. Cached input is counted into input_tokens — it
   * is what the quota paid for. */
  calls: number;
  input_tokens: number;
  output_tokens: number;
  cache_read_tokens: number;
  cost_usd: number;
}
