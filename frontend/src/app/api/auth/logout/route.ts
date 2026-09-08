import { NextResponse } from "next/server";

import { callApi, clearSession, readRefreshToken } from "@/lib/auth-session";

/** Sign out: revoke the session on the API, then drop the cookies here.
 *
 * The cookies are cleared whatever the API said. A network failure between the
 * two must not leave somebody looking at a signed-in page they cannot use -
 * the server-side revocation can be retried, the local state cannot.
 */
export async function POST() {
  const refresh = await readRefreshToken();
  if (refresh) {
    await callApi("/auth/logout", { refresh_token: refresh }).catch(() => undefined);
  }
  await clearSession();
  return new NextResponse(null, { status: 204 });
}
