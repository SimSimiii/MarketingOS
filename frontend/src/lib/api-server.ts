/**
 * The API as a server component sees it.
 *
 * Importing `next/headers` is what makes this module server-only: Next refuses
 * to bundle it into a client component, which is exactly the guard we want -
 * a page that renders on the server and forgets to use this one would silently
 * make unauthenticated calls, and in single-user mode it would even work.
 *
 * Pages import `{ api } from "@/lib/api-server"`. Client components import
 * `@/lib/api-client`. Both are `createApi` over the same surface.
 */

import { cookies } from "next/headers";

import { createApi, type AuthSource } from "@/lib/api-core";
import { ACCESS_TOKEN_COOKIE } from "@/lib/auth-cookies";

export { UnauthorizedError } from "@/lib/api-core";

const serverAuth: AuthSource = {
  async header(): Promise<Record<string, string>> {
    const token = (await cookies()).get(ACCESS_TOKEN_COOKIE)?.value;
    return token ? { Authorization: `Bearer ${token}` } : {};
  },
  // Server-side rendering never opens an EventSource or hands out a download
  // link it signed itself - both are things the browser does.
  tokenSync: () => undefined,
};

export const api = createApi(serverAuth);
