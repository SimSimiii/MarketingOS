"use client";

import { useEffect, useId, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { api, ApiError } from "@/lib/api-client";
import { formatAbsolute } from "@/lib/format";
import { problemText } from "@/lib/product-progress";
import { prospectSearchRequest, type ProspectSearchFilters } from "@/lib/prospect-search";
import type { LinkedInRun, MapOptions, MappedSegment } from "@/lib/types";

const selectClass = "h-9 w-full rounded-md border border-input bg-background px-3 text-sm";
type FilterField = "roles" | "industries" | "companySizes" | "geographies" | "languages" | "signals" | "exclusions";

export function ProspectSearchDialog({
  brandId, segment, scope, busy, onClose, onQualifyCompanies,
}: {
  brandId: string;
  segment: MappedSegment;
  scope: MapOptions;
  busy: boolean;
  onClose: () => void;
  onQualifyCompanies: () => void;
}) {
  const prefix = useId();
  const [filters, setFilters] = useState<ProspectSearchFilters>({
    target: "companies", source: "web", query: segment.name,
    roles: segment.buyer_role, industries: "", companySizes: "",
    geographies: scope.geography, languages: scope.language,
    signals: "", exclusions: scope.exclusions, limit: 5,
  });
  const [runs, setRuns] = useState<LinkedInRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState(false);
  const [available, setAvailable] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    api.listLinkedInRuns(brandId).then((rows) => {
      if (active) setRuns(rows);
    }).catch((reason: unknown) => {
      if (active) {
        const unavailable = reason instanceof ApiError && reason.status === 404;
        setAvailable(!unavailable);
        setError(unavailable ? "Public prospect search is unavailable for this workspace. The company website workflow remains available below when eligible." : reason instanceof Error ? reason.message : "Could not load saved searches");
      }
    }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [brandId]);

  const running = runs.some((run) => run.state === "running");
  const searches = runs.filter((run) => run.kind === "search" && run.request.segment_name === segment.name);
  const fields: { key: FilterField; label: string; hint: string }[] = [
    ...(filters.target !== "venues" ? [{ key: "roles" as const, label: "Professional roles", hint: "Owner, head of operations" }] : []),
    { key: "industries", label: filters.target === "venues" ? "Topics or interests" : "Industries", hint: filters.target === "venues" ? "Home renovation, family travel" : "Retail, recruitment" },
    ...(filters.target !== "venues" ? [{ key: "companySizes" as const, label: "Company sizes", hint: "10–50 employees" }] : []),
    { key: "geographies", label: "Countries or regions", hint: "France, Belgium" },
    { key: "languages", label: "Audience languages", hint: "French, English" },
    { key: "signals", label: "Publicly visible criteria", hint: filters.target === "venues" ? "Public partnership page, specialist event" : "Professional directory lists repair services" },
    { key: "exclusions", label: "Exclude", hint: "Recruiters, unrelated topics" },
  ];

  async function refresh() {
    setLoading(true);
    api.invalidate();
    try {
      setRuns(await api.listLinkedInRuns(brandId));
      setAvailable(true);
      setError("");
    } catch (reason) {
      const unavailable = reason instanceof ApiError && reason.status === 404;
      setAvailable(!unavailable);
      setError(unavailable ? "Public prospect search is unavailable for this workspace. The company website workflow remains available below when eligible." : reason instanceof Error ? reason.message : "Could not refresh searches");
    } finally { setLoading(false); }
  }

  async function search() {
    setPending(true);
    setError("");
    try {
      const run = await api.searchLinkedIn(brandId, prospectSearchRequest(segment, filters));
      setRuns((current) => [run, ...current]);
      toast.success("Search saved. Refresh results when it finishes; you can close this window.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not start the search");
    } finally { setPending(false); }
  }

  return <Dialog open onOpenChange={(open) => { if (!open) onClose(); }}>
    <DialogContent className="max-h-[90dvh] overflow-y-auto sm:max-w-3xl">
      <DialogHeader>
        <DialogTitle>Find prospects</DialogTitle>
        <DialogDescription>{segment.name} · Choose who to find and where to search.</DialogDescription>
      </DialogHeader>
      <form className="space-y-4" onSubmit={(event) => { event.preventDefault(); void search(); }}>
        <fieldset disabled={pending || loading || running || busy || !available} className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor={`${prefix}-target`}>Looking for</Label>
              <select id={`${prefix}-target`} className={selectClass} value={filters.target}
                onChange={(event) => setFilters({ ...filters, target: event.target.value as ProspectSearchFilters["target"], source: event.target.value === "venues" ? "web" : filters.source })}>
                <option value="companies">Companies</option>
                <option value="people">People in a professional role</option>
                <option value="venues">Consumer audience · places to reach them</option>
              </select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor={`${prefix}-source`}>Search source</Label>
              <select id={`${prefix}-source`} className={selectClass} value={filters.source} disabled={filters.target === "venues"}
                onChange={(event) => setFilters({ ...filters, source: event.target.value as ProspectSearchFilters["source"] })}>
                <option value="web">Public web</option>
                <option value="linkedin">LinkedIn public search results</option>
              </select>
            </div>
          </div>
          <p className="text-xs text-muted-foreground">
            {filters.target === "venues"
              ? "Find public communities, publications, events and partners where this audience may be reachable. Results describe access routes and unknowns; they do not expose consumer profiles or member lists. The existing company qualification system remains organisation based."
              : filters.source === "linkedin"
                ? "Searches publicly indexed LinkedIn pages. No account connection is required. Search excerpts remain leads to review, not verified identity, need or intent."
                : "Find public company sites, professional profiles and directories. These are search leads; contact details and buying needs are not verified."}
          </p>
          <div className="space-y-1.5">
            <Label htmlFor={`${prefix}-query`}>Describe what to look for</Label>
            <Input id={`${prefix}-query`} value={filters.query} maxLength={2000}
              onChange={(event) => setFilters({ ...filters, query: event.target.value })} />
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            {fields.map(({ key, label, hint }) => <div key={key} className="space-y-1.5">
              <Label htmlFor={`${prefix}-${key}`}>{label}</Label>
              <Input id={`${prefix}-${key}`} placeholder={hint} value={filters[key]} maxLength={1000}
                onChange={(event) => setFilters({ ...filters, [key]: event.target.value })} />
            </div>)}
          </div>
          <p className="text-xs text-muted-foreground">Separate multiple values with commas. Leave filters empty to keep the search open. Company research signals strengthen a lead when found; missing corroboration does not exclude it.</p>
          <div className="flex flex-wrap items-end gap-3">
            <div className="space-y-1.5">
              <Label htmlFor={`${prefix}-limit`}>Maximum results</Label>
              <Input id={`${prefix}-limit`} type="number" min={1} max={10} required className="w-24" value={filters.limit}
                onChange={(event) => setFilters({ ...filters, limit: Number(event.target.value) })} />
            </div>
            <Button type="submit">{pending ? "Starting…" : "Start public search"}</Button>
          </div>
        </fieldset>
        <p className="text-xs text-muted-foreground">One research step, up to ten results. Each attempt asks for at most three web searches; response corrections or transport retries may add calls. No targeting proposal or message is generated automatically.</p>
      </form>
      {error && <p role="alert" className="text-sm text-destructive">{problemText(error)}</p>}
      <div className="space-y-3 border-t border-border pt-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="font-medium">Saved searches for this audience</h3>
          <Button size="sm" variant="outline" disabled={loading || pending} onClick={refresh}>{loading ? "Refreshing…" : "Refresh results"}</Button>
        </div>
        {running && <p role="status" className="text-sm text-violet-300">A prospecting job is running for this brand. Refresh to see its result.</p>}
        {!loading && searches.length === 0 && <p className="text-sm text-muted-foreground">No saved prospect search for this audience yet.</p>}
        {searches.map((run, index) => <details key={run.id} open={index === 0} className="space-y-3 rounded-lg border border-border p-3">
          <summary className="cursor-pointer text-sm font-medium">{run.request.target === "venues" ? "Reach channels" : run.request.target === "people" ? "Professional people" : "Companies"} · {run.request.source === "web" ? "Web" : "LinkedIn"} · {run.state} · {formatAbsolute(run.created_at)}</summary>
          <details className="text-xs text-muted-foreground">
            <summary className="cursor-pointer">Search criteria used</summary>
            <p className="mt-2">Query: {run.request.query || "Criteria only"}</p>
            {run.request.criteria && Object.entries(run.request.criteria).filter(([, value]) => Array.isArray(value) && value.length > 0).map(([key, value]) => <p key={key}>{key.replaceAll("_", " ")}: {(value as string[]).join(", ")}</p>)}
          </details>
          {run.error && <p role="alert" className="text-sm text-destructive">{problemText(run.error)}</p>}
          {run.result.note && <p className="text-sm text-muted-foreground">{run.result.note}</p>}
          {run.state === "completed" && !run.result.candidates?.length && <p className="text-sm text-muted-foreground">No public matches were returned. Review the filters and search coverage; this does not establish that the audience is absent.</p>}
          {run.result.candidates?.map((candidate) => <div key={candidate.url} className="space-y-1 rounded-lg bg-black/20 p-3 text-sm">
            <a href={candidate.url} target="_blank" rel="noreferrer noopener" className="font-medium text-violet-300 hover:underline">{candidate.name} ↗</a>
            <p>{candidate.headline}</p><p>{candidate.reason}</p>
            <p className="text-xs text-amber-300">Unverified {run.request.target === "venues" ? "reach channel · check audience and access rules" : "search lead · review identity and current activity"}</p>
            <blockquote className="border-l-2 border-border pl-2 text-muted-foreground">{candidate.excerpt}</blockquote>
            <a href={candidate.source_url} target="_blank" rel="noreferrer noopener" className="text-xs text-violet-300 hover:underline">Search-reported source ↗</a>
          </div>)}
        </details>)}
      </div>
      {filters.target === "companies" && <details className="border-t border-border pt-3 text-sm">
        <summary className="cursor-pointer font-medium">Need company qualification and published contacts?</summary>
        <p className="my-2 text-xs text-muted-foreground">The existing company workflow reads official websites and checks the saved audience definition. It uses that definition and its scope, independently of the public search filters above. It can use one discovery call plus one call per company; results appear under Organisations.</p>
        <Button size="sm" variant="outline" disabled={busy || !segment.researchable || pending || running || loading} onClick={() => { onClose(); onQualifyCompanies(); }}>Find and qualify companies</Button>
      </details>}
    </DialogContent>
  </Dialog>;
}
