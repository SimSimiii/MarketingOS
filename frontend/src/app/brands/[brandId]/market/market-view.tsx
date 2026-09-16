"use client";

import { useCallback, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { toast } from "sonner";

import { Crosshair, Users, ShieldCheck, Radar, Swords, RefreshCw, ScanSearch } from "lucide-react";
import { BrandDisclosure, BrandSectionHeader } from "../../brand-ui";
import { ExpandableText } from "@/components/expandable-text";

import { AudiencePanel } from "./audience-panel";
import { PositioningMap } from "./positioning-map";
import { ProofInbox } from "./proof-inbox";
import { RadarFeed } from "./radar-feed";
import { RivalsPanel } from "./rivals-panel";
import { MarketJobCard } from "@/components/market-job-card";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api } from "@/lib/api-client";
import type {
  AudienceRead,
  Brand,
  MarketJob,
  MapOptions,
  MarketRead,
  ProofCandidate,
  RadarEvent,
} from "@/lib/types";

/** The same card the live board uses.
 *
 * One component rather than two renderings of one job: a user who watched a
 * scan on /live and then opened the brand should be looking at the same
 * thing, and the trace and the spend are worth as much here as there. */
function JobBanner({ job, now }: { job: MarketJob; now: number }) {
  if (job.state === "done" && !job.summary) return null;
  return <MarketJobCard job={job} now={now} />;
}

