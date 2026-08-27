"use client";

import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api } from "@/lib/api-client";
import type { BrandKnowledge } from "@/lib/types";

const GROUNDING_LABEL: Record<string, string> = {
  grounded: "from the material",
  inferred: "inferred",
  user_stated: "the user told us",
};

function Empty({ children }: { children: React.ReactNode }) {
  return <p className="text-sm text-muted-foreground">{children}</p>;
}

function Scroll({ children }: { children: React.ReactNode }) {
  return <div className="max-h-[55vh] space-y-3 overflow-y-auto pr-1">{children}</div>;
}

export function BrandKnowledgeDialog({
  brandId,
  brandName,
}: {
  brandId: string;
  /** Only for the dialog title. Omitted where the page already names the
   * brand in its header, which is every page inside a brand's workspace. */
  brandName?: string;
}) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [knowledge, setKnowledge] = useState<BrandKnowledge | null>(null);
  const [error, setError] = useState<string | null>(null);

  function handleOpenChange(next: boolean) {
    setOpen(next);
    if (next && !knowledge && !loading) {
      setLoading(true);
      setError(null);
      api
        .getBrandKnowledge(brandId)
        .then(setKnowledge)
        .catch((err) => setError(err instanceof Error ? err.message : "Failed to load"))
        .finally(() => setLoading(false));
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger render={<Button variant="outline" size="sm">View facts</Button>} />
      <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>What we know about {brandName ?? "this brand"}</DialogTitle>
        </DialogHeader>

        {loading && <p className="text-sm text-muted-foreground">Loading...</p>}
        {error && <p className="text-sm text-destructive">{error}</p>}
        {!loading && !error && knowledge === null && (
          <Empty>Nothing compiled for this brand yet.</Empty>
        )}

        {knowledge && (
          <Tabs defaultValue="evidence">
            <TabsList>
              <TabsTrigger value="evidence">
                Evidence ({knowledge.artifacts.evidence.entries.length})
              </TabsTrigger>
              <TabsTrigger value="audience">
                Audience ({knowledge.artifacts.audience.segments.length})
              </TabsTrigger>
              <TabsTrigger value="business">Business</TabsTrigger>
              <TabsTrigger value="voice">Voice</TabsTrigger>
              <TabsTrigger value="gaps">Gaps ({knowledge.artifacts.gaps.gaps.length})</TabsTrigger>
            </TabsList>

            <TabsContent value="evidence" className="pt-4">
              <Scroll>
                {knowledge.artifacts.evidence.entries.length === 0 ? (
                  <Empty>No facts extracted yet.</Empty>
                ) : (
                  knowledge.artifacts.evidence.entries.map((entry) => (
                    <div key={entry.id} className="rounded-md border p-3 text-sm">
                      <div className="mb-1 flex flex-wrap items-center gap-2">
                        <Badge variant="secondary">{entry.id}</Badge>
                        <Badge variant="outline">{entry.kind}</Badge>
                        <Badge variant="outline">{entry.strength}</Badge>
                        {entry.user_attested && <Badge variant="outline">from you</Badge>}
                      </div>
                      <p className="font-medium">{entry.claim}</p>
                      {entry.verbatim && (
                        <p className="mt-1 text-muted-foreground">
                          &ldquo;{entry.verbatim}&rdquo;
                          {entry.source && ` — ${entry.source}`}
                        </p>
                      )}
                    </div>
                  ))
                )}
              </Scroll>
            </TabsContent>

            <TabsContent value="audience" className="pt-4">
              <Scroll>
                {knowledge.artifacts.audience.segments.length === 0 ? (
                  <Empty>No audience segments established yet.</Empty>
                ) : (
                  knowledge.artifacts.audience.segments.map((segment) => (
                    <div key={segment.name} className="rounded-md border p-3 text-sm">
                      <p className="font-medium">{segment.name}</p>
                      <p className="mt-1 text-muted-foreground">{segment.situation}</p>
                      <p className="mt-1">
                        <span className="text-muted-foreground">Trying to: </span>
                        {segment.job_to_be_done || "unspecified"}
                      </p>
                      <p>
                        <span className="text-muted-foreground">Trigger: </span>
                        {segment.trigger || "unspecified"}
                      </p>
                      <Badge variant="outline" className="mt-2">
                        {segment.sophistication.replace("_", " ")}
                      </Badge>
                    </div>
                  ))
                )}
                {knowledge.artifacts.audience.objections.length > 0 && (
                  <div className="pt-2">
                    <p className="mb-2 text-sm font-medium">Why they say no</p>
                    {knowledge.artifacts.audience.objections.map((objection, i) => (
                      <div key={i} className="mb-2 rounded-md border p-3 text-sm">
                        <p className="font-medium">{objection.objection}</p>
                        <p className="mt-1 text-muted-foreground">
                          {objection.answer || "nothing in the material answers this yet"}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </Scroll>
            </TabsContent>

            <TabsContent value="business" className="pt-4">
              <Scroll>
                <div className="rounded-md border p-3 text-sm">
                  <p className="font-medium">
                    {knowledge.artifacts.business.company_name || "Not named in the material"}
                  </p>
                  <p className="mt-1 text-muted-foreground">
                    {knowledge.artifacts.business.what_it_does || "Unclear from the material"}
                  </p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {knowledge.artifacts.business.category && (
                      <Badge variant="outline">{knowledge.artifacts.business.category}</Badge>
                    )}
                    {knowledge.artifacts.business.business_model && (
                      <Badge variant="outline">{knowledge.artifacts.business.business_model}</Badge>
                    )}
                  </div>
                </div>
                {knowledge.artifacts.business.facts.map((fact, i) => (
                  <div key={i} className="rounded-md border p-3 text-sm">
                    <p>{fact.statement}</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {GROUNDING_LABEL[fact.grounding] ?? fact.grounding}
                      {fact.provenance?.quote && ` — "${fact.provenance.quote}"`}
                    </p>
                  </div>
                ))}
                {knowledge.artifacts.offer.plans.length > 0 && (
                  <div className="rounded-md border p-3 text-sm">
                    <p className="mb-1 font-medium">Plans</p>
                    {knowledge.artifacts.offer.plans.map((plan) => (
                      <p key={plan.name} className="text-muted-foreground">
                        {plan.name}: {plan.price || "price not published"}
                      </p>
                    ))}
                  </div>
                )}
              </Scroll>
            </TabsContent>

            <TabsContent value="voice" className="pt-4">
              <Scroll>
                <div className="rounded-md border p-3 text-sm">
                  <Badge variant={knowledge.artifacts.voice.learned ? "secondary" : "outline"}>
                    {knowledge.artifacts.voice.learned
                      ? "Learned from copy this company sent"
                      : "System default - no existing copy to learn from"}
                  </Badge>
                  <p className="mt-2">
                    <span className="text-muted-foreground">Tone: </span>
                    {knowledge.artifacts.voice.tone}
                  </p>
                  <p>
                    <span className="text-muted-foreground">Rhythm: </span>
                    {knowledge.artifacts.voice.rhythm}
                  </p>
                </div>
                {knowledge.artifacts.voice.exemplars.map((passage, i) => (
                  <div key={i} className="rounded-md border p-3 text-sm italic text-muted-foreground">
                    &ldquo;{passage}&rdquo;
                  </div>
                ))}
              </Scroll>
            </TabsContent>

            <TabsContent value="gaps" className="pt-4">
              <Scroll>
                {knowledge.artifacts.gaps.gaps.length === 0 ? (
                  <Empty>Nothing material is missing.</Empty>
                ) : (
                  knowledge.artifacts.gaps.gaps.map((gap) => (
                    <div key={gap.id} className="rounded-md border p-3 text-sm">
                      <div className="mb-1 flex items-center gap-2">
                        <Badge variant={gap.severity === "blocking" ? "destructive" : "outline"}>
                          {gap.severity}
                        </Badge>
                        {gap.answer && <Badge variant="secondary">answered</Badge>}
                      </div>
                      <p className="font-medium">{gap.missing}</p>
                      <p className="mt-1 text-muted-foreground">{gap.impact}</p>
                      {gap.answer && (
                        <p className="mt-1 text-muted-foreground">You answered: {gap.answer}</p>
                      )}
                    </div>
                  ))
                )}
              </Scroll>
            </TabsContent>
          </Tabs>
        )}
      </DialogContent>
    </Dialog>
  );
}
