"use client";

import { useState } from "react";
import { toast } from "sonner";

import { Search, ChevronDown } from "lucide-react";
import { BrandDisclosure, BrandSectionHeader } from "../../brand-ui";
import { ExpandableText } from "@/components/expandable-text";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { api } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import type { Rival, RivalKind, RivalProfile } from "@/lib/types";

/** How the reader meets each kind of competitor.
 *
 * `status_quo` is the one that matters and the one a category list never
 * contains: what they do instead of buying anything. It wins most deals in
 * most markets. */
const KIND: Record<RivalKind, { label: string; hint: string }> = {
  alternative: { label: "Alternative", hint: "solves the same problem for the same buyer" },
  incumbent: { label: "Incumbent", hint: "what they already pay for and would have to justify" },
  status_quo: { label: "What they do instead", hint: "a spreadsheet, a script, doing without" },
};

function ProfileDetail({ profile }: { profile: RivalProfile }) {
  if (!profile.verified) {
    return (
      <p className="text-xs text-muted-foreground">
        {profile.note || "Their site has not been read yet."}
      </p>
    );
  }
  return (
    <div className="space-y-2 text-xs">
      {profile.promise && (
        <p>
          <span className="text-muted-foreground">They promise: </span>
          {profile.promise}
        </p>
      )}
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-muted-foreground">
        {profile.pricing && <span>Pricing: {profile.pricing}</span>}
        {profile.free_entry && <span>Way in: {profile.free_entry}</span>}
        {profile.icp && <span>For: {profile.icp}</span>}
      </div>
      {profile.proof_shown.length > 0 && (
        <p className="text-amber-300">
          Shows proof: {profile.proof_shown.map((claim) => claim.text).join("; ")}
        </p>
      )}
      {profile.claims.length > 0 && (
        <ul className="space-y-0.5 text-muted-foreground">
          {profile.claims.map((claim) => (
            <li key={claim.text}>
              <span className="text-foreground/60">[{claim.axis}]</span> {claim.text}
              {claim.specific ? "" : " (no figure)"}
            </li>
          ))}
        </ul>
      )}
      <p className="text-muted-foreground/70">
        {profile.pages_read} page{profile.pages_read === 1 ? "" : "s"} read
        {profile.unverified_claims > 0 &&
          ` · ${profile.unverified_claims} claim${
            profile.unverified_claims === 1 ? "" : "s"
          } discarded as not really on their pages`}
      </p>
    </div>
  );
}

function RivalRow({
  brandId,
  rival,
  profile,
  onChanged,
}: {
  brandId: string;
  rival: Rival;
  profile: RivalProfile | undefined;
  onChanged: (rival: Rival | null) => void;
}) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);

  async function toggleMute() {
    setBusy(true);
    try {
      onChanged(await api.muteRival(brandId, rival.id, !rival.muted));
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not update that competitor");
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    setBusy(true);
    try {
      await api.deleteRival(brandId, rival.id);
      onChanged(null);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not remove that competitor");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      className={cn(
        "rounded-xl border border-border bg-card p-4",
        rival.muted && "opacity-50",
      )}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <button
          type="button"
          onClick={() => setOpen((value) => !value)}
          aria-expanded={open}
          className="min-w-40 flex-1 text-left"
        >
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-medium">{rival.name}</span>
            <Badge variant="outline" className="font-normal">
              {KIND[rival.kind]?.label ?? rival.kind}
            </Badge>
            {rival.added_by === "user" ? (
              <Badge variant="secondary" className="font-normal">
                you added this
              </Badge>
            ) : (
              <Badge variant="ghost" className="font-normal">
                found by scan
              </Badge>
            )}
            {profile && !profile.verified && (
              <Badge variant="outline" className="font-normal text-amber-400">
                site not read
              </Badge>
            )}
          </div>
          <span className="mt-2 inline-flex items-center gap-1.5 text-xs text-violet-300">{open ? "Hide competitor details" : "View competitor details"}<ChevronDown className={cn("size-3.5", open && "rotate-180")} /></span>
        </button>
        {rival.why && <div className="order-3 w-full"><ExpandableText text={rival.why} className="text-xs text-muted-foreground" limit={180} /></div>}

        <div className="order-last flex w-full shrink-0 justify-end gap-1 sm:order-none sm:w-auto">
          <Button size="sm" variant="ghost" disabled={busy} onClick={toggleMute}>
            {rival.muted ? "Include" : "Not a rival"}
          </Button>
          <Button size="sm" variant="ghost" disabled={busy} onClick={remove}>
            Remove
          </Button>
        </div>
      </div>
      {open && (
        <div className="mt-3 border-t border-border/50 pt-3">
          {profile ? (
            <ProfileDetail profile={profile} />
          ) : (
            <p className="text-xs text-muted-foreground">
              Not in the last scan. Run one to read their pages.
            </p>
          )}
          {rival.url && (
            <a
              href={rival.url}
              target="_blank"
              rel="noreferrer noopener"
              className="mt-2 inline-block text-xs text-muted-foreground underline underline-offset-2 hover:text-foreground"
            >
              {rival.url}
            </a>
          )}
        </div>
      )}
    </div>
  );
}

