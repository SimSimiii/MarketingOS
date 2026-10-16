"use client";

import { useCallback, useEffect, useMemo, useRef, useState, useSyncExternalStore, type ComponentType } from "react";
import { useRouter } from "next/navigation";
import {
  Activity,
  AudioLines,
  BookOpen,
  Building2,
  CornerDownLeft,
  LayoutDashboard,
  Mail,
  Plus,
  Search,
  Settings2,
} from "lucide-react";

import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { api } from "@/lib/api-client";
import type { Brand, Campaign } from "@/lib/types";
import { cn } from "@/lib/utils";

interface Entry {
  id: string;
  label: string;
  hint: string;
  group: "Actions" | "Go to" | "Campaigns" | "Brands";
  href: string;
  icon: ComponentType<{ className?: string }>;
  /** Extra words the entry answers to without showing them. */
  keywords?: string;
}

const ACTIONS: Entry[] = [
  { id: "a-campaign", label: "New campaign", hint: "Write a brief", group: "Actions", href: "/campaigns?new=1", icon: Plus, keywords: "create write email" },
  { id: "a-brand", label: "New brand", hint: "Register a business", group: "Actions", href: "/brands?new=1", icon: Plus, keywords: "create business workspace" },
];

const PAGES: Entry[] = [
  { id: "p-home", label: "Overview", hint: "What is waiting on you", group: "Go to", href: "/", icon: LayoutDashboard },
  { id: "p-campaigns", label: "Campaigns", hint: "Every brief and its emails", group: "Go to", href: "/campaigns", icon: Mail },
  { id: "p-live", label: "Runs", hint: "What is running now", group: "Go to", href: "/live", icon: AudioLines, keywords: "live progress" },
  { id: "p-brands", label: "Brands", hint: "Knowledge, market and proof", group: "Go to", href: "/brands", icon: Building2 },
  { id: "p-sources", label: "Campaign sources", hint: "Material attached to one campaign", group: "Go to", href: "/knowledge", icon: BookOpen },
  { id: "p-logs", label: "Activity", hint: "Every line every run logged", group: "Go to", href: "/logs", icon: Activity, keywords: "logs" },
  { id: "p-settings", label: "Settings", hint: "Models, account and defaults", group: "Go to", href: "/settings", icon: Settings2, keywords: "account password" },
];

const OPEN_EVENT = "marketingos:command-palette";

const noSubscription = () => () => {};

/** "⌘K" on a Mac, "Ctrl K" elsewhere - and "Ctrl K" while the static HTML
 * is built, when there is no platform to ask. */
export function useShortcutLabel(): string {
  return useSyncExternalStore(
    noSubscription,
    () => (/Mac|iPhone|iPad/.test(navigator.platform) ? "⌘K" : "Ctrl K"),
    () => "Ctrl K",
  );
}

/** Open the palette from anywhere - a button in the sidebar, say. */
export function openCommandPalette() {
  window.dispatchEvent(new Event(OPEN_EVENT));
}

/** Every word of the query appears somewhere in the entry. Forgiving enough
 * for "res web" to find "Resend webhook event evaluation", strict enough that
 * a list of thirty does not return all thirty. */
function matches(entry: Entry, query: string): boolean {
  const haystack = `${entry.label} ${entry.hint} ${entry.keywords ?? ""}`.toLocaleLowerCase();
  return query
    .toLocaleLowerCase()
    .split(/\s+/)
    .filter(Boolean)
    .every((word) => haystack.includes(word));
}

/**
 * Jump anywhere with the keyboard: Ctrl+K (⌘K on a Mac).
 *
 * The console is a set of lists - brands, campaigns, runs - and reaching one
 * campaign meant the sidebar, a list, a scan and a click. With a dozen
 * campaigns that is already the slow part of coming back to the product.
 * Campaigns and brands are loaded when the palette opens, not before, so a
 * reader who never presses the shortcut never pays for it.
 */
