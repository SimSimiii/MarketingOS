/**
 * The API as the browser sees it.
 *
 * Client components import this. Server components import `@/lib/api-server`
 * instead - same sixty calls, built from the same factory, differing only in
 * where the bearer token comes from. A server component has the request's
 * cookies; a browser has the document's, and neither can read the other's.
 *
 * The access token cookie is readable by script on purpose. The refresh token
 * is not: it is httpOnly and scoped to `/api/auth`, so only the route handlers
 * under `src/app/api/auth` ever see it. That is the split that matters - an
 * access token is worth sixty minutes, a refresh token is worth a month.
 */

import { createApi, type AuthSource } from "@/lib/api-core";
import { ACCESS_TOKEN_COOKIE } from "@/lib/auth-cookies";

export { UnauthorizedError } from "@/lib/api-core";

export function readAccessToken(): string | undefined {
  if (typeof document === "undefined") return undefined;
  const match = document.cookie.match(
    new RegExp(`(?:^|;\\s*)${ACCESS_TOKEN_COOKIE}=([^;]*)`),
  );
  return match ? decodeURIComponent(match[1]) : undefined;
}

const browserAuth: AuthSource = {
  async header(): Promise<Record<string, string>> {
    const token = readAccessToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  },
  tokenSync: readAccessToken,
};

export const api = createApi(browserAuth);
