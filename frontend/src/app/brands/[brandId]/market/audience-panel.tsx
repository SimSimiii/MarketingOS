"use client";

import { useMemo, useState } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import type {
  AudienceRead,
  Contact,
  MappedSegment,
  Prospect,
  SegmentKind,
} from "@/lib/types";

/** What each kind of segment is, in one phrase.
 *
 * The labels carry the whole argument of this page. A user looking at eight
 * segments they already knew has learned nothing; these say, per row, which
 * ones came from somewhere their own website could not have. */
const KIND_LABELS: Record<SegmentKind, string> = {
  core: "who you already sell to",
  adjacent: "same problem, different industry",
  influencer: "feels the pain, does not sign",
  channel: "would resell you to their own clients",
  triggered: "something just happened to them",
  unintended: "using it for something you did not design",
};

const CONTACT_ICONS: Record<Contact["kind"], string> = {
  email: "✉",
  phone: "☎",
  form: "▤",
  social: "◎",
};

function percent(fit: number): string {
  return `${Math.round(fit * 100)}%`;
}

/** One mapped buyer.
 *
 * `basis` is given as much room as the rate, deliberately. The number on its
 * own is a claim the user can only over-trust or ignore; the number next to
 * the reasoning that produced it is one they can correct in ten seconds — and
 * they are the person in the room who actually knows this market. */
