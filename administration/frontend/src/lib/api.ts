/**
 * The back-office API client.
 *
 * The token lives in `sessionStorage`, not `localStorage`, and that is the
 * one decision in this file worth arguing about. An operator token can read
 * and change every customer account; scoping it to the tab means closing the
 * tab ends the session, and a shared or borrowed machine does not keep a live
 * console behind a browser restart. The cost is signing in again after a
 * reload, which for a console used a few times a day is the right trade.
 */

const RAW_BASE =
  process.env.NEXT_PUBLIC_ADMIN_API_URL ?? "http://localhost:8001";

/** Trailing slashes turn every path into a double-slashed URL that some
 *  gateways redirect and others reject. */
export const ADMIN_API_URL = RAW_BASE.replace(/\/$/, "");

const TOKEN_KEY = "mos_admin_token";

export function readToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.sessionStorage.getItem(TOKEN_KEY);
  } catch {
    // Private mode, or storage blocked by policy. Treated as signed out
    // rather than as a crash on the sign-in page.
    return null;
  }
}

export function writeToken(token: string | null): void {
  if (typeof window === "undefined") return;
  try {
    if (token === null) window.sessionStorage.removeItem(TOKEN_KEY);
    else window.sessionStorage.setItem(TOKEN_KEY, token);
  } catch {
    /* See readToken. */
  }
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function readError(response: Response): Promise<string> {
  const body = await response.text();
  try {
    const parsed = JSON.parse(body) as { detail?: unknown };
    if (typeof parsed.detail === "string" && parsed.detail) return parsed.detail;
    // FastAPI's validation errors are a list of objects; the first message is
    // the useful one and the rest is schema noise.
    if (Array.isArray(parsed.detail) && parsed.detail.length > 0) {
      const first = parsed.detail[0] as { msg?: string };
      if (first?.msg) return first.msg;
    }
  } catch {
    /* Not JSON - a gateway error page or a crash. Fall through. */
  }
  return body || `Request failed (${response.status}).`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = readToken();
  const response = await fetch(`${ADMIN_API_URL}${path}`, {
    ...init,
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
  });

  if (response.status === 401) {
    // The token is gone or expired. Drop it here rather than leaving a dead
    // credential in storage for the next request to fail on too.
    writeToken(null);
    throw new ApiError("Your session has ended. Sign in again.", 401);
  }
  if (!response.ok) throw new ApiError(await readError(response), response.status);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

// ── Types ────────────────────────────────────────────────────────────────────

export type AdminRole = "support" | "admin" | "superadmin";
export type UserPlan = "free" | "pro" | "business";

export interface Admin {
  id: string;
  email: string;
  full_name: string | null;
  role: AdminRole;
  is_active: boolean;
  last_login_at: string | null;
  created_at: string;
}

export interface UserSummary {
  id: string;
  email: string;
  full_name: string | null;
  company_name: string | null;
  plan: UserPlan;
  status: string;
  monthly_run_quota: number;
  runs_used: number;
  brands: number;
  campaigns: number;
  runs: number;
  created_at: string;
  last_login_at: string | null;
}

export interface UserDetail extends UserSummary {
  suspended_reason: string | null;
  active_sessions: number;
  total_input_tokens: number;
  total_output_tokens: number;
  estimated_cost_usd: number;
  last_run_at: string | null;
}

export interface Overview {
  users_total: number;
  users_active: number;
  users_suspended: number;
  users_by_plan: Record<string, number>;
  signups_last_7_days: number;
  signups_last_30_days: number;
  brands_total: number;
  campaigns_total: number;
  runs_total: number;
  runs_last_7_days: number;
  runs_failed_last_7_days: number;
  tokens_total: number;
  model_spend_usd: number;
  estimated_mrr_usd: number;
}

export interface AuditEntry {
  id: string;
  admin_email: string | null;
  action: string;
  target_type: string | null;
  target_id: string | null;
  detail: Record<string, unknown> | null;
  ip_address: string | null;
  created_at: string;
}

export interface Workspace {
  brands: { id: string; name: string; created_at: string }[];
  campaigns: { id: string; name: string; status: string; created_at: string }[];
}

export interface TimeseriesPoint {
  day: string;
  value: number;
}

// ── Calls ────────────────────────────────────────────────────────────────────

export const api = {
  login: (email: string, password: string) =>
    request<{ access_token: string; expires_in: number; admin: Admin }>(
      "/api/auth/login",
      { method: "POST", body: JSON.stringify({ email, password }) },
    ),
  me: () => request<Admin>("/api/auth/me"),
  logout: () => request<void>("/api/auth/logout", { method: "POST" }),

  overview: () => request<Overview>("/api/overview"),
  timeseries: (metric: string, days = 30) =>
    request<{ metric: string; days: number; series: TimeseriesPoint[] }>(
      `/api/stats/timeseries?metric=${metric}&days=${days}`,
    ),

  listUsers: (params: {
    search?: string;
    plan?: string;
    status?: string;
    limit?: number;
    offset?: number;
  }) => {
    const query = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== "") query.set(key, String(value));
    }
    return request<{
      items: UserSummary[];
      total: number;
      limit: number;
      offset: number;
    }>(`/api/users?${query}`);
  },
  getUser: (id: string) => request<UserDetail>(`/api/users/${id}`),
  getWorkspace: (id: string) => request<Workspace>(`/api/users/${id}/workspace`),
  changePlan: (
    id: string,
    body: { plan: string; monthly_run_quota?: number; reason?: string },
  ) => request<UserDetail>(`/api/users/${id}/plan`, { method: "PATCH", body: JSON.stringify(body) }),
  setQuota: (
    id: string,
    body: { monthly_run_quota?: number; runs_used?: number; reason?: string },
  ) => request<UserDetail>(`/api/users/${id}/quota`, { method: "PATCH", body: JSON.stringify(body) }),
  suspend: (id: string, reason: string) =>
    request<UserDetail>(`/api/users/${id}/suspend`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),
  unsuspend: (id: string) =>
    request<UserDetail>(`/api/users/${id}/unsuspend`, { method: "POST" }),
  signOutUser: (id: string) =>
    request<{ sessions_revoked: number }>(`/api/users/${id}/sign-out`, { method: "POST" }),
  deleteUser: (id: string) =>
    request<{ deleted: string }>(`/api/users/${id}`, { method: "DELETE" }),

  listAdmins: () => request<Admin[]>("/api/admins"),
  createAdmin: (body: {
    email: string;
    password: string;
    full_name?: string;
    role: AdminRole;
  }) => request<Admin>("/api/admins", { method: "POST", body: JSON.stringify(body) }),
  updateAdmin: (id: string, body: { role?: AdminRole; is_active?: boolean }) =>
    request<Admin>(`/api/admins/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  resetAdminPassword: (id: string, password: string) =>
    request<void>(`/api/admins/${id}/password`, {
      method: "POST",
      body: JSON.stringify({ password }),
    }),

  audit: (params: { action?: string; target_id?: string; limit?: number } = {}) => {
    const query = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== "") query.set(key, String(value));
    }
    return request<AuditEntry[]>(`/api/audit?${query}`);
  },
};

/** Role ordering, mirroring admin.auth.ROLE_LEVELS. Used to hide controls the
 *  API would refuse anyway - the server is still the one enforcing it. */
const LEVELS: Record<AdminRole, number> = { support: 1, admin: 2, superadmin: 3 };

export function atLeast(role: AdminRole | undefined, minimum: AdminRole): boolean {
  return role !== undefined && LEVELS[role] >= LEVELS[minimum];
}
