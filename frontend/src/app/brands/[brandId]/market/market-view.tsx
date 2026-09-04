"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { AudiencePanel } from "./audience-panel";
import { PositioningMap } from "./positioning-map";
import { ProofInbox } from "./proof-inbox";
import { RadarFeed } from "./radar-feed";
import { RivalsPanel } from "./rivals-panel";
import { MarketJobCard } from "@/components/market-job-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api } from "@/lib/api-client";
import type {
  AudienceRead,
  Brand,
  MarketJob,
  MarketRead,
  ProofCandidate,
  RadarEvent,
} from "@/lib/types";

/** How often the page asks where a running scan got to.
 *
 * A scan is one search call plus one extraction per competitor - a couple of
 * minutes, not the fifteen a campaign takes - so it is polled rather than
 * streamed. Two seconds is fast enough that the progress line feels live and
 * slow enough that it is not a load-bearing request. */
const POLL_MS = 2_000;

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
  const [job, setJob] = useState<MarketJob | null>(initialJob);
  const [starting, setStarting] = useState(false);
  const [now, setNow] = useState(() => Date.now());

  const running = job?.state === "running";

  // Only while something is in flight: a ticking clock on a finished job is a
  // re-render a second for a number that has stopped moving.
  useEffect(() => {
    if (!running) return;
    const clock = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(clock);
  }, [running]);

  // Poll only while something is in flight, and refresh the server components
  // once when it lands - the scan wrote new rows, and everything on this page
  // is read from them.
  useEffect(() => {
    if (!running) return;
    let cancelled = false;
    const timer = setInterval(async () => {
      try {
        const next = await api.getMarketJob(brand.id);
        if (cancelled || !next) return;
        setJob(next);
        if (next.state !== "running") {
          clearInterval(timer);
          if (next.state === "done") {
            toast.success(next.summary || "Scan finished");
            router.refresh();
          }
        }
      } catch {
        // A dropped poll is not worth surfacing: the next one will land, and
        // the job is running in the background regardless of this page.
      }
    }, POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [brand.id, running, router]);

  const start = useCallback(
    async (kind: "scan" | "rescan" | "proof" | "audience") => {
      setStarting(true);
      try {
        const started =
          kind === "proof"
            ? await api.startProofHunt(brand.id)
            : kind === "audience"
              ? await api.startAudienceMap(brand.id)
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

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <p className="max-w-xl text-sm text-muted-foreground">
          The half of the argument that is not about {brand.name}: what everybody else promises,
          and which of this brand&rsquo;s claims are its alone. Every competitor, proof point and
          alert below belongs to this brand and to no other.
        </p>
        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant="outline"
            disabled={starting || running || rivals.length === 0}
            onClick={() => start("rescan")}
            title="Re-read the competitors already on your list, without searching for new ones"
          >
            Re-read the list
          </Button>
          <Button disabled={starting || running} onClick={() => start("scan")}>
            {running ? "Scanning…" : positioning ? "Scan again" : "Scan this market"}
          </Button>
        </div>
      </div>

      {job && <JobBanner job={job} now={now} />}

      {!positioning ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Nothing scanned yet</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-muted-foreground">
            <p>{note}</p>
            <p>
              Until then, every email is written blind to the field: your copy can be true,
              well-shaped and grounded in your own material, and still be the email your reader
              received from four other companies this quarter. Nothing in your own website can
              tell you which of your claims everybody else is also making.
            </p>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="flex flex-wrap items-center justify-between gap-3 p-4 text-sm">
            <span>{positioning.summary}</span>
            <span className="text-xs text-muted-foreground">
              read{" "}
              {initialMarket.scanned_at
                ? new Date(initialMarket.scanned_at).toLocaleDateString()
                : "—"}
            </span>
          </CardContent>
        </Card>
      )}

      <Tabs defaultValue={positioning ? "positioning" : "rivals"}>
        <TabsList>
          <TabsTrigger value="positioning">Positioning</TabsTrigger>
          <TabsTrigger value="rivals">
            Competitors
            {rivals.length > 0 && (
              <Badge variant="ghost" className="ml-1.5 font-normal">
                {rivals.length}
              </Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="audience">
            Audience
            {initialMarket.audience_segments > 0 && (
              <Badge variant="ghost" className="ml-1.5 font-normal">
                {initialMarket.audience_segments}
              </Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="proof">
            Proof
            {pendingProof > 0 && (
              <Badge variant="default" className="ml-1.5 font-normal">
                {pendingProof}
              </Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="radar">
            What changed
            {alerts > 0 && (
              <Badge variant="default" className="ml-1.5 font-normal">
                {alerts}
              </Badge>
            )}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="positioning">
          {positioning ? (
            <PositioningMap positioning={positioning} />
          ) : (
            <Card>
              <CardContent className="p-6 text-sm text-muted-foreground">
                Run a scan to see where you stand.
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
            onMap={() => start("audience")}
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
            onHunt={() => start("proof")}
          />
        </TabsContent>

        <TabsContent value="radar">
          <RadarFeed brandId={brand.id} events={initialRadar} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