export function CommandPalette() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const [data, setData] = useState<{ campaigns: Campaign[]; brands: Brand[] } | null>(null);
  const list = useRef<HTMLDivElement>(null);

  const show = useCallback(() => {
    setQuery("");
    setActive(0);
    setOpen(true);
  }, []);

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setOpen((value) => {
          if (!value) {
            setQuery("");
            setActive(0);
          }
          return !value;
        });
      }
    }
    window.addEventListener("keydown", onKey);
    window.addEventListener(OPEN_EVENT, show);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener(OPEN_EVENT, show);
    };
  }, [show]);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    Promise.all([
      api.listCampaigns(false, { limit: 100, offset: 0 }).catch(() => [] as Campaign[]),
      api.listBrands().catch(() => [] as Brand[]),
    ]).then(([campaigns, brands]) => {
      if (!cancelled) setData({ campaigns, brands });
    });
    return () => {
      cancelled = true;
    };
  }, [open]);

  const entries = useMemo(() => {
    const brandNames = new Map((data?.brands ?? []).map((brand) => [brand.id, brand.name]));
    const all: Entry[] = [
      ...ACTIONS,
      ...PAGES,
      ...(data?.campaigns ?? []).map((campaign) => ({
        id: `c-${campaign.id}`,
        label: campaign.name,
        hint: campaign.brand_id ? brandNames.get(campaign.brand_id) ?? "Campaign" : "One-off campaign",
        group: "Campaigns" as const,
        href: `/campaigns/${campaign.id}`,
        icon: Mail,
        keywords: campaign.request,
      })),
      ...(data?.brands ?? []).map((brand) => ({
        id: `b-${brand.id}`,
        label: brand.name,
        hint: brand.website_url?.replace(/^https?:\/\//, "").replace(/\/$/, "") ?? "Brand workspace",
        group: "Brands" as const,
        href: `/brands/${brand.id}`,
        icon: Building2,
      })),
    ];
    const found = query.trim() ? all.filter((entry) => matches(entry, query)) : all;
    // With nothing typed, the pages and the most recent campaigns - not a
    // scroll through every campaign ever written.
    if (!query.trim()) {
      return [
        ...found.filter((entry) => entry.group === "Actions"),
        ...found.filter((entry) => entry.group === "Go to"),
        ...found.filter((entry) => entry.group === "Campaigns").slice(0, 5),
        ...found.filter((entry) => entry.group === "Brands").slice(0, 5),
      ];
    }
    return found.slice(0, 30);
  }, [data, query]);

  const selected = Math.min(active, Math.max(0, entries.length - 1));

  useEffect(() => {
    list.current
      ?.querySelector(`[data-index="${selected}"]`)
      ?.scrollIntoView({ block: "nearest" });
  }, [selected]);

  function go(entry: Entry | undefined) {
    if (!entry) return;
    setOpen(false);
    router.push(entry.href);
  }

  function onKeyDown(event: React.KeyboardEvent) {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActive((selected + 1) % Math.max(1, entries.length));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActive((selected - 1 + entries.length) % Math.max(1, entries.length));
    } else if (event.key === "Enter") {
      event.preventDefault();
      go(entries[selected]);
    }
  }

  let lastGroup: Entry["group"] | null = null;

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent
        showCloseButton={false}
        className="top-[12%] translate-y-0 gap-0 overflow-hidden p-0 sm:max-w-2xl"
      >
        <DialogTitle className="sr-only">Jump to a page, campaign or brand</DialogTitle>
        <div className="flex items-center gap-3 border-b border-hairline px-5">
          <Search className="size-[1.125rem] shrink-0 text-violet-300" aria-hidden="true" />
          <input
            autoFocus
            value={query}
            onChange={(event) => {
              setQuery(event.target.value);
              setActive(0);
            }}
            onKeyDown={onKeyDown}
            placeholder="Jump to a campaign, brand or page…"
            aria-label="Search"
            role="combobox"
            aria-expanded="true"
            aria-controls="command-palette-list"
            aria-activedescendant={entries[selected] ? `cmd-${entries[selected].id}` : undefined}
            className="h-14 w-full bg-transparent text-[0.9375rem] outline-none placeholder:text-muted-foreground/70"
          />
          <kbd className="kbd hidden sm:inline-flex">Esc</kbd>
        </div>
        <div
          ref={list}
          id="command-palette-list"
          role="listbox"
          className="max-h-[min(26rem,60vh)] overflow-y-auto p-2"
        >
          {entries.length === 0 ? (
            <p className="px-3 py-10 text-center text-sm text-muted-foreground">
              {data === null ? "Loading…" : `Nothing matches “${query}”.`}
            </p>
          ) : (
            entries.map((entry, index) => {
              const heading = entry.group !== lastGroup ? entry.group : null;
              lastGroup = entry.group;
              const Icon = entry.icon;
              return (
                <div key={entry.id}>
                  {heading && (
                    <p className="px-3 pt-4 pb-1.5 text-[0.625rem] font-medium uppercase tracking-[0.2em] text-muted-foreground/80 first:pt-2">
                      {heading}
                    </p>
                  )}
                  <div
                    id={`cmd-${entry.id}`}
                    role="option"
                    aria-selected={index === selected}
                    data-index={index}
                    onMouseMove={() => setActive(index)}
                    onClick={() => go(entry)}
                    className={cn(
                      "flex cursor-pointer items-center gap-3 rounded-xl px-2.5 py-2 transition-colors",
                      index === selected
                        ? "bg-[linear-gradient(90deg,oklch(0.6_0.2_293/20%),oklch(0.6_0.2_293/5%))] text-foreground shadow-[0_0_0_1px_oklch(0.7_0.16_293/20%)]"
                        : "text-foreground/90",
                    )}
                  >
                    <span
                      className={cn(
                        "flex size-8 shrink-0 items-center justify-center rounded-lg border transition-colors",
                        index === selected
                          ? "border-violet-400/30 bg-violet-500/20 text-violet-200"
                          : "border-white/[0.06] bg-white/[0.03] text-muted-foreground",
                      )}
                    >
                      <Icon className="size-4" />
                    </span>
                    <span className="min-w-0 flex-1 truncate text-sm">{entry.label}</span>
                    <span className="hidden max-w-[40%] truncate text-xs text-muted-foreground sm:block">
                      {entry.hint}
                    </span>
                    {index === selected && (
                      <CornerDownLeft className="size-3.5 shrink-0 text-violet-300" aria-hidden="true" />
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>
        <div className="flex items-center gap-4 border-t border-hairline bg-black/20 px-5 py-2.5 text-[0.6875rem] text-muted-foreground">
          <span className="flex items-center gap-1.5"><kbd className="kbd">↑</kbd><kbd className="kbd">↓</kbd> to move</span>
          <span className="flex items-center gap-1.5"><kbd className="kbd">Enter</kbd> to open</span>
          <span className="ml-auto hidden items-center gap-1.5 sm:flex"><kbd className="kbd">Esc</kbd> to close</span>
        </div>
      </DialogContent>
    </Dialog>
  );
}
