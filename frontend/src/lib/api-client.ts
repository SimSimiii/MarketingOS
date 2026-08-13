import { API_URL } from "@/lib/config";
import type {
  Brand,
  BrandCreateRequest,
  BrandKnowledge,
  Campaign,
  CampaignCreateRequest,
  CampaignExecution,
  CampaignExecutionDetail,
  CampaignPolicyUpdate,
  CampaignResult,
  ExecutionLog,
  ExecutionTimeline,
  GeneratedAsset,
  KnowledgeDocument,
  KnowledgeDocumentDetail,
  KnowledgeSourceCreate,
  RunningExecution,
  UserSettings,
  UserSettingsUpdate,
} from "@/lib/types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
    ...init,
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`API error ${response.status}: ${detail}`);
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
    throw new Error(`API error ${response.status}: ${await response.text()}`);
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
  startCampaign: (id: string) =>
    request<CampaignExecution>(`/campaigns/${id}/start`, { method: "POST" }),
  restartCampaign: (id: string) =>
    request<CampaignExecution>(`/campaigns/${id}/restart`, { method: "POST" }),
  listCampaignExecutions: (id: string) =>
    request<CampaignExecution[]>(`/campaigns/${id}/executions`),

  getExecutionStatus: (executionId: string) =>
    request<CampaignExecutionDetail>(`/executions/${executionId}/status`),
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
  getKnowledgeDocument: (id: string) => request<KnowledgeDocumentDetail>(`/knowledge/${id}`),
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
  createBrand: (data: BrandCreateRequest) =>
    request<Brand>("/brands", { method: "POST", body: JSON.stringify(data) }),
  getBrandKnowledge: (id: string) => request<BrandKnowledge>(`/brands/${id}/knowledge`),
  deleteBrand: (id: string) => request<void>(`/brands/${id}`, { method: "DELETE" }),

  getSettings: () => request<UserSettings>("/settings"),
  updateSettings: (data: UserSettingsUpdate) =>
    request<UserSettings>("/settings", { method: "PATCH", body: JSON.stringify(data) }),

  listLogs: (limit = 200) => request<ExecutionLog[]>(`/logs?limit=${limit}`),
};
