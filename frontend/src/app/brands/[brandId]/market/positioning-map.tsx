"use client";

import { useState } from "react";

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
    label: "Yours alone",
    advice: "Lead an email here. A claim nobody else makes beats a stronger claim everybody makes.",
    tone: "border-emerald-500/40 bg-emerald-500/5",
    accent: "text-emerald-400",
  },
  contested: {
    label: "Contested",
    advice: "Usable, but the reader has heard it. Argue these — never assert them.",
    tone: "border-sky-500/30 bg-sky-500/5",
    accent: "text-sky-400",
  },
  table_stakes: {
    label: "Table stakes",
    advice:
      "True, and worth nothing as an argument. An email leading on one of these is an email they have already had.",
    tone: "border-amber-500/30 bg-amber-500/5",
    accent: "text-amber-400",
  },
  exposed: {
    label: "Where they are ahead",
    advice: "Do not raise these — an email that invites this comparison loses it.",
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

function ClaimLine({ claim }: { claim: Claim }) {
  return (
    <li className="flex items-start gap-2">
      <span
        className={cn(
          "mt-1.5 size-1.5 shrink-0 rounded-full",
          claim.specific ? "bg-foreground/60" : "bg-foreground/20",
        )}
        title={claim.specific ? "carries a checkable figure" : "an assertion, no figure"}
      />
      <span className="text-muted-foreground">{claim.text}</span>
    </li>
  );
}

function AxisCard({ reading }: { reading: AxisReading }) {
  const [open, setOpen] = useState(false);
  const territory = TERRITORY[reading.territory];
  const rivals = Object.entries(reading.theirs);

  return (
    <div className={cn("rounded-lg border p-3", territory.tone)}>
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="flex w-full items-start justify-between gap-2 text-left"
      >
        <div className="min-w-0">
          <p className="text-sm font-medium">{axisLabel(reading.axis)}</p>
          <p className="text-xs text-muted-foreground">
            {rivals.length === 0
              ? "nobody else claims it"
              : `${rivals.length} competitor${rivals.length === 1 ? "" : "s"} claim${
                  rivals.length === 1 ? "s" : ""
                } it too`}
          </p>
        </div>
        {reading.only_specific && (
          <Badge variant="outline" className={cn("shrink-0", territory.accent)}>
            only one with a number
          </Badge>
        )}
      </button>

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
        <div className="mt-3 space-y-2 border-t border-border/50 pt-2 text-xs">
          {rivals.map(([name, claims]) => (
            <div key={name}>
              <p className="font-medium text-foreground/80">{name}</p>
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
          className="mt-2 text-xs text-muted-foreground hover:text-foreground"
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
  return (
    <div className="space-y-2">
      <div>
        <h3 className={cn("text-sm font-medium", meta.accent)}>{meta.label}</h3>
        <p className="text-xs text-muted-foreground">{meta.advice}</p>
      </div>
      {readings.length === 0 ? (
        <p className="rounded-lg border border-dashed border-border/60 p-3 text-xs text-muted-foreground">
          Nothing here.
        </p>
      ) : (
        readings.map((reading) => <AxisCard key={reading.axis} reading={reading} />)
      )}
    </div>
  );
}

export function PositioningMap({ positioning }: { positioning: Positioning }) {
  const [showBrief, setShowBrief] = useState(false);
  const byTerritory = (territory: Territory) =>
    positioning.readings.filter((reading) => reading.territory === territory);

  return (
    <div className="space-y-4">
      {positioning.proof_deficit && (
        <Card className="ring-amber-500/40">
          <CardHeader>
            <CardTitle className="text-base">
              {positioning.rivals_with_proof} of {positioning.rivals_profiled} competitors name a
              customer. You name none.
            </CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            A reader comparing you is not comparing two sets of claims — they are comparing a
            claim to a claim with somebody&rsquo;s name under it. Three customer names and one
            sentence each is an afternoon&rsquo;s work, and it is the largest single gap between
            your copy and theirs.
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-4">
        <TerritoryColumn territory="open" readings={byTerritory("open")} />
        <TerritoryColumn territory="contested" readings={byTerritory("contested")} />
        <TerritoryColumn territory="table_stakes" readings={byTerritory("table_stakes")} />
        <TerritoryColumn territory="exposed" readings={byTerritory("exposed")} />
      </div>

      {positioning.crowd_words.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">The category&rsquo;s own words</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <p className="text-sm text-muted-foreground">
              Two or more competitors spend these. A sentence built only out of them says nothing
              about your company — and every draft is now checked against this list before anyone
              reads it.
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

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-base">What the strategist is told</CardTitle>
          <button
            type="button"
            onClick={() => setShowBrief((value) => !value)}
            className="text-xs text-muted-foreground hover:text-foreground"
          >
            {showBrief ? "Hide" : "Show"}
          </button>
        </CardHeader>
        {showBrief && (
          <CardContent>
            {/* Shown verbatim rather than paraphrased: the point of this page
                is that you can read what the machine was actually given, and a
                second wording of it is a second thing to keep in sync. */}
            <pre className="max-h-96 overflow-auto rounded-md bg-muted/40 p-3 text-xs whitespace-pre-wrap text-muted-foreground">
              {positioning.brief_for_strategy}
            </pre>
          </CardContent>
        )}
      </Card>
    </div>
  );
}
