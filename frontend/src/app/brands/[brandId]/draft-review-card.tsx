"use client";

import { useEffect, useState, type FormEvent } from "react";

import { SourceReviewDetails } from "@/components/source-review-details";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api-client";
import type { ApiSchemas } from "@/lib/api-schema";
import { startVisiblePolling } from "@/lib/visible-polling";

export function DraftReviewCard({ brandId, initialJob }: {
  brandId: string;
  initialJob: ApiSchemas["DraftReviewJobRead"] | null;
}) {
  const [text, setText] = useState("");
  const [destination, setDestination] = useState("");
  const [job, setJob] = useState(initialJob);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const activeJobId = job?.state === "running" ? job.id : null;
  const busy = submitting || activeJobId !== null;
  const review = job?.result;

  useEffect(() => {
    if (!activeJobId) return;
    let stopped = false;
    const stopPolling = startVisiblePolling(async () => {
      try {
        const state = await api.getDraftReview(brandId, activeJobId);
        if (stopped) return;
        setJob(state);
        setError("");
      } catch {
        if (stopped) return;
        setError("Could not read the review status. Trying again…");
      }
    }, 2500);
    return () => { stopped = true; stopPolling(); };
  }, [activeJobId, brandId]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setJob(null);
    setSubmitting(true);
    try {
      setJob(await api.reviewDraft(brandId, { text, destination: destination.trim() || null }));
    } catch (error) {
      setError(error instanceof Error ? error.message : "The draft could not be reviewed.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Card>
      <CardHeader><CardTitle className="text-base">Check an existing email</CardTitle></CardHeader>
      <CardContent>
        <form className="space-y-3" onSubmit={submit}>
          <div className="space-y-2">
            <Label htmlFor="draft-review-text">Email text</Label>
            <Textarea id="draft-review-text" rows={5} maxLength={16000} required disabled={busy}
              value={text} onChange={(event) => { setText(event.target.value); setJob(null); }}
              placeholder="Paste the subject, preview and message you plan to send." />
          </div>
          <div className="space-y-2">
            <Label htmlFor="draft-review-url">Button destination (optional)</Label>
            <Input id="draft-review-url" type="url" disabled={busy} value={destination}
              onChange={(event) => { setDestination(event.target.value); setJob(null); }} />
          </div>
          <Button size="sm" disabled={busy || !text.trim()}>
            {busy ? "Checking sources…" : "Check against brand sources"}
          </Button>
        </form>
        {(error || job?.error) && <p className="mt-3 text-sm text-destructive" role="alert">{error || job?.error}</p>}
        {review && (
          <section className="mt-4 space-y-3 text-sm" aria-live="polite">
            <h3 className="font-semibold">
              {!text && "Previous email · "}
              {review.approved ? "Source review passed"
                : review.decision?.verdict === "revise" ? "Changes needed" : "Review inconclusive"}
            </h3>
            {review.decision ? (
              <SourceReviewDetails decision={review.decision} sources={review.sources} />
            ) : review.issues.map((issue, index) => <p key={index}>{issue.detail}</p>)}
          </section>
        )}
      </CardContent>
    </Card>
  );
}
