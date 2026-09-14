import { cookies } from "next/headers";
import { ACCESS_TOKEN_COOKIE } from "@/lib/auth-cookies";
import { API_URL } from "@/lib/config";

/** Narrow same-origin proxy for downloads and streams; no credentials in URLs. */
export async function GET(request: Request, context: { params: Promise<{ path: string[] }> }) {
  const path = (await context.params).path.join("/");
  if (!/^(executions\/[0-9a-f-]{36}\/stream|market\/[0-9a-f-]{36}\/prospects\.csv)$/.test(path)) {
    return new Response("Not found", { status: 404 });
  }
  const target = new URL(`${API_URL}/${path}`);
  const query = new URL(request.url).searchParams;
  for (const key of ["segment", "after_event_id"]) {
    if (query.has(key)) target.searchParams.set(key, query.get(key)!);
  }
  const token = (await cookies()).get(ACCESS_TOKEN_COOKIE)?.value;
  const upstream = await fetch(target, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    cache: "no-store", signal: request.signal,
  });
  const headers = new Headers({ "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff" });
  for (const name of ["content-type", "content-disposition"]) {
    if (upstream.headers.has(name)) headers.set(name, upstream.headers.get(name)!);
  }
  return new Response(upstream.body, { status: upstream.status, headers });
}
