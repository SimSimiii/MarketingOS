"use client";

import { useState } from "react";

import { BrandDisclosure } from "../../brand-ui";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { AxisReading, Claim, Positioning, Territory } from "@/lib/types";

/** How each territory reads, in the user's terms rather than the model's.
 *
 * The `advice` line is the part that matters: a column headed "contested"
 * tells somebody nothing they can act on, and "argue these, never assert
 * them" tells them what to do on Monday. */
const TERRITORY: Record<
  Territory,
  { label: string; advice: string; tone: string; accent: string }
> = {
  open: {
    label: "Unmatched captured claims",
    advice: "Research potential differences. Missing captured claims do not establish exclusivity.",
    tone: "border-emerald-500/40 bg-emerald-500/5",
    accent: "text-emerald-400",
  },
  contested: {
    label: "Comparisons to inspect",
    advice: "Check the proposition, terms and limits before drawing a comparison.",
    tone: "border-sky-500/30 bg-sky-500/5",
    accent: "text-sky-400",
  },
  table_stakes: {
    label: "Equivalent captured claims",
    advice:
      "Common among the profiles read. Explain a supported detail rather than claiming uniqueness.",
    tone: "border-amber-500/30 bg-amber-500/5",
    accent: "text-amber-400",
  },
  exposed: {
    label: "Information to research",
    advice: "Our captured material has no match. This does not establish a weakness or missing feature.",
    tone: "border-rose-500/30 bg-rose-500/5",
    accent: "text-rose-400",
  },
};

const AXIS_LABEL: Record<string, string> = {
  speed: "Speed",
  price: "Price",
  breadth: "Coverage",
  quality: "Quality",
  effort: "Effort",
  control: "Control",
  security: "Security",
  proof: "Proof",
  support: "Support",
  other: "Other",
};

/** Claims shown per axis before the card is expanded. */
const VISIBLE_CLAIMS = 4;

function axisLabel(axis: string) {
  return AXIS_LABEL[axis] ?? axis;
}

const COMPARISON_LABEL: Record<string, string> = {
  equivalent: "Equivalent captured proposition",
  documented_difference: "Different figures on matching stated terms",
  potential_difference: "Scope or difference needs verification",
  unknown: "No equivalent captured; capability unknown",
};

function ClaimLine({ claim }: { claim: Claim }) {
  return (
    <li className="flex items-start gap-2">
      <span
        className={cn(
          "mt-1.5 size-1.5 shrink-0 rounded-full",
          claim.specific ? "bg-foreground/60" : "bg-foreground/20",
        )}
        title={claim.specific ? "carries a checkable detail" : "a broad assertion"}
      />
      <span className="text-muted-foreground">{claim.text}</span>
    </li>
  );
}

