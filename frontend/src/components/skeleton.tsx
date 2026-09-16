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
      className={cn("rounded-md bg-muted motion-safe:animate-pulse", className)}
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
    <div className="space-y-3">
      {eyebrow && <Skeleton className="h-2.5 w-24" />}
      <Skeleton className="h-8 w-2/3 max-w-sm" />
      <Skeleton className="h-4 w-4/5 max-w-lg" />
    </div>
  );
}

/** A row of stat tiles, at the size `StatTile` actually renders. */
export function SkeletonStats({ count = 3 }: { count?: number }) {
  return (
    <div className="grid gap-4 sm:grid-cols-3">
      {Array.from({ length: count }, (_, index) => (
        <Skeleton key={index} className="h-[7.5rem] rounded-xl" />
      ))}
    </div>
  );
}

/** A card holding a list or a table. */
export function SkeletonTable({ rows = 5 }: { rows?: number }) {
  return (
    <div className="divide-y divide-border overflow-hidden rounded-xl border border-border bg-card">
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
