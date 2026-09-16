import type { ReactNode } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

/**
 * The top of every page in the workspace.
 *
 * One component rather than an `h1` per route, because the type scale is the
 * cheapest signal that two pages belong to the same product - and before this
 * half the app opened at `text-3xl` with an eyebrow and half at `text-2xl`
 * without one, which reads as two products stitched together.
 *
 * `backTo` is for the pages you arrive at from a list. A detail page whose
 * only way back is the sidebar makes the reader guess which top-level section
 * they came from.
 */
export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
  backTo,
  meta,
}: {
  eyebrow?: string;
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  backTo?: { href: string; label: string };
  /** Badges, counts, timings - the line that qualifies the title. */
  meta?: ReactNode;
}) {
  return (
    <header className="space-y-4">
      {backTo && (
        <Link
          href={backTo.href}
          className="inline-flex items-center gap-1.5 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground"
        >
          <ArrowLeft className="size-3.5" aria-hidden="true" />
          {backTo.label}
        </Link>
      )}
      <div className="flex flex-wrap items-start justify-between gap-x-6 gap-y-4">
        <div className="min-w-0 max-w-2xl">
          {eyebrow && (
            <p className="mb-2.5 text-[10px] font-medium uppercase tracking-[0.2em] text-violet-300">
              {eyebrow}
            </p>
          )}
          <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">{title}</h1>
          {description && (
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{description}</p>
          )}
          {meta && (
            <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-muted-foreground">
              {meta}
            </div>
          )}
        </div>
        {actions && <div className="flex flex-wrap items-center gap-2 sm:gap-3">{actions}</div>}
      </div>
    </header>
  );
}

/**
 * The heading for a block inside a page. One step down from `PageHeader`, and
 * the thing to reach for instead of a bare `h2` so the gap between a page
 * title and a section title is the same gap everywhere.
 */
export function SectionHeading({
  title,
  description,
  actions,
  id,
}: {
  title: string;
  description?: ReactNode;
  actions?: ReactNode;
  id?: string;
}) {
  return (
    <header className="flex flex-wrap items-start justify-between gap-x-6 gap-y-3">
      <div className="min-w-0 max-w-2xl">
        <h2 id={id} className="text-lg font-semibold tracking-tight">
          {title}
        </h2>
        {description && (
          <p className="mt-1 text-sm leading-relaxed text-muted-foreground">{description}</p>
        )}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </header>
  );
}
