"use client";

import { useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
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
  headline:
    "border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400",
  supporting: "border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-500",
  background: "border-border text-muted-foreground",
};

const GROUNDING_LABEL: Record<string, string> = {
  grounded: "from your material",
  inferred: "inferred",
  user_stated: "you told us",
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
      <div className="flex flex-wrap items-center gap-2">
        <Input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search everything we know — a price, a customer, an integration…"
          className="max-w-md"
        />
        {BANDS.map((option) => (
          <Button
            key={option}
            size="sm"
            variant={band === option ? "default" : "outline"}
            onClick={() => setBand(band === option ? null : option)}
          >
            {BAND_LABEL[option]}
          </Button>
        ))}
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
      </div>

      <div className="flex flex-wrap gap-2">
        <Button
          size="sm"
          variant={category === null ? "secondary" : "ghost"}
          onClick={() => setCategory(null)}
        >
          Everything ({base.total})
        </Button>
        {base.shelves.map((shelf) => (
          <Button
            key={shelf.category}
            size="sm"
            variant={category === shelf.category ? "secondary" : "ghost"}
            onClick={() => setCategory(category === shelf.category ? null : shelf.category)}
            className={cn(shelf.count === 0 && "text-muted-foreground/60")}
          >
            {shelf.label} ({shelf.count})
          </Button>
        ))}
      </div>

      {query !== "" || band !== null ? (
        <FlatResults entries={visible} />
      ) : (
        <div className="space-y-6">
          {shelves.map((shelf) => (
            <section key={shelf.category} className="space-y-3">
              <div>
                <h2 className="text-base font-semibold tracking-tight">
                  {shelf.label}{" "}
                  <span className="text-sm font-normal text-muted-foreground">
                    · {shelf.count} fact{shelf.count === 1 ? "" : "s"}
                    {shelf.headline_count > 0 && `, ${shelf.headline_count} can lead an email`}
                  </span>
                </h2>
                <p className="text-sm text-muted-foreground">
                  Answers: <span className="italic">{shelf.buyer_question}</span>
                </p>
              </div>
              {shelf.entries.length === 0 ? (
                <Card className="border-dashed">
                  <CardContent className="p-4 text-sm text-muted-foreground">
                    Nothing here yet. {shelf.when_empty}
                  </CardContent>
                </Card>
              ) : (
                <div className="grid gap-3 lg:grid-cols-2">
                  {shelf.entries.map((entry) => (
                    <EntryCard key={entry.id} entry={entry} />
                  ))}
                </div>
              )}
            </section>
          ))}
        </div>
      )}
    </div>
  );
}

function FlatResults({ entries }: { entries: KnowledgeEntry[] }) {
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
    <div className="grid gap-3 lg:grid-cols-2">
      {entries.map((entry) => (
        <EntryCard key={entry.id} entry={entry} />
      ))}
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
          <p className="border-l-2 border-border pl-3 text-muted-foreground">
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
