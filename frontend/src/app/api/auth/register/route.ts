import { NextResponse } from "next/server";

import { callApi, isTokenPayload, storeSession } from "@/lib/auth-session";

/** Create an account and sign it in.
 *
 * Whether this is allowed at all is the API's call (`ALLOW_PUBLIC_SIGNUP`) -
 * a closed deployment answers 403 and that message is passed straight through,
 * rather than this handler guessing at a rule it does not own. */
export async function POST(request: Request) {
  const body = await request.json().catch(() => ({}));
  const { status, data } = await callApi("/auth/register", body, {
    "User-Agent": request.headers.get("user-agent") ?? "MarketingOS web",
  });

  if (status !== 201 || !isTokenPayload(data)) {
    return NextResponse.json(data ?? { detail: "Could not create the account." }, { status });
  }
  await storeSession(data);
  return NextResponse.json({ user: data.user }, { status: 201 });
}
