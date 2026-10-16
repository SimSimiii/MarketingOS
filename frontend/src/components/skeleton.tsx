import { cn } from "@/lib/utils";

/**
 * The shapes a page draws while it is waiting for its data.
 *
 * `app/loading.tsx` drew the dashboard for every route, so opening Activity or
 * Campaigns flashed a hero and three stat cards that were never going to
 * arrive - a layout shift dressed up as a loading state. These are the pieces
 * each route's own `loading.tsx` assembles into its own shape.
 *
 * Everything here is `aria-hidden`: the wrapper carries the one status message
 * a screen reader needs, and reading out a dozen empty boxes is worse than
 * silence.
 */
export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      aria-hidden="true"
      className={cn(
        "rounded-md bg-white/[0.045] bg-[linear-gradient(90deg,transparent_0%,oklch(1_0_0/5%)_45%,oklch(1_0_0/8%)_50%,oklch(1_0_0/5%)_55%,transparent_100%)] bg-[length:200%_100%] motion-safe:animate-shimmer",
        className,
      )}
    />
  );
}

/** The wrapper every `loading.tsx` opens with. */
export function SkeletonPage({
  label = "Loading…",
  children,
}: {
  label?: string;
  children: React.ReactNode;
}) {
  return (
    <div role="status" aria-label={label} className="space-y-8">
      <span className="sr-only">{label}</span>
      <div aria-hidden="true" className="space-y-8">
        {children}
      </div>
    </div>
  );
}

/** Eyebrow, title, description - the `PageHeader` every page opens with. */
export function SkeletonHeader({ eyebrow = true }: { eyebrow?: boolean }) {
  return (
    <div className="space-y-3.5">
      {eyebrow && <Skeleton className="h-2.5 w-28" />}
      <Skeleton className="h-11 w-2/3 max-w-sm rounded-lg" />
      <Skeleton className="h-4 w-4/5 max-w-lg" />
    </div>
  );
}

/** A row of stat tiles, at the size `StatTile` actually renders. */
export function SkeletonStats({ count = 3 }: { count?: number }) {
  return (
    <div className={cn("grid gap-4 sm:grid-cols-2", count === 4 ? "xl:grid-cols-4" : "lg:grid-cols-3")}>
      {Array.from({ length: count }, (_, index) => (
        <Skeleton key={index} className="h-[8.75rem] rounded-2xl" />
      ))}
    </div>
  );
}

/** A card holding a list or a table. */
export function SkeletonTable({ rows = 5 }: { rows?: number }) {
  return (
    <div className="surface divide-y divide-hairline overflow-hidden rounded-2xl">
      {Array.from({ length: rows }, (_, index) => (
        <div key={index} className="flex items-center gap-4 p-5">
          <Skeleton className="size-10 shrink-0 rounded-lg" />
          <div className="min-w-0 flex-1 space-y-2">
            <Skeleton className="h-4 w-1/3" />
            <Skeleton className="h-3 w-2/3" />
          </div>
          <Skeleton className="h-5 w-16 shrink-0 rounded-full" />
        </div>
      ))}
    </div>
  );
}

/** One section inside a layout that already drew its own chrome - a brand
 * tab, say. The layout's hero is on screen; drawing a second, page-sized
 * skeleton inside it reads as the page loading twice. */
export function SkeletonSection() {
  return (
    <SkeletonPage label="Loading…">
      <div className="space-y-2">
        <Skeleton className="h-5 w-48" />
        <Skeleton className="h-4 w-80 max-w-full" />
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Skeleton className="h-52 rounded-xl" />
        <Skeleton className="h-52 rounded-xl" />
      </div>
    </SkeletonPage>
  );
}

/** A campaign: header, the quoted brief, its facts beside the preset, runs. */
export function SkeletonCampaign() {
  return (
    <SkeletonPage label="Loading this campaign…">
      <SkeletonHeader />
      <Skeleton className="h-36 rounded-2xl" />
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_18rem]">
        <Skeleton className="h-28 rounded-xl" />
        <Skeleton className="h-40 rounded-xl" />
      </div>
      <SkeletonTable rows={3} />
    </SkeletonPage>
  );
}

/** A run: header, the scorecard, then the emails themselves. */
export function SkeletonRun() {
  return (
    <SkeletonPage label="Loading this run…">
      <SkeletonHeader />
      <Skeleton className="h-24 rounded-xl" />
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="space-y-4">
          <Skeleton className="h-96 rounded-xl" />
          <Skeleton className="h-48 rounded-xl" />
        </div>
        <Skeleton className="h-72 rounded-xl" />
      </div>
    </SkeletonPage>
  );
}