function SegmentCard({
  segment,
  selected,
  prospects,
  onSelect,
  onProspect,
  busy,
}: {
  segment: MappedSegment;
  selected: boolean;
  prospects: number;
  onSelect: () => void;
  onProspect: () => void;
  busy: boolean;
}) {
  return (
    <Card className={cn(selected && "ring-1 ring-primary/50")}>
      <CardHeader className="flex flex-row items-start justify-between gap-3">
        <button type="button" onClick={onSelect} className="min-w-0 space-y-1 text-left">
          <CardTitle className="text-base">{segment.name}</CardTitle>
          <p className="text-xs text-muted-foreground">
            {KIND_LABELS[segment.kind] ?? segment.kind}
            {segment.population ? ` · ${segment.population}` : ""}
          </p>
        </button>
        <div className="flex shrink-0 flex-col items-end gap-1">
          <Badge variant={segment.fit >= 0.25 ? "default" : "secondary"}>
            {percent(segment.fit)} would bite
          </Badge>
          {segment.unobvious && (
            <span className="text-[10px] uppercase tracking-wide text-muted-foreground">
              not on your site
            </span>
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-3 text-sm">
        {segment.who && <p className="text-foreground/90">{segment.who}</p>}
        {segment.why_them && (
          <p className="text-muted-foreground">Why them: {segment.why_them}</p>
        )}
        {segment.trigger && (
          <p className="text-muted-foreground">What starts them looking: {segment.trigger}</p>
        )}
        {segment.angle && (
          <p className="rounded-md bg-muted/40 p-2 text-xs">
            Open on: <span className="text-foreground">{segment.angle}</span>
          </p>
        )}
        {segment.objection && (
          <p className="text-xs text-muted-foreground">
            They say no because: {segment.objection}
          </p>
        )}
        {segment.basis && (
          <p className="text-xs text-muted-foreground">
            <span className="text-foreground/70">{percent(segment.fit)} is an estimate</span>,
            reasoned from: {segment.basis}
          </p>
        )}

        {segment.signals.length > 0 && (
          <div className="space-y-1">
            <p className="text-xs font-medium text-foreground/70">
              How you recognise one from the outside
            </p>
            <ul className="space-y-0.5 text-xs text-muted-foreground">
              {segment.signals.slice(0, 4).map((signal) => (
                <li key={signal}>— {signal}</li>
              ))}
            </ul>
          </div>
        )}
        {segment.where.length > 0 && (
          <p className="text-xs text-muted-foreground">
            Findable at: {segment.where.slice(0, 3).join(" · ")}
          </p>
        )}

        <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
          <span className="text-xs text-muted-foreground">
            {prospects > 0
              ? `${prospects} organisation${prospects === 1 ? "" : "s"} found`
              : "nobody named yet"}
          </span>
          <Button size="sm" variant="outline" disabled={busy} onClick={onProspect}>
            {busy ? "Searching…" : "Find these companies"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

/** One named organisation.
 *
 * Every address on this card was found on a page the server fetched and
 * checked back against it — an invented one never gets this far. That is what
 * makes the copy button honest, and it is why `invented_contacts` is shown
 * rather than swallowed: a row that had to discard three is a row whose other
 * claims deserve the same suspicion. */
function ProspectCard({
  brandId,
  prospect,
  onDecided,
}: {
  brandId: string;
  prospect: Prospect;
  onDecided: (updated: Prospect) => void;
}) {
  const [deciding, setDeciding] = useState(false);

  async function decide(status: "kept" | "dismissed") {
    setDeciding(true);
    try {
      onDecided(await api.decideProspect(brandId, prospect.id, status));
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not save that");
    } finally {
      setDeciding(false);
    }
  }

  return (
    <Card className={cn(prospect.status === "dismissed" && "opacity-50")}>
      <CardHeader className="flex flex-row items-start justify-between gap-3">
        <div className="min-w-0 space-y-1">
          <CardTitle className="text-base">
            <a
              href={prospect.url}
              target="_blank"
              rel="noreferrer noopener"
              className="hover:underline"
            >
              {prospect.name}
            </a>
          </CardTitle>
          <p className="text-xs text-muted-foreground">
            {prospect.what_they_do || prospect.segment}
          </p>
        </div>
        <Badge variant={prospect.fit >= 0.7 ? "secondary" : "outline"}>
          {percent(prospect.fit)} match
        </Badge>
      </CardHeader>

      <CardContent className="space-y-3 text-sm">
        {prospect.why_them && <p>{prospect.why_them}</p>}
        {prospect.verbatim && (
          <blockquote className="border-l-2 border-border pl-3 text-xs text-foreground/80 italic">
            &ldquo;{prospect.verbatim}&rdquo;
          </blockquote>
        )}

        {prospect.contacts.length > 0 ? (
          <ul className="space-y-1">
            {prospect.contacts.map((contact) => (
              <li key={`${contact.kind}-${contact.value}`} className="flex items-center gap-2">
                <span className="text-muted-foreground">{CONTACT_ICONS[contact.kind]}</span>
                <span className="font-mono text-xs">{contact.value}</span>
                {contact.label && (
                  <span className="text-xs text-muted-foreground">({contact.label})</span>
                )}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-xs text-muted-foreground">
            {prospect.verified
              ? "They publish no way to contact them anywhere we could read."
              : prospect.note || "Their site could not be read."}
          </p>
        )}

        {prospect.invented_contacts > 0 && (
          <p className="rounded-md bg-amber-500/10 p-2 text-xs text-amber-300">
            {prospect.invented_contacts} contact detail
            {prospect.invented_contacts === 1 ? " was" : "s were"} reported that could not be
            found anywhere on their site, and discarded. Weigh the rest of this row
            accordingly.
          </p>
        )}
        {prospect.caveat && (
          <p className="text-xs text-muted-foreground">Check first: {prospect.caveat}</p>
        )}

        <div className="flex flex-wrap items-center justify-between gap-2">
          <span className="text-xs text-muted-foreground">
            {prospect.status === "kept"
              ? "on your list"
              : prospect.status === "dismissed"
                ? "dismissed — it will not be offered again"
                : `read ${prospect.pages_read} page${prospect.pages_read === 1 ? "" : "s"}`}
          </span>
          <div className="flex gap-2">
            <Button
              size="sm"
              variant="ghost"
              disabled={deciding || prospect.status === "dismissed"}
              onClick={() => decide("dismissed")}
            >
              Not for us
            </Button>
            <Button
              size="sm"
              disabled={deciding || prospect.status === "kept"}
              onClick={() => decide("kept")}
            >
              Keep
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export function AudiencePanel({
  brandId,
  audience,
  onMap,
  onProspect,
  busy,
  runningKind,
}: {
  brandId: string;
  audience: AudienceRead;
  onMap: () => void;
  onProspect: (segment: string) => void;
  busy: boolean;
  runningKind: string | null;
}) {
  const [rows, setRows] = useState(audience.prospects);
  const [selected, setSelected] = useState<string | null>(null);

  const demand = audience.map;
  const bySegment = useMemo(() => {
    const counts = new Map<string, number>();
    for (const row of rows) {
      if (row.status === "dismissed") continue;
      counts.set(row.segment, (counts.get(row.segment) ?? 0) + 1);
    }
    return counts;
  }, [rows]);

  const visible = selected ? rows.filter((row) => row.segment === selected) : rows;
  // Counted over what is visible, not over everything: the export link is
  // scoped to the selected segment, and a button that says "3 kept" next to a
  // file containing one is a button that gets distrusted the first time
  // somebody opens the file.
  const kept = visible.filter((row) => row.status === "kept").length;

  function replace(updated: Prospect) {
    setRows((current) => current.map((row) => (row.id === updated.id ? updated : row)));
  }

  if (!demand) {
    return (
      <Card>
        <CardHeader className="flex flex-row items-start justify-between gap-4">
          <div>
            <CardTitle className="text-base">Nobody has mapped this yet</CardTitle>
            <p className="mt-1 max-w-2xl text-sm text-muted-foreground">{audience.note}</p>
          </div>
          <Button size="sm" onClick={onMap} disabled={busy}>
            {busy ? "Working…" : "Find the audience"}
          </Button>
        </CardHeader>
        <CardContent className="max-w-2xl space-y-2 text-sm text-muted-foreground">
          <p>
            Your website names the customer you set out to have. It is usually right and it is
            almost never complete — the buyer who converts best is routinely missing from it,
            for the same reason nobody put them there.
          </p>
          <p>
            This reads the market instead of the site: the industry one over with the same
            problem and a different vocabulary, the person who feels the pain daily but does
            not sign, the agency that would put you in front of forty clients, the company that
            only becomes a buyer the week something happens to them.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="flex flex-row items-start justify-between gap-4">
          <div className="min-w-0">
            <CardTitle className="text-base">{demand.summary}</CardTitle>
            {demand.reading && (
              <p className="mt-1 max-w-2xl text-sm text-muted-foreground">{demand.reading}</p>
            )}
          </div>
          <Button size="sm" variant="outline" onClick={onMap} disabled={busy}>
            {busy && runningKind === "audience" ? "Working…" : "Map again"}
          </Button>
        </CardHeader>
        <CardContent className="space-y-2 text-xs text-muted-foreground">
          <p>
            Every rate here is an estimate reasoned from public evidence, not a measured
            result — nothing has been sent to any of these people yet. Each one carries the
            reasoning it came from, so the parts that are wrong about your market should be
            obvious to you in seconds.
          </p>
          {demand.searched.length > 0 && (
            <p>Searched: {demand.searched.slice(0, 4).join(" · ")}</p>
          )}
          {demand.note && <p className="text-amber-300/80">{demand.note}</p>}
        </CardContent>
      </Card>

      <div className="grid gap-3 lg:grid-cols-2">
        {demand.segments.map((segment) => (
          <SegmentCard
            key={segment.name}
            segment={segment}
            selected={selected === segment.name}
            prospects={bySegment.get(segment.name) ?? 0}
            onSelect={() =>
              setSelected((current) => (current === segment.name ? null : segment.name))
            }
            onProspect={() => onProspect(segment.name)}
            busy={busy}
          />
        ))}
      </div>

      {rows.length > 0 && (
        <Card>
          <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-3">
            <div>
              <CardTitle className="text-base">
                {selected ? `Organisations for ${selected}` : "Every organisation found"}
              </CardTitle>
              <p className="mt-1 text-xs text-muted-foreground">
                Every address below was read off a page on that company&rsquo;s own site and
                checked against it. Nothing here was guessed from a domain name.
              </p>
            </div>
            <div className="flex items-center gap-2">
              {selected && (
                <Button size="sm" variant="ghost" onClick={() => setSelected(null)}>
                  Show all
                </Button>
              )}
              {/* An href rather than a fetch: the export is a file, and the
                  browser already knows how to save one. */}
              <a
                href={api.prospectsCsvUrl(brandId, selected ?? undefined)}
                className={cn(
                  "rounded-md border border-border px-3 py-1.5 text-xs",
                  kept === 0 && "pointer-events-none opacity-40",
                )}
                title={
                  kept === 0
                    ? "Keep at least one organisation first — the file only carries the rows you reviewed"
                    : "Download the rows you kept"
                }
              >
                Export {kept > 0 ? `${kept} kept` : "kept"}
              </a>
            </div>
          </CardHeader>
        </Card>
      )}

      <div className="space-y-3">
        {visible.map((prospect) => (
          <ProspectCard
            key={prospect.id}
            brandId={brandId}
            prospect={prospect}
            onDecided={replace}
          />
        ))}
      </div>
    </div>
  );
}
