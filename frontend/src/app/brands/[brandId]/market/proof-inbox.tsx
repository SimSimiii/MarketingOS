"use client";

import { useState } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api, nullIfMissing } from "@/lib/api-client";
import { refreshPage, usePageData } from "@/lib/page-data";
import { rankForArgument } from "@/lib/proof-relevance";
import type { ProofCandidate } from "@/lib/types";

const sourceChecks: Record<string, { label: string; detail: string }> = {
  quote_verified: {
    label: "Quote found on page",
    detail: "The quotation matches fetched page text. Check the attribution, conditions and meaning before approving.",
  },
  page_unavailable: {
    label: "Page could not be checked",
    detail: "Open the source and confirm the exact quotation yourself. A search excerpt is not a verified quotation.",
  },
  quote_not_found: {
    label: "Quotation not found",
    detail: "The fetched page did not contain this quotation. Approve only if you can confirm the exact words in the source.",
  },
  not_checked: {
    label: "Source review needed",
    detail: "This older candidate has no automatic source check. Open the page and verify its quotation and context.",
  },
};

/** The approval queue.
 *
 * Deliberately a human decision and deliberately not optimised away. A claim
 * about this company, sourced from a page this company does not control, is
 * the one kind of fact where being wrong is not a quality problem — it is the
 * user's name under somebody else's sentence. The person whose company it is
 * takes ten seconds to know whether a quotation is real.
 *
 * So the card is built around making that ten seconds possible: the exact
 * sentence, who said it, where it lives, and the reason it might not be what
 * it looks like. */
