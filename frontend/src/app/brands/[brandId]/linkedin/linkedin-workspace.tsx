"use client";
import { useRef, useState } from "react";
import Link from "next/link";
import { toast } from "sonner";
import { Button, buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api-client";
import type {
  LinkedInCandidate,
  LinkedInCriteria,
  LinkedInCriteriaRequest,
  LinkedInRun,
  LinkedInSearchRequest,
  MappedSegment,
} from "@/lib/types";

const selectClass = "h-9 rounded-md border border-input bg-background px-3 text-sm";

//: Empty rather than absent, so the editor below can render before anything
//: has been proposed - and so a user who knows their own buyer can fill it in
//: by hand and never spend the proposal call at all.
const EMPTY_CRITERIA: LinkedInCriteria = {
  roles: [], industries: [], company_sizes: [], geographies: [],
  profile_signals: [], corroboration: [], exclusions: [], rationale: "", basis: "",
};

//: Which fields the editor shows, in the order somebody would think of them.
//: `rationale` and `basis` are not here: they are the proposal explaining
//: itself, and are shown as prose rather than as inputs.
type CriteriaList =
  | "roles" | "industries" | "company_sizes" | "geographies"
  | "profile_signals" | "corroboration" | "exclusions";

//: Which fields the search is held to, and which only strengthen a lead. The
//: split is the whole point: a condition that cannot be read off a profile
//: cannot be met by one, and asking for it anyway returns nobody.
const CRITERIA_FIELDS: { key: CriteriaList; label: string; hint: string; note?: string }[] = [
  { key: "roles", label: "Roles or job titles", hint: "Head of talent, Recruitment lead" },
  { key: "industries", label: "Industries", hint: "Recruitment agencies, staffing" },
  { key: "company_sizes", label: "Organisation size", hint: "10-50 employees" },
  { key: "geographies", label: "Geographies", hint: "France, Benelux" },
  {
    key: "profile_signals",
    label: "Visible on the profile",
    hint: "Company page names an AI assistant",
    note: "What a LinkedIn page can actually say. These decide who comes back.",
  },
  {
    key: "corroboration",
    label: "Corroboration (optional)",
    hint: "A changelog announcing the feature",
    note: "Lives off LinkedIn. Strengthens a lead, never drops one for missing it.",
  },
  { key: "exclusions", label: "Do not return", hint: "Job seekers, students" },
];

//: The fields a search can be driven by. Corroboration and exclusions cannot
//: find anybody on their own.
const SEARCHABLE: CriteriaList[] = [
  "roles", "industries", "company_sizes", "geographies", "profile_signals",
];

function asList(value: string): string[] {
  return value.split(",").map((item) => item.trim()).filter(Boolean);
}

function hasCriteria(criteria: LinkedInCriteria): boolean {
  return SEARCHABLE.some((key) => (criteria[key] ?? []).length > 0);
}

/** The criteria a finished job produced, whichever kind of job it was. */
function criteriaOf(run: LinkedInRun): LinkedInCriteria | null {
  const stored =
    run.kind === "criteria" && run.state === "completed"
      ? (run.result as Partial<LinkedInCriteria>)
      : run.result.criteria;
  if (!stored) return null;
  //: A proposal saved before the split carries `signals`, which the search was
  //: held to as conditions. They were meant as profile criteria, so that is
  //: where they land - the ones that need a repo or a changelog to confirm can
  //: be moved down a field.
  const { signals, ...rest } = stored;
  return {
    ...EMPTY_CRITERIA,
    ...rest,
    profile_signals: rest.profile_signals ?? signals ?? [],
  };
}

export function LinkedInWorkspace({
  brandId,
  initialRuns,
  segments,
}: {
  brandId: string;
  initialRuns: LinkedInRun[];
  segments: MappedSegment[];
}) {
  const [runs, setRuns] = useState(initialRuns);
  const [ask, setAsk] = useState<LinkedInCriteriaRequest>({ segment_name: "", hint: "", target: "people" });
  //: The last criteria this brand produced, so a reload does not lose a
  //: proposal that has already been paid for.
  const [criteria, setCriteria] = useState<LinkedInCriteria>(
    () => initialRuns.map(criteriaOf).find((item) => item !== null) ?? EMPTY_CRITERIA,
  );
  const [query, setQuery] = useState("");
  const [limit, setLimit] = useState(5);
  const [pending, setPending] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const criteriaRef = useRef<HTMLDivElement>(null);
  const running = runs.some((run) => run.state === "running");
  const busy = pending || refreshing || running;
  const ready = hasCriteria(criteria) || query.trim().length >= 3;

  async function refresh() {
    setRefreshing(true);
    try {
      const latest = await api.listLinkedInRuns(brandId);
      setRuns(latest);
      setError("");
      //: A proposal the user has not touched is replaced by the one that just
      //: finished; anything they edited is theirs and is left alone.
      const proposed = latest.find((run) => run.kind === "criteria" && run.state === "completed");
      if (proposed && !hasCriteria(criteria)) setCriteria(criteriaOf(proposed) ?? EMPTY_CRITERIA);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Refresh failed. Previous results are still shown.");
    } finally {
      setRefreshing(false);
    }
  }

  async function propose() {
    setPending(true);
    setError("");
    try {
      const run = await api.proposeLinkedInCriteria(brandId, ask);
      setRuns((previous) => [run, ...previous]);
      toast.success("Working out who to look for. Use Refresh to see the proposal.");
      criteriaRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start");
    } finally {
      setPending(false);
    }
  }

  async function search() {
    setPending(true);
    setError("");
    try {
      const payload: LinkedInSearchRequest = {
        query: query.trim(),
        criteria: hasCriteria(criteria) ? criteria : null,
        target: ask.target,
        limit,
      };
      const run = await api.searchLinkedIn(brandId, payload);
      setRuns((previous) => [run, ...previous]);
      toast.success("Searching. Use Refresh to see the saved result.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start");
    } finally {
      setPending(false);
    }
  }

  return <div className="space-y-6">
    <div className="flex flex-wrap items-center gap-3">
      <Button variant="outline" disabled={refreshing || pending} onClick={refresh}>{refreshing ? "Refreshing..." : "Refresh"}</Button>
      <p className="text-sm text-muted-foreground">Saved results · manual refresh · no automatic sending</p>
    </div>
    {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
    {running && <p role="status" className="text-sm text-violet-300">A job is running. You can leave this page and refresh later.</p>}

    <div className="grid gap-6 lg:grid-cols-2">
      <Card><CardHeader><CardTitle>1. Who is worth looking for</CardTitle></CardHeader><CardContent>
        <form className="space-y-4" onSubmit={(event) => { event.preventDefault(); void propose(); }}>
          <p className="text-sm text-muted-foreground">
            You do not have to describe your buyer: this brand&rsquo;s compiled knowledge already
            does, and its audience map does it better. Propose the criteria, correct them, then
            search.
          </p>
          <div className="flex flex-wrap gap-4">
            <div className="space-y-2">
              <Label htmlFor="linkedin-segment">Audience</Label>
              <select id="linkedin-segment" className={selectClass} value={ask.segment_name}
                onChange={(e) => setAsk({ ...ask, segment_name: e.target.value })}>
                <option value="">Whoever your own material describes</option>
                {segments.map((segment) => <option key={segment.name} value={segment.name}>{segment.name}</option>)}
              </select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="linkedin-target">Search type</Label>
              <select id="linkedin-target" className={selectClass} value={ask.target}
                onChange={(e) => setAsk({ ...ask, target: e.target.value as LinkedInCriteriaRequest["target"] })}>
                <option value="people">People / profiles</option><option value="companies">Companies / accounts</option>
              </select>
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="linkedin-hint">Anything the material does not say (optional)</Label>
            <Textarea id="linkedin-hint" maxLength={2000} value={ask.hint}
              onChange={(e) => setAsk({ ...ask, hint: e.target.value })}
              placeholder="We only sell in France, and never to agencies under five people." />
          </div>
          <p className="text-xs text-muted-foreground">
            {segments.length === 0
              ? "Nobody has mapped this brand's audience yet - the proposal will be read out of the knowledge base. Market → Audience finds the buyers your own site does not name."
              : "One call against your own material. No web access at this step."}
          </p>
          <Button type="submit" disabled={busy}>Propose criteria</Button>
        </form>
      </CardContent></Card>

      <Card ref={criteriaRef}><CardHeader><CardTitle>2. Search LinkedIn</CardTitle></CardHeader><CardContent>
        <form className="space-y-4" onSubmit={(event) => { event.preventDefault(); void search(); }}>
          <div className="grid gap-3 sm:grid-cols-2">
            {CRITERIA_FIELDS.map(({ key, label, hint, note }) => (
              <div key={key} className="space-y-1.5">
                <Label htmlFor={`criteria-${key}`}>{label}</Label>
                <Input id={`criteria-${key}`} placeholder={hint} value={(criteria[key] ?? []).join(", ")}
                  onChange={(e) => setCriteria({ ...criteria, [key]: asList(e.target.value) })} />
                {note && <p className="text-xs text-muted-foreground">{note}</p>}
              </div>
            ))}
          </div>
          {criteria.rationale && (
            <p className="text-xs text-muted-foreground">
              Proposed from {criteria.basis || "your material"}: {criteria.rationale}
            </p>
          )}
          <div className="space-y-2">
            <Label htmlFor="linkedin-query">Extra words for this search (optional)</Label>
            <Input id="linkedin-query" maxLength={2000} value={query} onChange={(e) => setQuery(e.target.value)}
              placeholder="Hiring right now" />
          </div>
          <div className="space-y-2">
            <Label htmlFor="linkedin-limit">Maximum results</Label>
            <Input id="linkedin-limit" type="number" min={1} max={10} required className="w-24"
              value={limit} onChange={(e) => setLimit(Number(e.target.value))} />
          </div>
          <p className="text-xs text-muted-foreground">
            {ready
              ? "One research call, at most three web searches inside it. A web search reads whole pages: this is the most expensive call in the product and can run to several hundred thousand tokens. Public results may be incomplete or outdated."
              : "Propose criteria above, fill one field in by hand, or type what to look for - a search needs something to look for."}
          </p>
          <Button type="submit" disabled={busy || !ready}>Search LinkedIn</Button>
        </form>
      </CardContent></Card>
    </div>

    <h2 className="text-lg font-medium">Searches and proposals</h2>
    {runs.length === 0 && <p className="text-sm text-muted-foreground">No LinkedIn work yet. Propose criteria, or type who you are looking for.</p>}
    {runs.map((run) => <RunCard key={run.id} run={run} brandId={brandId} onReuse={setCriteria} />)}
  </div>;
}

function RunCard({
  run,
  brandId,
  onReuse,
}: {
  run: LinkedInRun;
  brandId: string;
  onReuse: (criteria: LinkedInCriteria) => void;
}) {
  const criteria = criteriaOf(run);
  const title = run.kind === "criteria"
    ? `Criteria${run.request.segment_name ? ` for ${run.request.segment_name}` : ""}`
    : run.kind === "search"
      ? run.request.query || "Search on the proposed criteria"
      : `Message to ${run.request.recipient_name}`;
  return <Card><CardHeader><CardTitle className="text-base">{title}</CardTitle>
    <p className="text-xs text-muted-foreground">{run.state} · {new Date(run.created_at).toLocaleString()} · {run.calls} model calls · {run.input_tokens + run.output_tokens} tokens</p>
  </CardHeader><CardContent className="space-y-4">
    {run.error && <p role="alert" className="text-sm text-destructive">{run.error}</p>}
    {run.state === "running" && <p className="text-sm text-muted-foreground">In progress at last refresh.</p>}
    {run.result.note && <p className="text-sm text-muted-foreground">{run.result.note}</p>}

    {criteria && (
      <div className="space-y-2 rounded-lg border border-border p-4">
        {CRITERIA_FIELDS.filter(({ key }) => (criteria[key] ?? []).length > 0).map(({ key, label }) => (
          <p key={key} className="text-sm"><span className="text-muted-foreground">{label}:</span> {(criteria[key] ?? []).join(", ")}</p>
        ))}
        {criteria.rationale && <p className="text-xs text-muted-foreground">{criteria.rationale}</p>}
        {run.kind === "criteria" && run.state === "completed" && (
          <Button size="sm" variant="outline" onClick={() => onReuse(criteria)}>Use these criteria</Button>
        )}
      </div>
    )}

    {run.kind === "search" && run.state === "completed" && !run.result.candidates?.length && (
      <div className="space-y-1">
        <p>No public candidates came back.</p>
        {/* Naming the knob that is usually the wrong one: a search asked to
            confirm something a profile does not carry rejects every real
            prospect and reports it as an empty market. */}
        <p className="text-sm text-muted-foreground">
          Check Visible on the profile first - anything there that needs a repository, a
          changelog or a forum post to confirm belongs under Corroboration, where it
          strengthens a lead instead of excluding one. After that, widen the roles or drop
          the geography.
        </p>
      </div>
    )}

    {run.result.candidates?.map((candidate) => (
      <CandidateCard key={candidate.url} candidate={candidate} brandId={brandId} />
    ))}

    {run.result.body && <>
      <p className="whitespace-pre-wrap rounded-lg border border-border p-4 text-sm">{run.result.body}</p>
      <p className="text-xs text-muted-foreground">{run.result.characters} / {run.result.limit} characters</p>
    </>}
  </CardContent></Card>;
}

function CandidateCard({ candidate, brandId }: { candidate: LinkedInCandidate; brandId: string }) {
  //: Writing to somebody is a campaign, not a search result's side effect:
  //: the message is planned by the same Strategist as an email, against this
  //: brand's audience and proof. So this hands the recipient to the campaign
  //: form rather than drafting anything here.
  //:
  //: The headline travels with them. It is the one recipient-specific fact
  //: this product has actually got hold of, and dropping it here is what
  //: produced the messages this page exists to avoid: a writer handed a name,
  //: a URL and nothing else writes a description of the product with a
  //: greeting in front. It arrives in an editable box under a warning, not as
  //: a confirmed fact - the candidate's `reason` is a model's argument for
  //: why they match and deliberately does not travel.
  const draftHref = `/campaigns?linkedin_name=${encodeURIComponent(candidate.name)}`
    + `&linkedin_url=${encodeURIComponent(candidate.url)}&brand=${brandId}`
    + (candidate.headline
      ? `&linkedin_headline=${encodeURIComponent(candidate.headline.slice(0, 500))}`
      : "");
  return <div className="space-y-2 rounded-lg border border-border p-4">
    <a href={candidate.url} target="_blank" rel="noreferrer" className="font-medium text-violet-300 hover:underline">{candidate.name} ↗</a>
    <p className="text-sm">{candidate.headline}</p><p className="text-sm">{candidate.reason}</p>
    <p className="text-xs text-amber-300">Unverified search lead — check identity and current role.</p>
    <blockquote className="border-l-2 border-border pl-3 text-sm text-muted-foreground">{candidate.excerpt}</blockquote>
    <a href={candidate.source_url} target="_blank" rel="noreferrer" className="block text-xs text-violet-300 hover:underline">Open reported source ↗</a>
    <Link href={draftHref} className={buttonVariants({ variant: "outline", size: "sm" })}>Write to them</Link>
  </div>;
}
