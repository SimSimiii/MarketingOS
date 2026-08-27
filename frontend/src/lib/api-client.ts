import { API_URL } from "@/lib/config";
import type {
  AudienceRead,
  Brand,
  BrandCreateRequest,
  BrandStyleUpdate,
  BrandKnowledge,
  BrandOverview,
  Campaign,
  CampaignCreateRequest,
  CampaignExecution,
  CampaignPolicyUpdate,
  CampaignResult,
  ExecutionLog,
  ExecutionTimeline,
  GeneratedAsset,
  KnowledgeBase,
  KnowledgeDocument,
  KnowledgeDocumentDetail,
  KnowledgeSourceCreate,
  MarketJob,
  MarketRead,
  ModelCatalog,
  ProofCandidate,
  ProofStatus,
  Prospect,
  ProspectSearchRequest,
  ProspectStatus,
  RadarEvent,
  Rival,
  RivalCreateRequest,
  RunForecast,
  RunningExecution,
  UserSettings,
  UserSettingsUpdate,
} from "@/lib/types";

/** The readable half of a FastAPI error.
 *
 * FastAPI puts the message a human should read in `detail`, and raising the
 * raw body instead surfaces `API error 422: {"detail":"GPT-5.6 Sol cannot run
 * ..."}` in a toast - the one sentence that would have helped, wrapped in
 * punctuation. Falls back to the body when it is not JSON, which is what a
 * proxy or a crash returns. */
async function errorMessage(response: Response): Promise<string> {
  const body = await response.text();
  try {
    const parsed = JSON.parse(body) as { detail?: unknown };
    if (typeof parsed.detail === "string" && parsed.detail) return parsed.detail;
  } catch {
    // Not JSON - fall through to the raw body below.
  }
  return `API error ${response.status}: ${body}`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
    ...init,
  });

  if (!response.ok) {
    throw new Error(await errorMessage(response));
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

/** Multipart upload - the browser sets its own Content-Type boundary. */
async function upload<T>(path: string, body: FormData): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, { method: "POST", body, cache: "no-store" });
  if (!response.ok) {
    throw new Error(await errorMessage(response));
  }
  return (await response.json()) as T;
}

