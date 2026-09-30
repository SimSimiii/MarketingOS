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

import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Compass } from "lucide-react";

import { EmptyState } from "@/components/empty-state";
import { buttonVariants } from "@/components/ui/button";
import BrandsLoading from "@/app/brands/loading";
import BrandLoading from "@/app/brands/[brandId]/loading";
import CampaignsLoading from "@/app/campaigns/loading";
import LiveLoading from "@/app/live/loading";
import LogsLoading from "@/app/logs/loading";
import SettingsLoading from "@/app/settings/loading";
import {
  Skeleton,
  SkeletonCampaign,
  SkeletonHeader,
  SkeletonPage,
  SkeletonRun,
  SkeletonSection,
  SkeletonStats,
  SkeletonTable,
} from "@/components/skeleton";
import { UnauthorizedError } from "@/lib/api-client";
import { normalizePath } from "@/lib/paths";

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

/** True inside a layout that has already drawn the page's chrome. */
const NestedPage = createContext(false);

/** Wrap a layout's children in this, and any page loading beneath it draws a
 * section-sized placeholder instead of a whole page. */
export function NestedPageProvider({ children }: { children: ReactNode }) {
  return <NestedPage.Provider value>{children}</NestedPage.Provider>;
}

/**
 * The page's own shape while its data is on the way.
 *
 * Every page used to draw the dashboard here - a hero and three stat tiles -
 * whatever it was about to become, so opening Activity flashed a layout that
 * was never going to arrive and then jumped. Each route already had a
 * `loading.tsx` in its own shape; with no server streaming them in, this is
 * the place that picks one.
 */
export function PageLoading() {
  const nested = useContext(NestedPage);
  const path = normalizePath(usePathname());
  if (nested) return <SkeletonSection />;
  if (/^\/campaigns\/[^/]+\/executions\//.test(path)) return <SkeletonRun />;
  if (/^\/campaigns\/[^/]+$/.test(path)) return <SkeletonCampaign />;
  if (path.startsWith("/campaigns") || path.startsWith("/knowledge")) return <CampaignsLoading />;
  if (/^\/brands\/[^/]+/.test(path)) return <BrandLoading />;
  if (path.startsWith("/brands")) return <BrandsLoading />;
  if (path.startsWith("/live")) return <LiveLoading />;
  if (path.startsWith("/logs")) return <LogsLoading />;
  if (path.startsWith("/settings")) return <SettingsLoading />;
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
      icon={Compass}
      title="Nothing here"
      description="This page does not exist, or it belongs to another account."
      action={
        <Link href="/" className={buttonVariants({ variant: "outline", size: "sm" })}>
          Back to overview
        </Link>
      }
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
