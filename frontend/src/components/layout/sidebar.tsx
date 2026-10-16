"use client";

import { useEffect, useState, type ComponentType } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Dialog as DialogPrimitive } from "@base-ui/react/dialog";
import {
  Activity,
  AudioLines,
  BookOpen,
  Building2,
  LayoutDashboard,
  Mail,
  Menu,
  Search,
  Settings2,
  Sparkles,
  X,
} from "lucide-react";

import { openCommandPalette, useShortcutLabel } from "@/components/command-palette";
import { AccountMenu } from "@/components/layout/account-menu";
import { api, readAccessToken } from "@/lib/api-client";
import { AUTH_REQUIRED } from "@/lib/config";
import { normalizePath } from "@/lib/paths";
import { cn } from "@/lib/utils";

interface NavItem {
  href: string;
  label: string;
  icon: ComponentType<{ className?: string }>;
  /** Shows how many runs are in progress beside it. */
  live?: boolean;
}

// Knowledge and market remain inside each brand's workspace. Grouped by what
// the reader is doing - making things, keeping the material they are made
// from, and looking after the system - so seven links read as three choices.
const NAV_GROUPS: { label: string; items: NavItem[] }[] = [
  {
    label: "Studio",
    items: [
      { href: "/", label: "Overview", icon: LayoutDashboard },
      { href: "/campaigns", label: "Campaigns", icon: Mail },
      { href: "/live", label: "Runs", icon: AudioLines, live: true },
    ],
  },
  {
    label: "Library",
    items: [
      { href: "/brands", label: "Brands", icon: Building2 },
      { href: "/knowledge", label: "Campaign sources", icon: BookOpen },
    ],
  },
  {
    label: "System",
    items: [
      { href: "/logs", label: "Activity", icon: Activity },
      { href: "/settings", label: "Settings", icon: Settings2 },
    ],
  },
];

const ALL_ITEMS = NAV_GROUPS.flatMap((group) => group.items);

function activeHrefFor(pathname: string): string | undefined {
  return ALL_ITEMS.find((item) =>
    item.href === "/" ? pathname === "/" : pathname === item.href || pathname.startsWith(`${item.href}/`),
  )?.href;
}

/**
 * How many campaign runs are going right now.
 *
 * Asked once per navigation rather than on a timer: the Runs page itself is
 * refreshed by hand on purpose, and a sidebar polling behind every page would
 * be the only thing in the console spending requests while nobody reads it.
 * Moving between pages is when the reader looks at the sidebar anyway.
 */