function ProofCard({
  brandId,
  candidate,
  onDecided,
}: {
  brandId: string;
  candidate: ProofCandidate;
  onDecided: (decided: ProofCandidate) => void;
}) {
  const [deciding, setDeciding] = useState(false);
  const sourceCheck = sourceChecks[candidate.verification_status] || sourceChecks.not_checked;

  async function decide(approved: boolean) {
    setDeciding(true);
    try {
      const updated = await api.decideProof(brandId, candidate.id, approved);
      onDecided(updated);
      toast.success(
        approved
          ? `Added as ${updated.evidence_id} — your copy may now cite it.`
          : "Rejected. It will not be offered again.",
      );
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not save that decision");
    } finally {
      setDeciding(false);
    }
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between gap-3">
        <div className="min-w-0 space-y-1">
          <CardTitle className="text-base">{candidate.claim}</CardTitle>
          <p className="text-xs text-muted-foreground">
            {candidate.attributed_to || "unattributed"}
            {candidate.venue ? ` · ${candidate.venue}` : ""}
          </p>
        </div>
        <Badge variant={candidate.verification_status === "quote_verified" ? "secondary" : "outline"}>
          {sourceCheck.label}
        </Badge>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <p className="text-xs text-muted-foreground">{sourceCheck.detail}</p>
        {/* The verbatim is the thing being approved. Approving this card
            licenses these exact words in a finished email, so it is the
            largest text on the card rather than a footnote. */}
        <blockquote className="border-l-2 border-violet-400/40 pl-3 text-foreground/90 italic">
          &ldquo;{candidate.verbatim}&rdquo;
        </blockquote>

        {candidate.context && (
          <dl className="grid gap-1 text-xs text-muted-foreground">
            {[
              ["Subject", candidate.context.subject],
              ["Source", candidate.context.source_kind],
              ["Supports", candidate.context.claim_scope],
              ["Conditions", candidate.context.conditions],
              ["Time", candidate.context.temporal_scope],
              ["Limits", candidate.context.limitations],
            ].filter(([, value]) => value && value !== "unknown").map(([label, value]) => (
              <div key={label}><dt className="inline font-medium">{label}: </dt><dd className="inline">{value.replaceAll("_", " ")}</dd></div>
            ))}
          </dl>
        )}

        {candidate.caveat && (
          <p className="rounded-md bg-amber-500/10 p-2 text-xs text-amber-300">
            Check first: {candidate.caveat}
          </p>
        )}

        <div className="flex flex-wrap items-center justify-between gap-2">
          <a
            href={candidate.url}
            target="_blank"
            rel="noreferrer noopener"
            className="text-xs text-muted-foreground underline underline-offset-2 hover:text-foreground"
          >
            Read it on the page
          </a>
          <div className="flex gap-2">
            <Button
              size="sm"
              variant="ghost"
              disabled={deciding}
              onClick={() => decide(false)}
            >
              Not us
            </Button>
            <Button size="sm" disabled={deciding} onClick={() => decide(true)}>
              I checked the source
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export function ProofInbox({
  brandId,
  candidates,
  onHunt,
  hunting,
  busy,
}: {
  brandId: string;
  candidates: ProofCandidate[];
  onHunt: () => void;
  hunting: boolean;
  busy: boolean;
}) {
  const [rows, setRows] = useState(candidates);
  const [argument, setArgument] = useState("");
  const known = usePageData(() => api.getKnowledgeBase({ brandId }).catch(nullIfMissing), [brandId]);
  const pending = rankForArgument(rows.filter((row) => row.status === "pending"), argument,
    (row) => `${row.claim} ${row.verbatim} ${row.context?.claim_scope ?? ""} ${row.context?.conditions ?? ""}`);
  const approved = rows.filter((row) => row.status === "approved");
  const entries = known.status === "ready" ? known.data?.shelves.flatMap((shelf) => shelf.entries)
    .filter((entry) => entry.citable && entry.origin === "evidence") ?? [] : [];
  const ranked = rankForArgument(entries, argument,
    (entry) => `${entry.statement} ${entry.verbatim} ${entry.context?.conditions ?? ""}`);

  function replace(updated: ProofCandidate) {
    setRows((current) =>
      current.map((row) => (row.id === updated.id ? updated : row)),
    );
    refreshPage();
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-4">
          <div>
            <CardTitle className="text-base">Proof somebody else wrote</CardTitle>
            <p className="mt-1 text-sm text-muted-foreground">
              Find public testimonials and independent mentions. Review each source before adding it to your evidence ledger.
            </p>
          </div>
          <Button size="sm" onClick={onHunt} disabled={busy}>
            {hunting ? "Searching…" : "Search the web"}
          </Button>
        </CardHeader>
        {approved.length > 0 && (
          <CardContent className="text-sm text-muted-foreground">
            {approved.length} approved and in your evidence ledger
            {approved.length > 0 && (
              <>
                {" "}
                (
                {approved
                  .map((row) => row.evidence_id)
                  .filter(Boolean)
                  .join(", ")}
                )
              </>
            )}
            . Your next campaign can cite {approved.length === 1 ? "it" : "them"} by name.
          </CardContent>
        )}
      </Card>

      <div className="space-y-2">
        <label htmlFor="proof-argument" className="text-sm font-medium">Argument you want to support</label>
        <Input id="proof-argument" value={argument} onChange={(event) => setArgument(event.target.value)}
          placeholder="e.g. custom domains for client forms" />
        <p className="text-xs text-muted-foreground">
          Sort known evidence and new candidates by matching words. Official documentation can support
          capabilities; customer outcomes keep their attribution and conditions. This is a browsing aid, not a fit assessment.
        </p>
      </div>

      <Card>
        <CardHeader><CardTitle className="text-base">Already in your knowledge ({entries.length})</CardTitle></CardHeader>
        <CardContent className="space-y-3 text-sm">
          {known.status === "loading" && <p className="text-muted-foreground">Loading known evidence…</p>}
          {known.status === "failed" && <p className="text-amber-300">Known evidence could not be loaded. Refresh to try again.</p>}
          {known.status === "ready" && !entries.length && <p className="text-muted-foreground">No compiled evidence yet. Add and compile product sources first.</p>}
          {ranked.length > 0 && (
            <details open={!!argument.trim()}>
              <summary className="cursor-pointer text-muted-foreground">Browse existing facts and sources</summary>
              <div className="mt-3 max-h-[36rem] space-y-4 overflow-auto">
                {ranked.map((entry) => (
                  <article key={entry.id} className="space-y-2 border-t border-white/10 pt-3">
                    <p className="font-medium">[{entry.id}] {entry.statement}</p>
                    <Badge variant="outline">{entry.kind.replaceAll("_", " ")} · compiled source</Badge>
                    <blockquote className="border-l-2 border-violet-400/40 pl-3 italic text-foreground/80">{entry.verbatim}</blockquote>
                    {entry.context && <p className="text-xs text-muted-foreground">{[
                      entry.context.subject, entry.context.claim_scope, entry.context.conditions,
                      entry.context.temporal_scope, entry.context.limitations,
                    ].filter((item) => item && item !== "unknown").join(" · ")}</p>}
                    <p className="text-xs text-muted-foreground">{entry.source.startsWith("https://") || entry.source.startsWith("http://")
                      ? <a href={entry.source} target="_blank" rel="noreferrer noopener" className="underline">Read the source</a>
                      : entry.source || "Source not recorded"}</p>
                  </article>
                ))}
              </div>
            </details>
          )}
        </CardContent>
      </Card>

      {pending.length === 0 ? (
        <Card>
          <CardContent className="p-6 text-sm text-muted-foreground">
            {rows.length === 0
              ? "No candidates yet. Search for public evidence to review. An empty search means nothing was found in the sources checked; it does not establish that nobody has written about you."
              : "Nothing left to decide."}
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {pending.map((candidate) => (
            <ProofCard
              key={candidate.id}
              brandId={brandId}
              candidate={candidate}
              onDecided={replace}
            />
          ))}
        </div>
      )}
    </div>
  );
}