export function MarketView({
  brand,
  initialMarket,
  initialProof,
  initialRadar,
  initialAudience,
  initialJob,
}: {
  brand: Brand;
  initialMarket: MarketRead;
  initialProof: ProofCandidate[];
  initialRadar: RadarEvent[];
  initialAudience: AudienceRead;
  initialJob: MarketJob | null;
}) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [job, setJob] = useState<MarketJob | null>(initialJob);
  const [starting, setStarting] = useState(false);
  const [now, setNow] = useState(() => Date.now());

  const running = job?.state === "running";

  const [refreshing, setRefreshing] = useState(false);
  async function refreshStatus() {
    setRefreshing(true);
    try {
      setJob(await api.getMarketJob(brand.id));
      setNow(Date.now());
      router.refresh();
    } catch (error) { toast.error(error instanceof Error ? error.message : "Could not refresh status"); }
    finally { setRefreshing(false); }
  }

  const start = useCallback(
    async (kind: "scan" | "rescan" | "proof" | "audience", options?: MapOptions) => {
      setStarting(true);
      try {
        const started =
          kind === "proof"
            ? await api.startProofHunt(brand.id)
            : kind === "audience"
              ? await api.startAudienceMap(brand.id, options)
              : await api.startMarketScan(brand.id, kind === "scan");
        setJob(started);
      } catch (error) {
        toast.error(error instanceof Error ? error.message : "Could not start that");
      } finally {
        setStarting(false);
      }
    },
    [brand.id],
  );

  // Prospecting is the one job that takes an argument, so it does not fold
  // into `start` - and it is the one the user launches most often, from a
  // card rather than from the toolbar.
  const findProspects = useCallback(
    async (segment: string) => {
      setStarting(true);
      try {
        setJob(await api.startProspectSearch(brand.id, { segment }));
      } catch (error) {
        toast.error(error instanceof Error ? error.message : "Could not start that search");
      } finally {
        setStarting(false);
      }
    },
    [brand.id],
  );

  const researchAudience = useCallback(
    async (segment: string) => {
      setStarting(true);
      try {
        setJob(await api.startAudienceResearch(brand.id, segment));
      } catch (error) {
        toast.error(error instanceof Error ? error.message : "Could not start audience research");
      } finally {
        setStarting(false);
      }
    },
    [brand.id],
  );

  const buildDossier = useCallback(
    async (segment: string, rebuild: boolean) => {
      setStarting(true);
      try {
        const started = await api.startRelevanceDossier(brand.id, segment, rebuild);
        setJob(started);
        // Exact-triple reuse finishes inside the request and therefore never
        // enters the polling effect. Refresh the server data here too.
        if (started.state === "done") {
          toast.success(started.summary || "Relevance dossier is current");
          router.refresh();
        }
      } catch (error) {
        toast.error(error instanceof Error ? error.message : "Could not build that dossier");
      } finally {
        setStarting(false);
      }
    },
    [brand.id, router],
  );

  const { positioning, profiles, rivals, note } = initialMarket;
  const pendingProof = initialProof.filter((row) => row.status === "pending").length;
  const alerts = initialRadar.filter(
    (row) => row.seen_at === null && row.severity === "acts_on_copy",
  ).length;

  const sections = [
    { value: "positioning", label: "Positioning", hint: "Where you stand", icon: Crosshair, count: null },
    { value: "rivals", label: "Competitors", hint: "Who buyers compare", icon: Swords, count: rivals.length },
    { value: "audience", label: "Audiences", hint: "Who to reach", icon: Users, count: initialMarket.audience_segments },
    { value: "proof", label: "Proof", hint: "Review evidence", icon: ShieldCheck, count: pendingProof },
    { value: "radar", label: "Changes", hint: "Market updates", icon: Radar, count: alerts },
  ];
  const requestedTab = searchParams.get("tab");
  const activeTab = sections.some((section) => section.value === requestedTab) ? requestedTab! : positioning ? "positioning" : "rivals";
  function changeTab(value: unknown) {
    if (typeof value !== "string") return;
    const params = new URLSearchParams(searchParams.toString());
    params.set("tab", value);
    window.history.pushState(null, "", `?${params.toString()}`);
  }

  return (
    <div className="space-y-5">
      <BrandSectionHeader title="Market intelligence" description="Understand your buyers, track competitors and find the evidence that sets you apart." actions={
        <Button variant="outline" size="sm" disabled={refreshing} onClick={refreshStatus}><RefreshCw className={refreshing ? "size-4 animate-spin" : "size-4"} />{refreshing ? "Refreshing…" : "Refresh results"}</Button>
      } />
      <Tabs value={activeTab} onValueChange={changeTab} className="gap-5">
        <TabsList aria-label="Market sections" className="market-section-tabs grid w-full grid-cols-2 gap-2 rounded-xl border border-border bg-card p-2 sm:grid-cols-3 xl:grid-cols-5">
          {sections.map(({ icon: Icon, ...section }) => <TabsTrigger key={section.value} value={section.value} className="market-section-trigger flex min-h-16 min-w-0 flex-col items-start justify-center gap-1 rounded-lg border px-3 py-3 text-left whitespace-normal">
            <span className="flex w-full items-center gap-1.5"><Icon className="size-4" /><span className="whitespace-nowrap text-xs font-semibold sm:text-sm">{section.label}</span>{section.count !== null && section.count > 0 && <span className="ml-auto shrink-0 whitespace-nowrap rounded bg-background/50 px-1.5 text-[10px] tabular-nums">{section.count}</span>}</span>
            <span className="text-[11px] font-normal opacity-80">{section.hint}</span>
          </TabsTrigger>)}
        </TabsList>

        {job && (running || job.state === "failed") && <JobBanner job={job} now={now} />}
        {(activeTab === "positioning" || activeTab === "rivals" || activeTab === "radar") && <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border bg-card/50 p-4">
          <div><p className="text-sm font-medium">Market research</p><p className="mt-1 text-xs text-muted-foreground">{initialMarket.scanned_at ? `Last scanned ${new Date(initialMarket.scanned_at).toLocaleDateString()}` : "Start a scan to discover your competitive landscape."}</p></div>
          <div className="flex flex-wrap gap-2"><Button variant="outline" size="sm" disabled={starting || running || rivals.length === 0} onClick={() => start("rescan")} title="Re-read existing competitors without finding new ones">Update competitors</Button><Button size="sm" disabled={starting || running} onClick={() => start("scan")}><ScanSearch className="size-4" />{running && (job?.kind === "scan" || job?.kind === "rescan") ? "Scanning…" : positioning ? "New market scan" : "Scan this market"}</Button></div>
        </div>}
        <TabsContent value="positioning">
          {positioning ? (
            <div className="space-y-5"><div className="rounded-xl border border-violet-400/20 bg-violet-500/5 p-5"><h3 className="mb-2 text-sm font-semibold text-violet-300">Market snapshot</h3><ExpandableText text={positioning.summary} /></div><PositioningMap positioning={positioning} /></div>
          ) : (
            <Card>
              <CardContent className="p-6 text-sm text-muted-foreground">
                {note || "Run a scan to see where you stand."}
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="rivals">
          <RivalsPanel brandId={brand.id} rivals={rivals} profiles={profiles} />
        </TabsContent>

        <TabsContent value="audience">
          <AudiencePanel
            /* Remounted when the server data changes, so a finished search
               actually appears. The panel keeps the user's keep/dismiss
               decisions in local state, which would otherwise survive a
               `router.refresh()` and hide the rows it just fetched. */
            key={`${initialAudience.map?.mapped_at ?? "none"}:${initialAudience.prospects.length}:${initialAudience.research.map((item) => item.version).join("-")}:${initialAudience.relevance.map((item) => `${item.status}-${item.generation_version ?? 0}`).join("-")}`}
            brandId={brand.id}
            audience={initialAudience}
            onMap={(options) => start("audience", options)}
            onProspect={findProspects}
            onResearch={researchAudience}
            onDossier={buildDossier}
            busy={starting || running}
            runningKind={running ? (job?.kind ?? null) : null}
          />
        </TabsContent>

        <TabsContent value="proof">
          <ProofInbox
            brandId={brand.id}
            candidates={initialProof}
            hunting={running && job?.kind === "proof"}
            busy={starting || running}
            onHunt={() => start("proof")}
          />
        </TabsContent>

        <TabsContent value="radar">
          <RadarFeed brandId={brand.id} events={initialRadar} />
        </TabsContent>
      </Tabs>
        {job && !running && job.state !== "failed" && <BrandDisclosure title="Latest activity" description={job.summary ? "View the last result and execution details" : "View execution details"}><JobBanner job={job} now={now} /></BrandDisclosure>}
    </div>
  );
}