export function RivalsPanel({
  brandId,
  rivals,
  profiles,
}: {
  brandId: string;
  rivals: Rival[];
  profiles: RivalProfile[];
}) {
  const [rows, setRows] = useState(rivals);
  const [query, setQuery] = useState("");
  const [showMuted, setShowMuted] = useState(false);
  const visible = rows.filter((row) => (showMuted || !row.muted) && `${row.name} ${row.url} ${row.why}`.toLowerCase().includes(query.trim().toLowerCase()));
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [kind, setKind] = useState<RivalKind>("alternative");
  const [adding, setAdding] = useState(false);

  const byName = new Map(profiles.map((profile) => [profile.name.toLowerCase(), profile]));

  async function add(event: React.FormEvent) {
    event.preventDefault();
    if (!name.trim()) return;
    setAdding(true);
    try {
      const rival = await api.addRival(brandId, { name: name.trim(), url: url.trim(), kind });
      setRows((current) =>
        current.some((row) => row.id === rival.id) ? current : [...current, rival],
      );
      setName("");
      setUrl("");
      toast.success(`${rival.name} added. Run a scan to read their pages.`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not add that competitor");
    } finally {
      setAdding(false);
    }
  }

  return (
    <div className="space-y-4">
      <BrandSectionHeader title="Competitors" description="Curate the alternatives your buyers compare. Your decisions are kept through every scan." />
      <BrandDisclosure title="Add a competitor" description="Know an alternative we missed? Add it to your research list.">
          <form onSubmit={add} className="flex flex-wrap items-end gap-3">
            <div className="min-w-40 flex-1 space-y-1.5">
              <Label htmlFor="rival-name">Name</Label>
              <Input
                id="rival-name"
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="Portkey"
              />
            </div>
            <div className="min-w-48 flex-1 space-y-1.5">
              <Label htmlFor="rival-url">Website</Label>
              <Input
                id="rival-url"
                value={url}
                onChange={(event) => setUrl(event.target.value)}
                placeholder="portkey.ai"
              />
            </div>
            <div className="w-56 space-y-1.5">
              <Label htmlFor="rival-kind">How the buyer meets them</Label>
              <Select value={kind} onValueChange={(value) => setKind(value as RivalKind)}>
                <SelectTrigger id="rival-kind">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {(Object.keys(KIND) as RivalKind[]).map((option) => (
                    <SelectItem key={option} value={option}>
                      {KIND[option].label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Button type="submit" disabled={adding || !name.trim()}>
              Add
            </Button>
          </form>
          <p className="mt-2 text-xs text-muted-foreground">{KIND[kind].hint}</p>
      </BrandDisclosure>
      <div className="flex flex-wrap items-center gap-3 rounded-xl border border-border bg-card p-3">
        <div className="relative min-w-48 flex-1"><Search className="absolute left-3 top-2.5 size-4 text-muted-foreground" /><Input aria-label="Search competitors" placeholder="Search competitors…" value={query} onChange={(event) => setQuery(event.target.value)} className="pl-9" /></div>
        <Button variant={showMuted ? "secondary" : "outline"} size="sm" aria-pressed={showMuted} onClick={() => setShowMuted(!showMuted)}>Include muted</Button>
        <span role="status" className="text-xs text-muted-foreground">{visible.length} of {rows.length}</span>
      </div>
      {rows.length > 0 && visible.length === 0 && <div className="rounded-xl border border-dashed p-6 text-center text-sm text-muted-foreground">No matching competitors. Try another search or include muted entries.</div>}
      {rows.length === 0 ? (
        <Card>
          <CardContent className="p-6 text-sm text-muted-foreground">
            Nobody on the list yet. Run a scan to find who your buyer is really deciding between,
            or add the ones you already know.
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-2">
          {visible.map((rival) => (
            <RivalRow
              key={rival.id}
              brandId={brandId}
              rival={rival}
              profile={byName.get(rival.name.toLowerCase())}
              onChanged={(updated) =>
                setRows((current) =>
                  updated === null
                    ? current.filter((row) => row.id !== rival.id)
                    : current.map((row) => (row.id === rival.id ? updated : row)),
                )
              }
            />
          ))}
        </div>
      )}
    </div>
  );
}
