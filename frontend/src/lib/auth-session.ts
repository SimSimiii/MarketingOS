/**
 * Server-side session plumbing, shared by the route handlers under
 * `src/app/api/auth`.
 *
 * Those handlers exist for one reason: cookies are per-origin. The API sets
 * its own cookies on its own hostname, and a Next.js server component can only
 * read cookies that arrived on *this* origin. So sign-in goes browser → Next →
 * API, and Next re-issues the tokens as its own cookies. That is what lets a
 * server-rendered page know who is looking at it.
 *
 * The split between the two cookies is the security-relevant part:
 *
 * - The **access token** is readable by script, because client components and
 *   the `EventSource` URL builder need it and neither can read an httpOnly
 *   cookie. It is worth sixty minutes.
 * - The **refresh token** is httpOnly and scoped to `/api/auth`, so it is sent
 *   to these handlers and to nothing else - not to a page, not to a client
 *   component, not to the API. It is worth a month, which is exactly why.
 */

import { cookies } from "next/headers";

import { API_URL } from "@/lib/config";
import {
  ACCESS_TOKEN_COOKIE,
  REFRESH_COOKIE_PATH,
  REFRESH_TOKEN_COOKIE,
} from "@/lib/auth-cookies";
import type { Account } from "@/lib/types";

export interface TokenPayload {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  user: Account;
}

/** Secure cookies are dropped by the browser over plain HTTP, which is what
 *  `next dev` serves - so the flag follows the deployment rather than being
 *  hardcoded either way. */
const secure = process.env.NODE_ENV === "production";

export async function storeSession(tokens: TokenPayload): Promise<void> {
  const jar = await cookies();
  jar.set(ACCESS_TOKEN_COOKIE, tokens.access_token, {
    maxAge: tokens.expires_in,
    httpOnly: false,
    secure,
    sameSite: "lax",
    path: "/",
  });
  jar.set(REFRESH_TOKEN_COOKIE, tokens.refresh_token, {
    // Thirty days, matching the API's default REFRESH_TOKEN_TTL_DAYS. A cookie
    // that outlives the token it holds only produces a failed refresh; one
    // that dies first signs somebody out early.
    maxAge: 30 * 24 * 3600,
    httpOnly: true,
    secure,
    sameSite: "lax",
    path: REFRESH_COOKIE_PATH,
  });
}

export async function clearSession(): Promise<void> {
  const jar = await cookies();
  jar.delete({ name: ACCESS_TOKEN_COOKIE, path: "/" });
  jar.delete({ name: REFRESH_TOKEN_COOKIE, path: REFRESH_COOKIE_PATH });
}

export async function readRefreshToken(): Promise<string | undefined> {
  return (await cookies()).get(REFRESH_TOKEN_COOKIE)?.value;
}

/** Forward a call to the API and hand back its status and body unchanged.
 *
 * Unchanged matters: the API already writes messages a person can read, and a
 * handler that replaced them with its own would be inventing an explanation
 * for a failure it does not understand.
 */
export async function callApi(
  path: string,
  body: unknown,
  headers: Record<string, string> = {},
): Promise<{ status: number; data: unknown }> {
  const response = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...headers },
    body: JSON.stringify(body ?? {}),
    cache: "no-store",
  });
  const text = await response.text();
  let data: unknown = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = { detail: text || "The API did not answer with JSON." };
  }
  return { status: response.status, data };
}

export function isTokenPayload(data: unknown): data is TokenPayload {
  return (
    typeof data === "object" &&
    data !== null &&
    typeof (data as TokenPayload).access_token === "string" &&
    typeof (data as TokenPayload).refresh_token === "string"
  );
}