function AxisCard({ reading }: { reading: AxisReading }) {
  const [open, setOpen] = useState(false);
  const territory = TERRITORY[reading.territory];
  const rivals = Object.entries(reading.theirs);
  const notes = reading.comparison_notes ?? [];
  const comparisons = reading.comparisons ?? {};

  return (
    <div className={cn("rounded-lg border p-3", territory.tone)}>
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        className="flex w-full flex-wrap items-start justify-between gap-2 text-left"
      >
        <div className="min-w-0">
          <p className="text-xs text-muted-foreground">{axisLabel(reading.axis)}</p>
          <p className="text-sm font-medium">{reading.proposition || reading.ours[0]?.text || axisLabel(reading.axis)}</p>
          <p className="text-xs text-muted-foreground">
            {COMPARISON_LABEL[reading.comparison_status ?? "unknown"]}
          </p>
        </div>
        {reading.only_specific && (
          <Badge variant="outline" className={cn("shrink-0", territory.accent)}>
            more specific captured wording
          </Badge>
        )}
      </button>

      {notes.length > 0 && (
        <p className="mt-2 text-xs text-muted-foreground">
          {(open ? notes : notes.slice(0, 1)).join(" ")}
        </p>
      )}

      {reading.ours.length > 0 && (
        <>
          {/* Only the first few, ranked by what the fact is worth to a sale.
              A real ledger can put twenty claims on one axis, and a card that
              renders all of them is a card nobody reads to the end - which
              costs exactly the axis this column exists to point at. */}
          <ul className="mt-2 space-y-1 text-xs">
            {(open ? reading.ours : reading.ours.slice(0, VISIBLE_CLAIMS)).map((claim) => (
              <ClaimLine key={claim.text} claim={claim} />
            ))}
          </ul>
          {!open && reading.ours.length > VISIBLE_CLAIMS && (
            <p className="mt-1 text-xs text-muted-foreground">
              +{reading.ours.length - VISIBLE_CLAIMS} more
            </p>
          )}
        </>
      )}

      {open && rivals.length > 0 && (
        <div className="mt-3 space-y-2 border-t border-hairline pt-2 text-xs">
          {rivals.map(([name, claims]) => (
            <div key={name}>
              <p className="font-medium text-foreground/80">{name}</p>
              {comparisons[name] && (
                <p className="mt-1 text-muted-foreground">{COMPARISON_LABEL[comparisons[name]]}</p>
              )}
              <ul className="mt-1 space-y-1">
                {claims.map((claim) => (
                  <ClaimLine key={claim.text} claim={claim} />
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}

      {(rivals.length > 0 || reading.ours.length > VISIBLE_CLAIMS) && (
        <button
          type="button"
          onClick={() => setOpen((value) => !value)}
          aria-expanded={open}
          className="mt-3 min-h-9 cursor-pointer rounded-lg border border-white/10 bg-white/[0.035] px-3 text-xs font-medium text-foreground transition-colors hover:border-white/[0.16] hover:bg-white/[0.07]"
        >
          {open ? "Show less" : rivals.length > 0 ? "See what they say" : "See all"}
        </button>
      )}
    </div>
  );
}

function TerritoryColumn({
  territory,
  readings,
}: {
  territory: Territory;
  readings: AxisReading[];
}) {
  const meta = TERRITORY[territory];
  const [showAll, setShowAll] = useState(false);
  const visible = showAll ? readings : readings.slice(0, VISIBLE_CLAIMS);
  return (
    <div className="space-y-2">
      <div>
        <h3 className={cn("text-sm font-medium", meta.accent)}>{meta.label}</h3>
        <p className="text-xs text-muted-foreground">{meta.advice}</p>
      </div>
      {readings.length === 0 ? (
        <p className="rounded-xl bg-white/[0.025] p-3 text-xs text-muted-foreground ring-1 ring-white/[0.06]">
          Nothing here.
        </p>
      ) : (
        visible.map((reading, index) => (
          <AxisCard key={`${reading.axis}:${reading.proposition ?? "legacy"}:${index}`} reading={reading} />
        ))
      )}
      {readings.length > VISIBLE_CLAIMS && (
        <button
          type="button"
          onClick={() => setShowAll((value) => !value)}
          aria-expanded={showAll}
          className="min-h-9 cursor-pointer rounded-lg border border-white/10 bg-white/[0.035] px-3 text-xs font-medium text-foreground"
        >
          {showAll ? "Show fewer propositions" : `Show ${readings.length - VISIBLE_CLAIMS} more propositions`}
        </button>
      )}
    </div>
  );
}

/**
 * The positioning in one sentence, for the reader.
 *
 * The API's own `summary` is the line the strategist is briefed with -
 * "8 competitor(s) read - open ground on other" - which is written for a
 * model and reads to a person like a log line; "other" is a bucket name, not
 * ground anybody could stand on. This says the same thing from the same
 * readings, in the axis names the map below uses.
 */
export function positioningSentence(positioning: Positioning): string {
  const n = positioning.rivals_profiled;
  if (n === 0) return "No competitors read yet, so the copy is written blind to the field.";
  const open = [...new Set(positioning.readings
    .filter((reading) => reading.territory === "open")
    .map((reading) => (reading.axis === "other" ? "claims outside the usual categories" : axisLabel(reading.axis).toLowerCase())))];
  const ground = open.length > 0
    ? `Potential differences to verify: ${open.length === 1 ? open[0] : `${open.slice(0, -1).join(", ")} and ${open[open.length - 1]}`}.`
    : "No potential open ground identified in the captured claims.";
  const proof = positioning.proof_deficit
    ? ` ${positioning.rivals_with_proof} show customer proof; none was captured in your material.`
    : "";
  return `Read ${n} competitor${n === 1 ? "" : "s"}. ${ground}${proof}`;
}

export function PositioningMap({ positioning }: { positioning: Positioning }) {
  const byTerritory = (territory: Territory) =>
    positioning.readings.filter((reading) => reading.territory === territory);

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        This compares claims captured from the pages we could read. Unread pages and missed
        claims remain unknown. A missing claim does not prove that a competitor lacks a feature.
      </p>
      {positioning.proof_deficit && (
        <Card className="ring-amber-500/40">
          <CardHeader>
            <CardTitle className="text-base">
              {positioning.rivals_with_proof} of {positioning.rivals_profiled} competitors name a
              customer. No matching proof was captured in your material.
            </CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            Review the customer evidence they publish. If you have relevant, authorised customer
            quotes or results, add their sources. Do not invent proof to fill this gap.
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 md:grid-cols-2 2xl:grid-cols-4">
        <TerritoryColumn territory="open" readings={byTerritory("open")} />
        <TerritoryColumn territory="contested" readings={byTerritory("contested")} />
        <TerritoryColumn territory="table_stakes" readings={byTerritory("table_stakes")} />
        <TerritoryColumn territory="exposed" readings={byTerritory("exposed")} />
      </div>

      {positioning.crowd_words.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Shared category vocabulary</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <p className="text-sm text-muted-foreground">
              Two or more competitors use these words. Keep the vocabulary needed to explain your
              product. Sharing a term does not make a claim generic; explain the supported action,
              condition or benefit behind it.
            </p>
            <div className="flex flex-wrap gap-1.5">
              {positioning.crowd_words.map((word) => (
                <Badge key={word} variant="outline" className="font-normal">
                  {word}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <BrandDisclosure title="Strategy brief" description="The full positioning instructions available to your campaign strategist.">
        <pre className="max-h-96 overflow-auto rounded-xl bg-black/25 p-4 text-xs leading-relaxed ring-1 ring-white/[0.05] whitespace-pre-wrap text-muted-foreground">{positioning.brief_for_strategy}</pre>
      </BrandDisclosure>
    </div>
  );
}
