import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { ACCESS_TOKEN_COOKIE } from "@/lib/auth-cookies";
import { AUTH_REQUIRED } from "@/lib/config";

/**
 * Send signed-out visitors to the sign-in page.
 *
 * This is a redirect, not a security boundary, and the difference is worth
 * being explicit about: it only looks at whether a cookie exists, never at
 * whether the token in it is valid. Every page underneath renders from API
 * calls that carry the token, and the API is what decides. Faking a cookie
 * here buys a blank page and a row of 401s.
 *
 * What it does buy is the difference between "you are signed out" and a
 * dashboard full of failed requests.
 *
 * Named `proxy` rather than `middleware`: Next.js 16 renamed the convention.
 */
/**
 * On AWS the console's Function URL is public - CloudFront's origin access
 * control cannot sign a browser's POST, and signing in is a POST - so
 * CloudFront stamps every request with a header only it knows, and anything
 * arriving without it came around the CDN and its WAF. Unset (a laptop, a
 * test), nothing is checked. `/api/health` is exempt: the Lambda Web Adapter
 * polls it from inside the container, not through CloudFront.
 */
const ORIGIN_VERIFY_SECRET = process.env.ORIGIN_VERIFY_SECRET;

export function proxy(request: NextRequest) {
  const { pathname, search } = request.nextUrl;

  if (
    ORIGIN_VERIFY_SECRET &&
    pathname !== "/api/health" &&
    request.headers.get("x-origin-verify") !== ORIGIN_VERIFY_SECRET
  ) {
    return new NextResponse("Forbidden", { status: 403 });
  }
  // The auth route handlers are how you sign in; the redirects below are for
  // pages only. They are matched at all so the origin check covers them.
  if (pathname.startsWith("/api/")) return NextResponse.next();

  // Single-user mode: no accounts, no sign-in page, nothing to guard. This is
  // the shape a laptop install keeps, and putting a login wall in front of it
  // would break the one deployment that never asked for one.
  if (!AUTH_REQUIRED) return NextResponse.next();
  if (pathname === "/session/renew") return NextResponse.next();

  const signedIn = request.cookies.has(ACCESS_TOKEN_COOKIE);
  const onAuthPage = pathname === "/login" || pathname === "/register";

  if (!signedIn && !onAuthPage) {
    const url = request.nextUrl.clone();
    url.pathname = "/session/renew";
    url.search = "";
    // Where they were going, so signing in lands them there instead of on the
    // dashboard. Only ever a path from this origin - `next` is read back
    // through `URL` with this origin as the base, so an absolute URL in it
    // cannot become an open redirect.
    if (pathname !== "/") url.searchParams.set("next", `${pathname}${search}`);
    return NextResponse.redirect(url);
  }

  if (signedIn && onAuthPage) {
    const url = request.nextUrl.clone();
    url.pathname = "/";
    url.search = "";
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  /*
   * Everything except:
   *   _next/*     - the build output
   *   favicon,
   *   any path with a file extension (static assets)
   * `api/*` is matched for the origin check and then passed straight through.
   */
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.[^/]+$).*)"],
};