export const api = {
  listCampaigns: (includeArchived = false) =>
    request<Campaign[]>(`/campaigns${includeArchived ? "?include_archived=true" : ""}`),
  getCampaign: (id: string) => request<Campaign>(`/campaigns/${id}`),
  createCampaign: (data: CampaignCreateRequest) =>
    request<Campaign>("/campaigns", { method: "POST", body: JSON.stringify(data) }),
  deleteCampaign: (id: string) => request<void>(`/campaigns/${id}`, { method: "DELETE" }),
  archiveCampaign: (id: string) =>
    request<Campaign>(`/campaigns/${id}/archive`, { method: "POST" }),
  unarchiveCampaign: (id: string) =>
    request<Campaign>(`/campaigns/${id}/unarchive`, { method: "POST" }),
  duplicateCampaign: (id: string) =>
    request<Campaign>(`/campaigns/${id}/duplicate`, { method: "POST" }),
  updateCampaignPolicy: (id: string, data: CampaignPolicyUpdate) =>
    request<Campaign>(`/campaigns/${id}/policy`, { method: "PUT", body: JSON.stringify(data) }),
  /** What running this campaign will cost, before it is run. Free and
   * instant - nothing behind this endpoint calls a model. */
  getCampaignForecast: (id: string) => request<RunForecast>(`/campaigns/${id}/forecast`),
  startCampaign: (id: string) =>
    request<CampaignExecution>(`/campaigns/${id}/start`, { method: "POST" }),
  restartCampaign: (id: string) =>
    request<CampaignExecution>(`/campaigns/${id}/restart`, { method: "POST" }),
  listCampaignExecutions: (id: string) =>
    request<CampaignExecution[]>(`/campaigns/${id}/executions`),

  getExecutionResult: (executionId: string) =>
    request<CampaignResult>(`/executions/${executionId}/result`),
  getExecutionAssets: (executionId: string) =>
    request<GeneratedAsset[]>(`/executions/${executionId}/assets`),
  cancelExecution: (executionId: string) =>
    request<{ status: string }>(`/executions/${executionId}/cancel`, { method: "POST" }),
  /** Everything broadcast for this run so far, replayed from the database -
   * what a page loads before opening the stream so a reload starts full
   * rather than blank. */
  getExecutionTimeline: (executionId: string) =>
    request<ExecutionTimeline>(`/executions/${executionId}/timeline`),
  /** One run's log lines, optionally narrowed to a single agent's lane.
   * DEBUG progress chatter is left out unless `includeDebug` asks for it. */
  getExecutionLogs: (
    executionId: string,
    options: { agentId?: string; includeDebug?: boolean } = {},
  ) => {
    const query = new URLSearchParams();
    if (options.agentId) query.set("agent_id", options.agentId);
    if (options.includeDebug) query.set("include_debug", "true");
    const suffix = query.size > 0 ? `?${query}` : "";
    return request<ExecutionLog[]>(`/executions/${executionId}/logs${suffix}`);
  },
  listRunningExecutions: () => request<RunningExecution[]>("/executions/running"),
  /** SSE URL for the live execution feed - opened directly as an EventSource
   * by the client component, not through the JSON `request()` helper.
   * `afterEventId` resumes where the timeline left off, so the handover from
   * HTTP to the stream neither skips events nor repeats them. */
  executionStreamUrl: (executionId: string, afterEventId?: number) =>
    `${API_URL}/executions/${executionId}/stream` +
    (afterEventId ? `?after_event_id=${afterEventId}` : ""),

  listKnowledgeDocuments: (scope: { campaignId?: string; brandId?: string } = {}) => {
    const query = new URLSearchParams();
    if (scope.campaignId) query.set("campaign_id", scope.campaignId);
    if (scope.brandId) query.set("brand_id", scope.brandId);
    const suffix = query.size > 0 ? `?${query}` : "";
    return request<KnowledgeDocument[]>(`/knowledge${suffix}`);
  },
  /** Everything compiled about one business, classified onto shelves and
   * ranked by what each fact is worth to a sale. 404s until the first
   * campaign run, which is when compilation happens. */
  getKnowledgeBase: (scope: { brandId?: string; campaignId?: string }) => {
    const query = new URLSearchParams();
    if (scope.brandId) query.set("brand_id", scope.brandId);
    if (scope.campaignId) query.set("campaign_id", scope.campaignId);
    return request<KnowledgeBase>(`/knowledge/base?${query}`);
  },
  addKnowledgeSource: (data: KnowledgeSourceCreate) =>
    request<KnowledgeDocumentDetail[]>("/knowledge", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  uploadKnowledgeFile: (
    file: File,
    scope: { campaignId?: string; brandId?: string } = {},
    title?: string,
  ) => {
    const body = new FormData();
    body.append("file", file);
    if (scope.campaignId) body.append("campaign_id", scope.campaignId);
    if (scope.brandId) body.append("brand_id", scope.brandId);
    if (title) body.append("title", title);
    return upload<KnowledgeDocumentDetail[]>("/knowledge/upload", body);
  },
  deleteKnowledgeDocument: (id: string) => request<void>(`/knowledge/${id}`, { method: "DELETE" }),

  listBrands: () => request<Brand[]>("/brands"),
  /** Every brand with the state of its own workspace - sources, compiled
   * knowledge, competitors, waiting proof and unseen alerts - in one request
   * rather than three per brand. */
  listBrandOverviews: () => request<BrandOverview[]>("/brands/overview"),
  getBrand: (id: string) => request<Brand>(`/brands/${id}`),
  createBrand: (data: BrandCreateRequest) =>
    request<Brand>("/brands", { method: "POST", body: JSON.stringify(data) }),
  getBrandKnowledge: (id: string) => request<BrandKnowledge>(`/brands/${id}/knowledge`),
  /** How this brand's email looks once it is rendered. Every field optional —
   * a brand with none of it set still renders, in the typographic tier. */
  updateBrandStyle: (id: string, data: BrandStyleUpdate) =>
    request<Brand>(`/brands/${id}/style`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  /** Every model the picker can offer and every agent one can be pinned to.
   * Static for the lifetime of a build, so callers are free to fetch it once
   * and keep it. */
  getModelCatalog: () => request<ModelCatalog>("/models"),

  getSettings: () => request<UserSettings>("/settings"),
  updateSettings: (data: UserSettingsUpdate) =>
    request<UserSettings>("/settings", { method: "PATCH", body: JSON.stringify(data) }),

  listLogs: (limit = 200) => request<ExecutionLog[]>(`/logs?limit=${limit}`),

  // ------------------------------------------------------------------ market
  //
  // Everything here is scoped to a brand rather than to a campaign: a market
  // belongs to the business and outlives any one campaign, which is the same
  // reason compiled knowledge does.

  /** Everything the market page shows, in one request. */
  getMarket: (brandId: string) => request<MarketRead>(`/market/${brandId}`),
  addRival: (brandId: string, data: RivalCreateRequest) =>
    request<Rival>(`/market/${brandId}/rivals`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  /** Take a competitor out of the map without forgetting the decision -
   * deleting one only means the next scan proposes it again. */
  muteRival: (brandId: string, rivalId: string, muted: boolean) =>
    request<Rival>(`/market/${brandId}/rivals/${rivalId}`, {
      method: "PATCH",
      body: JSON.stringify({ muted }),
    }),
  deleteRival: (brandId: string, rivalId: string) =>
    request<void>(`/market/${brandId}/rivals/${rivalId}`, { method: "DELETE" }),

  /** Read the market. `discover` searches the web for competitors nobody has
   * named yet; off re-reads the existing list only, which is what a weekly
   * refresh wants. */
  startMarketScan: (brandId: string, discover = true) =>
    request<MarketJob>(`/market/${brandId}/scan`, {
      method: "POST",
      body: JSON.stringify({ discover }),
    }),
  startProofHunt: (brandId: string) =>
    request<MarketJob>(`/market/${brandId}/proof/hunt`, { method: "POST" }),
  /** Where the running (or last finished) job for one brand got to. */
  getMarketJob: (brandId: string) => request<MarketJob | null>(`/market/${brandId}/job`),
  /** Every market job this server knows about, running ones first. Not
   * brand-scoped: the live board asks what is happening anywhere. */
  listMarketJobs: () => request<MarketJob[]>("/market/jobs"),

  listProof: (brandId: string, status?: ProofStatus) =>
    request<ProofCandidate[]>(
      `/market/${brandId}/proof${status ? `?status_filter=${status}` : ""}`,
    ),
  /** Approving a found proof is what turns it into a fact the copy may spend:
   * it enters the evidence ledger on the next run and the evidence gate
   * licenses the words in it. */
  decideProof: (brandId: string, proofId: string, approved: boolean) =>
    request<ProofCandidate>(`/market/${brandId}/proof/${proofId}`, {
      method: "POST",
      body: JSON.stringify({ approved }),
    }),

  // ---------------------------------------------------------------- demand
  //
  // Who would buy this, and which named organisations match. Brand-scoped
  // like the rest of the market, and for the same reason.

  /** The demand map and every organisation found for it, in one request.
   * `segment` narrows the prospect list without hiding the map - the map is
   * the context the numbers beside each name are read in. */
  getAudience: (brandId: string, segment?: string) =>
    request<AudienceRead>(
      `/market/${brandId}/audience${segment ? `?segment=${encodeURIComponent(segment)}` : ""}`,
    ),
  /** Work out who would actually buy this, including the buyers the company's
   * own website would never have named. */
  startAudienceMap: (brandId: string) =>
    request<MarketJob>(`/market/${brandId}/audience/map`, {
      method: "POST",
      body: JSON.stringify({}),
    }),
  /** Name real organisations that match one mapped segment. Every contact it
   * produces was read off a page the server fetched and checked back against
   * it, so the list is short and it is real. */
  startProspectSearch: (brandId: string, data: ProspectSearchRequest) =>
    request<MarketJob>(`/market/${brandId}/audience/prospects`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  /** Keep or dismiss one organisation. A dismissal is remembered rather than
   * deleted, or the next search finds them again. */
  decideProspect: (brandId: string, prospectId: string, status: ProspectStatus) =>
    request<Prospect>(`/market/${brandId}/prospects/${prospectId}`, {
      method: "POST",
      body: JSON.stringify({ status }),
    }),
  /** The kept rows, as a file. A prospect list that cannot leave the product
   * is a demo - the people who use this already have somewhere they send mail
   * from. Kept rows only: a file that quietly included unreviewed ones would
   * defeat the review it came from. */
  prospectsCsvUrl: (brandId: string, segment?: string) =>
    `${API_URL}/market/${brandId}/prospects.csv${
      segment ? `?segment=${encodeURIComponent(segment)}` : ""
    }`,

  listRadar: (brandId: string, limit = 50) =>
    request<RadarEvent[]>(`/market/${brandId}/radar?limit=${limit}`),
  markRadarSeen: (brandId: string) =>
    request<{ marked: number }>(`/market/${brandId}/radar/seen`, { method: "POST" }),
};
