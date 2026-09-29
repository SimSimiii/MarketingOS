"use client";

/**
 * How a page gets its data, now that there is no server to render it.
 *
 * The console is a static export on S3: every page is HTML that loads its data
 * from the browser, against `/api` on its own domain. This module is the whole
 * of that mechanism, so each page stays what it was - fetch, then render -
 * with the fetch moved into `usePageData` and the render into `<PageData>`.
 *
 * Three things a server used to do for free are rebuilt here:
 *
 * - `refreshPage()` replaces `router.refresh()`: it reloads the data of every
 *   page currently mounted, which is what a mutation wants afterwards.
 * - `notFound()` and `redirect()` are thrown from a loader and handled by
 *   `<PageData>`, so a loader reads like the server component it replaced.
 * - An `UnauthorizedError` (the session is over and could not be renewed)
 *   sends the reader to /session/renew, as the server did.
 */

import { useEffect, useRef, useState, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";

import { EmptyState } from "@/components/empty-state";
import {
  Skeleton,
  SkeletonHeader,
  SkeletonPage,
  SkeletonStats,
  SkeletonTable,
} from "@/components/skeleton";
import { UnauthorizedError } from "@/lib/api-client";

const reloaders = new Set<() => void>();

/** Load the data of every mounted page again. What `router.refresh()` did. */
export function refreshPage(): void {
  for (const reload of reloaders) reload();
}

class NotFoundSignal extends Error {}

class RedirectSignal extends Error {
  constructor(readonly to: string) {
    super(`Redirect to ${to}`);
  }
}

/** Inside a loader: this page does not exist. */
export function notFound(): never {
  throw new NotFoundSignal("Not found");
}

/** Inside a loader: this page lives somewhere else. */
export function redirect(to: string): never {
  throw new RedirectSignal(to);
}

export type PageState<T> =
  | { status: "loading" }
  | { status: "ready"; data: T }
  | { status: "failed"; error: unknown };

/**
 * Run `load` when the page mounts, whenever `deps` change, and on
 * `refreshPage()`. A refresh keeps the current data on screen while it
 * reloads, as a server refresh did; a change of `deps` (another brand, another
 * page of results) shows the loading state instead of the previous entity.
 */
export function usePageData<T>(load: () => Promise<T>, deps: readonly unknown[]): PageState<T> {
  const key = JSON.stringify(deps);
  const [result, setResult] = useState<{ key: string; state: PageState<T> } | null>(null);
  const [tick, setTick] = useState(0);
  const loader = useRef(load);

  // Declared before the loading effect, so it runs first in the same commit.
  useEffect(() => {
    loader.current = load;
  });

  useEffect(() => {
    const reload = () => setTick((value) => value + 1);
    reloaders.add(reload);
    return () => {
      reloaders.delete(reload);
    };
  }, []);

  useEffect(() => {
    let active = true;
    loader.current().then(
      (data) => {
        if (active) setResult({ key, state: { status: "ready", data } });
      },
      (error: unknown) => {
        if (active) setResult({ key, state: { status: "failed", error } });
      },
    );
    return () => {
      active = false;
    };
  }, [key, tick]);

  // A result for other deps is not this page's data: show the loading state
  // rather than the previous brand or the previous page of results.
  return result !== null && result.key === key ? result.state : { status: "loading" };
}

/** Render a page once its data is there; the loading, missing, moved and
 *  signed-out cases are handled here once, for every page. */
export function PageData<T>({
  state,
  children,
}: {
  state: PageState<T>;
  children: (data: T) => ReactNode;
}) {
  const router = useRouter();
  const error = state.status === "failed" ? state.error : undefined;

  useEffect(() => {
    if (error instanceof RedirectSignal) {
      router.replace(error.to);
    } else if (error instanceof UnauthorizedError) {
      const here = `${window.location.pathname}${window.location.search}`;
      window.location.replace(`/session/renew/?next=${encodeURIComponent(here)}`);
    }
  }, [error, router]);

  if (state.status === "loading") return <PageLoading />;
  if (state.status === "failed") {
    if (error instanceof NotFoundSignal) return <PageNotFound />;
    if (error instanceof RedirectSignal || error instanceof UnauthorizedError) {
      return <PageLoading />;
    }
    // Anything else is a real failure: app/error.tsx shows it, with a retry.
    throw error;
  }
  return <>{children(state.data)}</>;
}

export function PageLoading() {
  return (
    <SkeletonPage label="Loading your workspace…">
      <SkeletonHeader />
      <Skeleton className="h-48 rounded-2xl" />
      <SkeletonStats />
      <SkeletonTable rows={4} />
    </SkeletonPage>
  );
}

function PageNotFound() {
  return (
    <EmptyState
      title="Nothing here"
      description="This page does not exist, or it belongs to another account."
    />
  );
}

const UUID = "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}";

/**
 * The ids in the current URL.
 *
 * Not `useParams()`: the static export has one page per dynamic route, built
 * for the placeholder "_", and CloudFront serves it for every real id. The
 * params that page was built with are "_"; the address bar has the real ones.
 */
export function useRouteIds(): { brandId: string; campaignId: string; executionId: string } {
  const pathname = usePathname();
  const path = pathname.includes("/_") && typeof window !== "undefined"
    ? window.location.pathname
    : pathname;
  const after = (segment: string) =>
    path.match(new RegExp(`/${segment}/(${UUID})(?:/|$)`))?.[1] ?? "";
  return {
    brandId: after("brands"),
    campaignId: after("campaigns"),
    executionId: after("executions"),
  };
}
