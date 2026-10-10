/**
 * The API as the browser sees it - and, the console being a static export,
 * the only way anything here reaches it.
 *
 * The API sets both session cookies itself, on this origin (CloudFront routes
 * /api/* to it). The access token cookie is readable by script on purpose: it
 * goes back as a bearer header, which mutations require. The refresh token is
 * not: it is httpOnly and scoped to /api/auth, so only the refresh and sign-out
 * endpoints ever see it. That is the split that matters - an access token is
 * worth sixty minutes, a refresh token is worth a month.
 */

import { createApi, type AuthSource } from "@/lib/api-core";
import { ACCESS_TOKEN_COOKIE } from "@/lib/auth-cookies";
import { renewSession } from "@/lib/renew-session";

export { ApiError, UnauthorizedError, nullIfMissing } from "@/lib/api-core";

export function readAccessToken(): string | undefined {
  if (typeof document === "undefined") return undefined;
  const match = document.cookie.match(
    new RegExp(`(?:^|;\\s*)${ACCESS_TOKEN_COOKIE}=([^;]*)`),
  );
  return match ? decodeURIComponent(match[1]) : undefined;
}

const browserAuth: AuthSource = {
  refresh: renewSession,
  async header(): Promise<Record<string, string>> {
    const token = readAccessToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  },
};

export const api = createApi(browserAuth);
