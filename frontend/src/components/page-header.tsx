import type { ReactNode } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import { DocumentTitle } from "@/components/document-title";

/**
 * The top of every page in the workspace.
 *
 * One component rather than an `h1` per route, because the type scale is the
 * cheapest signal that two pages belong to the same product - and before this
 * half the app opened at `text-3xl` with an eyebrow and half at `text-2xl`
 * without one, which reads as two products stitched together.
 *
 * The title is set in the display serif: it is the one line on the page that
 * is a headline rather than a label, and setting it apart from the interface
 * type is what makes the rest of the page read as instruments beneath it.
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
  documentTitle,
}: {
  eyebrow?: string;
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  backTo?: { href: string; label: string };
  /** Badges, counts, timings - the line that qualifies the title. */
  meta?: ReactNode;
  /** The browser tab's name, when `title` is not a plain string. */
  documentTitle?: string;
}) {
  return (
    <header className="rise space-y-5">
      <DocumentTitle title={documentTitle ?? (typeof title === "string" ? title : null)} />
      {backTo && (
        <Link
          href={backTo.href}
          className="group/back inline-flex max-w-full items-center gap-1.5 rounded-full border border-white/[0.08] bg-white/[0.03] py-1 pr-3 pl-2 text-xs font-medium text-muted-foreground transition-colors hover:border-white/15 hover:bg-white/[0.06] hover:text-foreground"
        >
          <ArrowLeft
            className="size-3.5 shrink-0 transition-transform group-hover/back:-translate-x-0.5"
            aria-hidden="true"
          />
          <span className="truncate">{backTo.label}</span>
        </Link>
      )}
      <div className="flex flex-wrap items-end justify-between gap-x-8 gap-y-5">
        <div className="min-w-0 max-w-3xl flex-1 basis-80">
          {eyebrow && <Eyebrow>{eyebrow}</Eyebrow>}
          <h1 className="font-display text-[2.375rem] leading-[1.05] tracking-[-0.01em] text-gradient sm:text-[2.875rem]">
            {title}
          </h1>
          {description && (
            <p className="mt-3 max-w-2xl text-[0.9375rem] leading-relaxed text-muted-foreground">
              {description}
            </p>
          )}
          {meta && (
            <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-muted-foreground">
              {meta}
            </div>
          )}
        </div>
        {actions && (
          <div className="flex flex-wrap items-center gap-2 sm:gap-2.5">{actions}</div>
        )}
      </div>
    </header>
  );
}

/** The small capitals over a title: which part of the product this is. */
export function Eyebrow({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <p
      className={
        "mb-3 flex items-center gap-2.5 text-[0.6875rem] font-medium uppercase tracking-[0.2em] text-violet-300/90 " +
        (className ?? "")
      }
    >
      <span
        className="h-px w-6 bg-gradient-to-r from-violet-400/80 to-transparent"
        aria-hidden="true"
      />
      {children}
    </p>
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
    <header className="flex flex-wrap items-end justify-between gap-x-6 gap-y-3">
      <div className="min-w-0 max-w-2xl">
        <h2 id={id} className="font-display text-[1.75rem] leading-tight tracking-[-0.005em]">
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

/** The quiet label over a group of rows - "Waiting on you", "Running now". */
export function GroupLabel({
  children,
  id,
  live = false,
  count,
}: {
  children: ReactNode;
  id?: string;
  live?: boolean;
  count?: number;
}) {
  return (
    <h2 id={id} className="flex items-center gap-2.5 text-[0.6875rem] font-medium uppercase tracking-[0.18em] text-muted-foreground">
      {live && <span className="live-dot" aria-hidden="true" />}
      {children}
      {count !== undefined && (
        <span className="rounded-full bg-white/[0.06] px-1.5 py-px text-[0.625rem] tracking-normal tabular-nums text-foreground/80">
          {count}
        </span>
      )}
      <span className="h-px flex-1 bg-gradient-to-r from-white/[0.08] to-transparent" aria-hidden="true" />
    </h2>
  );
}
