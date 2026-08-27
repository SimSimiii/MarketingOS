"use client";

import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

/** What one cold reader said about the version that shipped. Mirrors
 * app.marketing.report.ReaderVerdict. */
export interface ReaderVerdict {
  what_it_sells: string;
  stopped_at: string;
  biggest_doubt: string;
  to_click_it_would_have_to: string;
  fixes: string[];
  opens_in_100: number | null;
  clicks_in_100: number | null;
  persona: string;
  pull: number;
}

export interface ScoredEmail {
  position: number;
  subject: string;
  pull: number;
  landed?: boolean;
  read_reported?: boolean;
  reader_verdicts?: ReaderVerdict[];
  /** Interchangeable openings and category boilerplate the free check found
   * in the shipped copy. */
  sameness?: string[];
}

/** Why an email scored what it scored.
 *
 * This exists because the system's most expensive judgment used to reach the
 * user as a single digit. A run that scored 4/10 persisted exactly `{"pull":
 * 4}` — and the same model call had already said what it thought the email
 * was selling, where it stopped reading, what was really stopping it
 * clicking, and the one thing the email would have had to say for it to
 * click. All of it was thrown away.
 *
 * A user shown "4/10" learns that something is wrong. A user shown "I could
 * not tell what this company does" and "I would have clicked if it had told
 * me who else uses it" learns what to do on Monday. */
function VerdictBlock({ verdict }: { verdict: ReaderVerdict }) {
  return (
    <div className="space-y-2 text-sm">
      {verdict.persona && (
        <p className="text-xs text-muted-foreground">Read as: {verdict.persona}</p>
      )}

      {/* The single most diagnostic line here. An answer that does not match
          what the product is means the copy failed before any of its
          arguments were judged. */}
      {verdict.what_it_sells && (
        <div>
          <p className="text-xs text-muted-foreground">What they thought you were selling</p>
          <p className="text-foreground/90">{verdict.what_it_sells}</p>
        </div>
      )}

      {verdict.to_click_it_would_have_to && (
        <div className="rounded-md bg-emerald-500/10 p-2.5">
          <p className="text-xs text-emerald-300/80">
            &ldquo;I would have clicked if this email had told me…&rdquo;
          </p>
          <p className="mt-0.5 text-emerald-100">{verdict.to_click_it_would_have_to}</p>
        </div>
      )}

      <div className="grid gap-2 sm:grid-cols-2">
        {verdict.biggest_doubt && (
          <div>
            <p className="text-xs text-muted-foreground">What stopped them</p>
            <p className="text-foreground/80">{verdict.biggest_doubt}</p>
          </div>
        )}
        {verdict.stopped_at && (
          <div>
            <p className="text-xs text-muted-foreground">Where they drifted</p>
            <p className="text-foreground/80 italic">&ldquo;{verdict.stopped_at}&rdquo;</p>
          </div>
        )}
      </div>

      {verdict.fixes.length > 0 && (
        <div>
          <p className="text-xs text-muted-foreground">Lines they would cut or change</p>
          <ul className="mt-0.5 space-y-0.5">
            {verdict.fixes.map((fix) => (
              <li key={fix} className="text-foreground/80">
                — {fix}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function EmailVerdicts({ email }: { email: ScoredEmail }) {
  const [open, setOpen] = useState(email.landed === false);
  const verdicts = email.reader_verdicts ?? [];
  const opens = verdicts.find((verdict) => verdict.opens_in_100 !== null);

  return (
    <div className="rounded-lg border border-border">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="flex w-full items-start justify-between gap-3 p-3 text-left"
      >
        <div className="min-w-0">
          <p className="text-sm font-medium">
            #{email.position} &ldquo;{email.subject}&rdquo;
          </p>
          {opens && (
            <p className="text-xs text-muted-foreground tabular-nums">
              of a hundred people like them, {opens.opens_in_100} open it and{" "}
              {opens.clicks_in_100 ?? 0} click
            </p>
          )}
        </div>
        <Badge
          variant={email.landed === false ? "outline" : "default"}
          className={cn("shrink-0", email.landed === false && "text-amber-400")}
        >
          {email.read_reported === false ? "no verdict" : `${email.pull.toFixed(0)}/10`}
        </Badge>
      </button>

      {open && (
        <div className="space-y-4 border-t border-border/50 p-3">
          {verdicts.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No cold reader reported back on this one, so the score is a placeholder rather than
              a verdict.
            </p>
          ) : (
            verdicts.map((verdict, index) => (
              <div key={verdict.persona || index}>
                {index > 0 && <div className="mb-3 border-t border-border/40" />}
                <VerdictBlock verdict={verdict} />
              </div>
            ))
          )}

          {(email.sameness?.length ?? 0) > 0 && (
            <div className="rounded-md bg-amber-500/10 p-2.5 text-sm">
              <p className="text-xs text-amber-300/80">
                Could have been sent by a competitor
              </p>
              <ul className="mt-1 space-y-1 text-amber-100/90">
                {email.sameness?.map((issue) => (
                  <li key={issue}>— {issue}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function ReaderVerdictCard({ emails }: { emails: ScoredEmail[] }) {
  const withVerdicts = emails.filter(
    (email) => (email.reader_verdicts?.length ?? 0) > 0 || (email.sameness?.length ?? 0) > 0,
  );
  if (withVerdicts.length === 0) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Why it scored what it scored</CardTitle>
        <p className="mt-1 text-sm text-muted-foreground">
          A stranger who had never heard of you read each of these and reported what happened.
          They were never shown your brief, your website or what the email was trying to do —
          only the email.
        </p>
      </CardHeader>
      <CardContent className="space-y-2">
        {withVerdicts.map((email) => (
          <EmailVerdicts key={email.position} email={email} />
        ))}
      </CardContent>
    </Card>
  );
}
