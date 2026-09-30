"use client";

import { useCallback, useEffect, useMemo, useRef, useState, type ComponentType } from "react";
import { useRouter } from "next/navigation";
import {
  Activity,
  AudioLines,
  BookOpen,
  Building2,
  CornerDownLeft,
  LayoutDashboard,
  Mail,
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
  group: "Go to" | "Campaigns" | "Brands";
  href: string;
  icon: ComponentType<{ className?: string }>;
  /** Extra words the entry answers to without showing them. */
  keywords?: string;
}

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
        className="top-[15%] translate-y-0 gap-0 overflow-hidden p-0 sm:max-w-xl"
      >
        <DialogTitle className="sr-only">Jump to a page, campaign or brand</DialogTitle>
        <div className="flex items-center gap-3 border-b border-border px-4">
          <Search className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
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
            className="h-12 w-full bg-transparent text-sm outline-none placeholder:text-muted-foreground"
          />
          <kbd className="hidden rounded border border-border px-1.5 py-0.5 text-[10px] text-muted-foreground sm:inline">
            Esc
          </kbd>
        </div>
        <div
          ref={list}
          id="command-palette-list"
          role="listbox"
          className="max-h-[min(24rem,60vh)] overflow-y-auto p-2"
        >
          {entries.length === 0 ? (
            <p className="px-3 py-8 text-center text-sm text-muted-foreground">
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
                    <p className="px-3 pb-1 pt-3 text-[10px] font-medium uppercase tracking-[0.16em] text-muted-foreground first:pt-1">
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
                      "flex cursor-pointer items-center gap-3 rounded-lg px-3 py-2",
                      index === selected ? "bg-violet-500/15 text-foreground" : "text-foreground/90",
                    )}
                  >
                    <Icon
                      className={cn("size-4 shrink-0", index === selected ? "text-violet-300" : "text-muted-foreground")}
                    />
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
        <div className="flex items-center gap-4 border-t border-border bg-muted/30 px-4 py-2 text-[11px] text-muted-foreground">
          <span><kbd className="font-sans">↑ ↓</kbd> to move</span>
          <span><kbd className="font-sans">Enter</kbd> to open</span>
        </div>
      </DialogContent>
    </Dialog>
  );
}
