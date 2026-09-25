import { NextResponse } from "next/server";

import {
  callApi,
  clearSession,
  isTokenPayload,
  readRefreshToken,
  storeSession,
} from "@/lib/auth-session";

/** Trade the refresh cookie for a new pair.
 *
 * The API rotates on every use - the presented token is revoked in the same
 * transaction that issues its replacement - so this handler must always store
 * what comes back. Dropping the response would leave the browser holding a
 * refresh token that has already been spent.
 */
export async function POST(request: Request) {
  const origin = request.headers.get("origin");
  if ((origin && origin !== new URL(request.url).origin)
      || request.headers.get("sec-fetch-site") === "cross-site") {
    return NextResponse.json({ detail: "Invalid origin." }, { status: 403 });
  }
  const refresh = await readRefreshToken();
  if (!refresh) {
    return NextResponse.json({ detail: "No session to refresh." }, { status: 401 });
  }

  const { status, data } = await callApi("/auth/refresh", { refresh_token: refresh });
  if (status !== 200 || !isTokenPayload(data)) {
    // A refresh that fails is a session that is over: expired, revoked, or
    // suspended. Leaving the dead cookies in place would make every later
    // request fail the same way, silently.
    if (status === 401 || status === 403) await clearSession();
    return NextResponse.json(data ?? { detail: "Session expired." }, { status });
  }

  await storeSession(data);
  return NextResponse.json({ user: data.user, expires_in: data.expires_in });
}
