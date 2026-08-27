"use client";

import { useState } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api-client";
import type { ProofCandidate } from "@/lib/types";

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
        <Badge variant={candidate.confidence >= 0.7 ? "secondary" : "outline"}>
          {Math.round(candidate.confidence * 100)}% sure
        </Badge>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        {/* The verbatim is the thing being approved. Approving this card
            licenses these exact words in a finished email, so it is the
            largest text on the card rather than a footnote. */}
        <blockquote className="border-l-2 border-border pl-3 text-foreground/90 italic">
          &ldquo;{candidate.verbatim}&rdquo;
        </blockquote>

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
              This is real
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
}: {
  brandId: string;
  candidates: ProofCandidate[];
  onHunt: () => void;
  hunting: boolean;
}) {
  const [rows, setRows] = useState(candidates);
  const pending = rows.filter((row) => row.status === "pending");
  const approved = rows.filter((row) => row.status === "approved");

  function replace(updated: ProofCandidate) {
    setRows((current) =>
      current.map((row) => (row.id === updated.id ? updated : row)),
    );
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="flex flex-row items-start justify-between gap-4">
          <div>
            <CardTitle className="text-base">Proof somebody else wrote</CardTitle>
            <p className="mt-1 text-sm text-muted-foreground">
              Your own site has no testimonial, so every sentence of your marketing is you
              asserting something about yourself — which a stranger discounts to roughly nothing.
              Almost every real company has been vouched for somewhere and forgotten. This goes
              and looks.
            </p>
          </div>
          <Button size="sm" onClick={onHunt} disabled={hunting}>
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

      {pending.length === 0 ? (
        <Card>
          <CardContent className="p-6 text-sm text-muted-foreground">
            {rows.length === 0
              ? "Nothing found yet. If a search comes back empty, that is itself the answer: nobody outside your own site has written about you, and three customer names would change your copy more than any rewrite."
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
