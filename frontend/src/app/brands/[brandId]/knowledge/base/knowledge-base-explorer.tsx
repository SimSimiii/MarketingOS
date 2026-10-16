"use client";

import { useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { FilterPills, SearchField, Toolbar } from "@/components/toolbar";
import { cn } from "@/lib/utils";
import type { FactCategory, KnowledgeBase, KnowledgeEntry, ValueBand } from "@/lib/types";

/** What each band means where the user reads it. The score is on the card for
 * anyone who wants it; the band is what a person actually decides on. */
const BAND_LABEL: Record<ValueBand, string> = {
  headline: "Can lead an email",
  supporting: "Worth a line",
  background: "Context only",
};

const BAND_CLASS: Record<ValueBand, string> = {
  headline: "border-emerald-400/25 bg-emerald-400/10 text-emerald-300",
  supporting: "border-amber-400/25 bg-amber-400/10 text-amber-300",
  background: "border-white/10 text-muted-foreground",
};

const GROUNDING_LABEL: Record<string, string> = {
  grounded: "from your material",
  inferred: "inferred",
  user_stated: "you told us",
  vendor_claim: "your material claims this",
};

const BANDS: ValueBand[] = ["headline", "supporting", "background"];

export function KnowledgeBaseExplorer({ base }: { base: KnowledgeBase }) {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState<FactCategory | null>(null);
  const [band, setBand] = useState<ValueBand | null>(null);

  const entries = useMemo(
    () => base.shelves.flatMap((shelf) => shelf.entries),
    [base.shelves],
  );

  // Word overlap rather than substring, so "pricing team plan" finds the Team
  // plan without the user having to guess how the compiler phrased it. The
  // whole base is already client-side, so this costs nothing per keystroke.
  const terms = useMemo(
    () => query.toLowerCase().match(/[a-z0-9]+/g)?.filter((word) => word.length > 1) ?? [],
    [query],
  );

  const visible = useMemo(() => {
    const matched = entries
      .filter((entry) => (category === null || entry.category === category))
      .filter((entry) => (band === null || entry.band === band))
      .map((entry) => {
        if (terms.length === 0) return { entry, overlap: 0 };
        const haystack = `${entry.statement} ${entry.verbatim} ${entry.tags.join(" ")}`;
        const words = new Set(haystack.toLowerCase().match(/[a-z0-9]+/g) ?? []);
        return { entry, overlap: terms.filter((term) => words.has(term)).length };
      })
      .filter(({ overlap }) => terms.length === 0 || overlap > 0);
    if (terms.length > 0) {
      matched.sort((a, b) => b.overlap - a.overlap || b.entry.value - a.entry.value);
    }
    return matched.map(({ entry }) => entry);
  }, [entries, category, band, terms]);

  const filtering = query !== "" || category !== null || band !== null;
  const shelves = base.shelves.filter((shelf) => category === null || shelf.category === category);

  return (
    <div className="space-y-5">
      <Toolbar>
        <SearchField
          label="Search knowledge"
          value={query}
          onChange={setQuery}
          placeholder="Search everything we know — a price, a customer, an integration…"
        />
        <FilterPills
          label="Filter by strength"
          value={band ?? "any"}
          onChange={(value) => setBand(value === "any" ? null : value)}
          options={[
            { value: "any" as const, label: "Any strength" },
            ...BANDS.map((option) => ({ value: option, label: BAND_LABEL[option] })),
          ]}
        />
        {filtering && (
          <Button
            size="sm"
            variant="ghost"
            onClick={() => {
              setQuery("");
              setCategory(null);
              setBand(null);
            }}
          >
            Clear
          </Button>
        )}
      </Toolbar>

      <div role="group" aria-label="Shelves" className="flex flex-wrap gap-2">
        <ShelfChip active={category === null} onClick={() => setCategory(null)} label="Everything" count={base.total} />
        {base.shelves.map((shelf) => (
          <ShelfChip
            key={shelf.category}
            active={category === shelf.category}
            onClick={() => setCategory(category === shelf.category ? null : shelf.category)}
            label={shelf.label}
            count={shelf.count}
          />
        ))}
      </div>

      {query !== "" || band !== null ? (
        <FlatResults entries={visible} />
      ) : (
        <div className="space-y-10">
          {shelves.map((shelf) => (
            <section key={shelf.category} className="space-y-4">
              <div className="border-b border-hairline pb-3">
                <h2 className="font-display text-[1.625rem] leading-tight">
                  {shelf.label}{" "}
                  <span className="font-sans text-sm font-normal text-muted-foreground">
                    · {shelf.count} fact{shelf.count === 1 ? "" : "s"}
                    {shelf.headline_count > 0 && `, ${shelf.headline_count} can lead an email`}
                  </span>
                </h2>
                <p className="text-sm text-muted-foreground">
                  Answers: <span className="italic">{shelf.buyer_question}</span>
                </p>
              </div>
              {shelf.entries.length === 0 ? (
                <Card className="bg-transparent bg-none shadow-none ring-white/[0.06] [--card-spacing:--spacing(4)]">
                  <CardContent className="text-sm text-muted-foreground">
                    Nothing here yet. {shelf.when_empty}
                  </CardContent>
                </Card>
              ) : (
                <ShelfEntries entries={shelf.entries} expanded={category === shelf.category} />
              )}
            </section>
          ))}
        </div>
      )}
    </div>
  );
}

/** How many facts a shelf shows before it is asked for the rest. */
const SHELF_PREVIEW = 4;

/**
 * One shelf's facts, strongest first, the rest behind a button.
 *
 * Every fact of every shelf used to render at once - 237 cards, a page
 * thirty thousand pixels tall - so the shelf headings that make the base
 * navigable were a screen apart. The best few answer "what do we have here";
 * the rest are one click away, and a shelf picked from the filter above opens
 * in full.
 */
function ShelfEntries({ entries, expanded }: { entries: KnowledgeEntry[]; expanded: boolean }) {
  const [showAll, setShowAll] = useState(false);
  const ranked = useMemo(() => [...entries].sort((a, b) => b.value - a.value), [entries]);
  const all = expanded || showAll;
  const shown = all ? ranked : ranked.slice(0, SHELF_PREVIEW);
  return (
    <div className="space-y-3">
      <div className="grid gap-3 lg:grid-cols-2">
        {shown.map((entry) => (
          <EntryCard key={entry.id} entry={entry} />
        ))}
      </div>
      {!expanded && ranked.length > SHELF_PREVIEW && (
        <Button size="sm" variant="ghost" onClick={() => setShowAll(!showAll)}>
          {showAll ? "Show the strongest only" : `Show all ${ranked.length}`}
        </Button>
      )}
    </div>
  );
}

/** Search results arrive in pages of this size. */
const RESULT_PAGE = 40;

function FlatResults({ entries }: { entries: KnowledgeEntry[] }) {
  const [limit, setLimit] = useState(RESULT_PAGE);
  if (entries.length === 0) {
    return (
      <Card>
        <CardContent className="p-6 text-sm text-muted-foreground">
          Nothing matches. If it is true and it is not here, the material we read never said it —
          add the page that does and the next run will pick it up.
        </CardContent>
      </Card>
    );
  }
  return (
    <div className="space-y-3">
      <p role="status" className="text-xs text-muted-foreground">
        {entries.length} fact{entries.length === 1 ? "" : "s"} match
      </p>
      <div className="grid gap-3 lg:grid-cols-2">
        {entries.slice(0, limit).map((entry) => (
          <EntryCard key={entry.id} entry={entry} />
        ))}
      </div>
      {entries.length > limit && (
        <Button size="sm" variant="outline" onClick={() => setLimit(limit + RESULT_PAGE)}>
          Show {Math.min(RESULT_PAGE, entries.length - limit)} more
        </Button>
      )}
    </div>
  );
}

function EntryCard({ entry }: { entry: KnowledgeEntry }) {
  const [open, setOpen] = useState(false);
  return (
    <Card>
      <CardContent className="space-y-2 p-4 text-sm">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="outline" className={BAND_CLASS[entry.band]}>
            {BAND_LABEL[entry.band]}
          </Badge>
          <Badge variant="secondary">{entry.kind || entry.origin}</Badge>
          {entry.citable && <Badge variant="outline">citable as {entry.id}</Badge>}
          <span className="ml-auto text-xs tabular-nums text-muted-foreground">
            {entry.value}/100
          </span>
        </div>

        <p className="font-medium">{entry.statement}</p>

        {entry.verbatim && (
          <p className="border-l-2 border-violet-400/30 pl-3 text-muted-foreground">
            &ldquo;{entry.verbatim}&rdquo;
          </p>
        )}

        <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          <span>{GROUNDING_LABEL[entry.grounding] ?? entry.grounding}</span>
          {entry.source && (
            <>
              <span>·</span>
              <span className="truncate">{entry.source}</span>
            </>
          )}
          {entry.tags.map((tag) => (
            <Badge key={tag} variant="ghost" className="text-xs">
              {tag}
            </Badge>
          ))}
        </div>

        {/* The score is only worth showing if the user can argue with it. */}
        <button
          type="button"
          onClick={() => setOpen(!open)}
          className="text-xs text-muted-foreground underline underline-offset-2 hover:text-foreground"
        >
          {open ? "Hide" : "Why this score?"}
        </button>
        {open && (
          <ul className="list-disc space-y-1 pl-5 text-xs text-muted-foreground">
            {entry.why.map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

/** One shelf in the row above the facts: a pill with how much it holds. */
function ShelfChip({
  active,
  onClick,
  label,
  count,
}: {
  active: boolean;
  onClick: () => void;
  label: string;
  count: number;
}) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className={cn(
        "inline-flex h-8 cursor-pointer items-center gap-2 rounded-full border px-3.5 text-[0.8125rem] font-medium transition-all focus-visible:ring-3 focus-visible:ring-ring/45 focus-visible:outline-none",
        active
          ? "border-violet-400/40 bg-violet-500/20 text-violet-100 shadow-[0_6px_18px_-8px_oklch(0.6_0.22_293/70%)]"
          : count === 0
            ? "border-white/[0.06] text-muted-foreground/60 hover:text-muted-foreground"
            : "border-white/10 bg-white/[0.03] text-foreground/85 hover:border-white/20 hover:bg-white/[0.06]",
      )}
    >
      {label}
      <span className={cn("tabular-nums", active ? "text-violet-200" : "text-muted-foreground")}>{count}</span>
    </button>
  );
}