function useRunningCount(pathname: string): number {
  const [count, setCount] = useState(0);
  useEffect(() => {
    if (AUTH_REQUIRED && readAccessToken() === undefined) return;
    let cancelled = false;
    api
      .listRunningExecutions()
      .then((runs) => {
        if (!cancelled) setCount(runs.length);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [pathname]);
  return count;
}

function Wordmark({ compact = false }: { compact?: boolean }) {
  return (
    <span className="flex items-center gap-3">
      <span
        className={cn(
          "brand-mark flex shrink-0 items-center justify-center rounded-[0.7rem] text-white",
          compact ? "size-8" : "size-9",
        )}
      >
        <Sparkles className={compact ? "size-4" : "size-[1.15rem]"} aria-hidden="true" />
      </span>
      <span className="leading-none">
        <span className="block text-[1.0625rem] font-semibold tracking-tight">
          Marketing<span className="text-gradient-accent">OS</span>
        </span>
        {!compact && (
          <span className="mt-1 block text-[0.625rem] font-medium uppercase tracking-[0.22em] text-muted-foreground">
            Email studio
          </span>
        )}
      </span>
    </span>
  );
}

function NavLinks({
  pathname,
  running,
  onNavigate,
}: {
  pathname: string;
  running: number;
  onNavigate?: () => void;
}) {
  const activeHref = activeHrefFor(pathname);
  return (
    <nav aria-label="Main navigation" className="space-y-6">
      {NAV_GROUPS.map((group) => (
        <div key={group.label}>
          <p className="mb-2 px-3 text-[0.625rem] font-medium uppercase tracking-[0.22em] text-muted-foreground/70">
            {group.label}
          </p>
          <ul className="space-y-0.5">
            {group.items.map(({ href, label, icon: Icon, live }) => {
              const active = href === activeHref;
              return (
                <li key={href}>
                  <Link
                    href={href}
                    onClick={onNavigate}
                    aria-current={active ? "page" : undefined}
                    className={cn(
                      "group/nav relative flex items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium transition-all duration-200",
                      active
                        ? "bg-[linear-gradient(90deg,oklch(0.6_0.2_293/22%),oklch(0.6_0.2_293/6%))] text-foreground shadow-[inset_0_1px_0_0_oklch(1_0_0/6%),0_0_0_1px_oklch(0.7_0.16_293/22%)]"
                        : "text-muted-foreground hover:bg-white/[0.045] hover:text-foreground",
                    )}
                  >
                    {/* A lit bar down the left edge rather than a dot on the
                        right: the eye finds the start of a row before its end. */}
                    {active && (
                      <span
                        className="absolute inset-y-2 -left-3 w-[3px] rounded-r-full bg-violet-400 shadow-[0_0_12px_oklch(0.7_0.2_293/90%)]"
                        aria-hidden="true"
                      />
                    )}
                    <span
                      className={cn(
                        "flex size-7 shrink-0 items-center justify-center rounded-lg transition-colors",
                        active
                          ? "bg-violet-500/20 text-violet-200"
                          : "text-muted-foreground group-hover/nav:text-foreground",
                      )}
                    >
                      <Icon className="size-4" aria-hidden="true" />
                    </span>
                    <span className="flex-1 truncate">{label}</span>
                    {live && running > 0 && (
                      <span
                        className="flex items-center gap-1.5 rounded-full bg-violet-500/15 px-2 py-0.5 text-[0.6875rem] font-semibold tabular-nums text-violet-200 ring-1 ring-violet-400/25"
                        title={`${running} run${running === 1 ? "" : "s"} in progress`}
                      >
                        <span className="live-dot !size-1.5" aria-hidden="true" />
                        {running}
                        <span className="sr-only"> running</span>
                      </span>
                    )}
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </nav>
  );
}

function SearchButton({ onOpen }: { onOpen?: () => void }) {
  const shortcut = useShortcutLabel();
  return (
    <button
      type="button"
      onClick={() => {
        onOpen?.();
        openCommandPalette();
      }}
      className="group/search flex w-full cursor-pointer items-center gap-2.5 rounded-xl border border-white/[0.08] bg-black/20 px-3 py-2.5 text-sm text-muted-foreground shadow-[inset_0_1px_2px_0_oklch(0_0_0/25%)] transition-colors hover:border-violet-400/30 hover:text-foreground"
    >
      <Search className="size-4 transition-colors group-hover/search:text-violet-300" aria-hidden="true" />
      <span className="flex-1 text-left">Jump to…</span>
      <kbd className="kbd hidden lg:inline-flex">{shortcut}</kbd>
    </button>
  );
}

function SidebarFooter() {
  if (AUTH_REQUIRED) return <AccountMenu />;
  return (
    <div className="mx-3 mb-4 flex items-center gap-3 rounded-xl border border-white/[0.06] bg-white/[0.025] px-3 py-2.5">
      <span className="size-1.5 shrink-0 rounded-full bg-emerald-400 shadow-[0_0_8px_oklch(0.8_0.17_160/80%)]" aria-hidden="true" />
      <span className="min-w-0 leading-tight">
        <span className="block text-xs font-medium">Single workspace</span>
        <span className="block truncate text-[0.6875rem] text-muted-foreground">No sign-in on this install</span>
      </span>
    </div>
  );
}

/** The desktop sidebar, from `lg` up. */
export function Sidebar() {
  const pathname = normalizePath(usePathname());
  const running = useRunningCount(pathname);

  return (
    <aside className="glass sticky top-0 hidden h-dvh w-[16.5rem] shrink-0 flex-col border-r border-white/[0.06] text-sidebar-foreground lg:flex">
      {/* A seam of light down the inside edge, where the sidebar meets the
          page - it separates the two without a heavier border. */}
      <span
        aria-hidden="true"
        className="pointer-events-none absolute inset-y-0 right-0 w-px bg-gradient-to-b from-violet-400/30 via-white/[0.04] to-transparent"
      />
      <Link href="/" className="mx-3 mt-5 mb-5 rounded-xl px-3 py-2" aria-label="MarketingOS home">
        <Wordmark />
      </Link>
      <div className="px-3 pb-6">
        <SearchButton />
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto px-3 pb-6">
        <NavLinks pathname={pathname} running={running} />
      </div>
      <SidebarFooter />
    </aside>
  );
}

/**
 * The phone and tablet header: the mark, the palette, and a drawer holding
 * the same navigation the desktop sidebar shows.
 *
 * It used to be a strip of links scrolling sideways under the logo, with the
 * last two cut off by the edge of the screen and nothing to say they were
 * there. A drawer shows every destination at once, grouped the same way.
 */
export function MobileHeader() {
  const pathname = normalizePath(usePathname());
  const running = useRunningCount(pathname);
  const [open, setOpen] = useState(false);

  return (
    <header className="glass sticky top-0 z-40 flex items-center justify-between gap-3 border-b border-white/[0.06] px-4 py-3 lg:hidden">
      <Link href="/" aria-label="MarketingOS home" className="rounded-lg">
        <Wordmark compact />
      </Link>
      <div className="flex items-center gap-2">
        {running > 0 && (
          <Link
            href="/live"
            className="flex items-center gap-1.5 rounded-full bg-violet-500/15 px-2.5 py-1 text-xs font-semibold tabular-nums text-violet-200 ring-1 ring-violet-400/25"
          >
            <span className="live-dot !size-1.5" aria-hidden="true" />
            {running}
            <span className="sr-only"> runs in progress</span>
          </Link>
        )}
        <button
          type="button"
          onClick={openCommandPalette}
          aria-label="Jump to a campaign, brand or page"
          className="flex size-9 cursor-pointer items-center justify-center rounded-xl border border-white/[0.08] bg-white/[0.03] text-muted-foreground transition-colors hover:text-foreground"
        >
          <Search className="size-4" aria-hidden="true" />
        </button>
        <DialogPrimitive.Root open={open} onOpenChange={setOpen}>
          <DialogPrimitive.Trigger
            aria-label="Open navigation"
            className="flex size-9 cursor-pointer items-center justify-center rounded-xl border border-white/[0.08] bg-white/[0.03] text-muted-foreground transition-colors hover:text-foreground"
          >
            <Menu className="size-4" aria-hidden="true" />
          </DialogPrimitive.Trigger>
          <DialogPrimitive.Portal>
            <DialogPrimitive.Backdrop className="fixed inset-0 z-50 bg-[oklch(0.08_0.02_285/70%)] backdrop-blur-sm transition-opacity duration-300 data-[ending-style]:opacity-0 data-[starting-style]:opacity-0" />
            <DialogPrimitive.Popup className="fixed inset-y-0 left-0 z-50 flex w-[min(19rem,86vw)] flex-col overflow-y-auto border-r border-white/[0.08] bg-sidebar bg-[radial-gradient(ellipse_100%_40%_at_0%_0%,oklch(0.5_0.2_293/18%),transparent_70%)] shadow-[24px_0_80px_-20px_oklch(0_0_0/80%)] transition-transform duration-300 ease-[cubic-bezier(0.22,1,0.36,1)] outline-none data-[ending-style]:-translate-x-full data-[starting-style]:-translate-x-full">
              <DialogPrimitive.Title className="sr-only">Navigation</DialogPrimitive.Title>
              <div className="flex items-center justify-between px-5 pt-5 pb-5">
                <Wordmark />
                <DialogPrimitive.Close
                  aria-label="Close navigation"
                  className="flex size-9 cursor-pointer items-center justify-center rounded-xl text-muted-foreground transition-colors hover:bg-white/[0.06] hover:text-foreground"
                >
                  <X className="size-4" aria-hidden="true" />
                </DialogPrimitive.Close>
              </div>
              <div className="px-4 pb-6">
                <SearchButton onOpen={() => setOpen(false)} />
              </div>
              <div className="flex-1 px-4 pb-6">
                <NavLinks pathname={pathname} running={running} onNavigate={() => setOpen(false)} />
              </div>
              <SidebarFooter />
            </DialogPrimitive.Popup>
          </DialogPrimitive.Portal>
        </DialogPrimitive.Root>
      </div>
    </header>
  );
}
