"use client";

import { useEffect, useSyncExternalStore } from "react";
import { usePathname } from "next/navigation";

import { readAccessToken } from "@/lib/api-client";
import { AUTH_REQUIRED } from "@/lib/config";

const noSubscription = () => () => {};

/** Where this visitor should be, or null to stay. */
function redirectFor(pathname: string, signedIn: boolean): string | null {
  const path = pathname.replace(/\/+$/, "") || "/";
  if (path === "/session/renew") return null;
  const onAuthPage = path === "/login" || path === "/register";
  if (!signedIn && !onAuthPage) {
    // Where they were going, so signing in lands them there instead of on the
    // dashboard. Only ever a path from this origin.
    const next = `${window.location.pathname}${window.location.search}`;
    return `/session/renew/${path === "/" ? "" : `?next=${encodeURIComponent(next)}`}`;
  }
  if (signedIn && onAuthPage) return "/";
  return null;
}

/**
 * Send signed-out visitors to the sign-in flow - what src/proxy.ts did when the
 * console had a server.
 *
 * This is a redirect, not a security boundary: it only looks at whether the
 * access cookie exists, never at whether the token in it is valid. Every page
 * underneath loads its data from the API with that token, and the API is what
 * decides. Faking a cookie here buys a blank page and a row of 401s.
 *
 * Nothing renders until the check has run in the browser, so no page starts
 * loading data it is about to be redirected away from.
 */
export function AuthGuard({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  // False while the static HTML is built and during hydration; true after.
  const inBrowser = useSyncExternalStore(noSubscription, () => true, () => false);
  const target =
    AUTH_REQUIRED && inBrowser ? redirectFor(pathname, readAccessToken() !== undefined) : null;

  useEffect(() => {
    if (target) window.location.replace(target);
  }, [target]);

  if (!AUTH_REQUIRED) return <>{children}</>;
  if (!inBrowser || target) return null;
  return <>{children}</>;
}
