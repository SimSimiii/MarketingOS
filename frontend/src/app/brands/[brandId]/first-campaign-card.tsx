"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api-client";
import { refreshPage } from "@/lib/page-data";
import { problemText, progressText } from "@/lib/product-progress";
import type { MarketJob } from "@/lib/types";

export function FirstCampaignCard({ brandId, initialJob }: { brandId: string; initialJob: MarketJob | null }) {
  const [job, setJob] = useState(initialJob);
  const [objective, setObjective] = useState("Introduce our product to a new buyer with one clear next step.");
  const [starting, setStarting] = useState(false);
  const [connectionLost, setConnectionLost] = useState(false);
  const running = job?.state === "running";
  const audienceLink = `/brands/${brandId}/market?tab=audience${job?.audience ? `&audience=${encodeURIComponent(job.audience)}` : ""}`;
  const quotaLimited = /(?:rate limit|session limit)/i.test(job?.error ?? "");
  const quotaReset = job?.error.match(/\bresets\s+(\d{1,2}:\d{2}\s*(?:am|pm)?(?:\s*\([\w/-]+\))?)/i)?.[1].trim();
  const statusText = quotaLimited
    ? `The model subscription reached its limit. ${quotaReset ? `Try again after ${quotaReset}.` : "Try again after the quota resets."} Saved preparation can be reused.`
    : job?.error ? problemText(job.error) : progressText(job?.summary || job?.message);

  useEffect(() => {
    if (!running) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    async function check() {
      try {
        const next = await api.getMarketJob(brandId);
        if (cancelled) return;
        setConnectionLost(false);
        if (next?.kind !== "first_campaign") {
          setJob(null);
          return;
        }
        setJob(next);
        if (next.state !== "running") {
          refreshPage();
          return;
        }
      } catch {
        if (cancelled) return;
        setConnectionLost(true);
      }
      timer = setTimeout(check, 5000);
    }
    timer = setTimeout(check, 2000);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [brandId, running]);

  async function prepare(event: React.FormEvent) {
    event.preventDefault();
    if (starting || running || objective.trim().length < 10) return;
    setStarting(true);
    try {
      setJob(await api.prepareFirstCampaign(brandId, objective.trim()));
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not start preparation.");
    } finally {
      setStarting(false);
    }
  }

  return (
    <Card>
      <CardHeader><CardTitle>Prepare a first campaign</CardTitle></CardHeader>
      <CardContent className="space-y-4 text-sm">
        {job && (
          <div role="status" className="space-y-2">
            <p className="font-medium">{job.campaign_id ? "Recommended first campaign" : running ? "Preparing in the background" : job.state === "failed" ? "Preparation stopped" : "No email prepared for this objective"}</p>
            {job.audience && <p>{job.audience}</p>}
            <p className="text-muted-foreground">{statusText}</p>
            {connectionLost && <p className="text-muted-foreground">Reconnecting to the preparation status…</p>}
            {running && <p className="text-muted-foreground">You can leave this page and return for the result.</p>}
          </div>
        )}
        {job?.campaign_id ? (
          <div className="flex flex-wrap gap-2">
            <Link href={`/campaigns/${job.campaign_id}`} className={buttonVariants({ size: "sm" })}>Review and generate email</Link>
            <Link href={audienceLink} className={buttonVariants({ size: "sm", variant: "outline" })}>Check the sources</Link>
          </div>
        ) : !running && (
          <form onSubmit={prepare} className="space-y-3">
            <p className="text-muted-foreground">
              {job ? "Your sources and research are saved. Describe the specific use you want to introduce, or review the audience evidence."
                : "We read your sources, compare a few audiences and check the evidence for the strongest one. You can review the recommendation before generating one email."}
            </p>
            <Label htmlFor="first-campaign-objective">What should the email accomplish?</Label>
            <Textarea
              id="first-campaign-objective"
              value={objective}
              onChange={(event) => setObjective(event.target.value)}
              minLength={10}
              maxLength={2000}
              required
            />
            <div className="flex flex-wrap gap-2">
              <Button type="submit" disabled={starting || objective.trim().length < 10}>
                {starting ? "Starting…" : job ? "Continue preparation" : "Prepare campaign"}
              </Button>
              {job && (
                <Link href={audienceLink} className={buttonVariants({ variant: "outline" })}>
                  Review audiences
                </Link>
              )}
            </div>
          </form>
        )}
      </CardContent>
    </Card>
  );
}
