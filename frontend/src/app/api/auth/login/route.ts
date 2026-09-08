import { NextResponse } from "next/server";

import { callApi, isTokenPayload, storeSession } from "@/lib/auth-session";

/** Sign in, and turn the API's tokens into this origin's cookies.
 *
 * The password never touches a cookie or a URL: it arrives in this request's
 * body, goes straight out in the next one, and is not logged on the way. */
export async function POST(request: Request) {
  const body = await request.json().catch(() => ({}));
  const { status, data } = await callApi("/auth/login", body, {
    // Passed through so the API can record which device a session belongs to,
    // for the "where you are signed in" list.
    "User-Agent": request.headers.get("user-agent") ?? "MarketingOS web",
  });

  if (status !== 200 || !isTokenPayload(data)) {
    return NextResponse.json(data ?? { detail: "Sign-in failed." }, { status });
  }
  await storeSession(data);
  // The tokens themselves stay on the server side of this exchange - the
  // browser gets the account and the cookies, and never has to hold a refresh
  // token in script-reachable memory.
  return NextResponse.json({ user: data.user });
}
