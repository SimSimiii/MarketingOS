"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";

import { Notice } from "@/components/notice";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api-client";
import { timeAgo } from "@/lib/format";
import type { EmailRevision, EmailRevisionHistory, GeneratedAsset } from "@/lib/types";
import { cn } from "@/lib/utils";
import { startVisiblePolling } from "@/lib/visible-polling";
import { diffStats, diffWords } from "@/lib/word-diff";

const MAX_CHARS = 500;
const POLL_MS = 1500;

const STATE_LABEL: Record<string, string> = {
  running: "Writing…",
  proposed: "Proposal",
  blocked: "Failed a check",
  unchanged: "No change",
  failed: "Could not finish",
  accepted: "Accepted",
  rejected: "Declined",
};

interface Issue {
  gate: string;
  detail: string;
  severity?: string;
}

function issuesOf(revision: EmailRevision): Issue[] {
  const issues = (revision.checks as { issues?: Issue[] } | null)?.issues;
  return Array.isArray(issues) ? issues : [];
}

/**
 * Ask for a change to one finished email, see what it would change, decide.
 *
 * Nothing on the email moves until a proposal is accepted, and the original
 * is always one click away. A proposal is checked by the same deterministic
 * gates as the run - on its own text, never inheriting the original's
 * verdicts - and one that fails them is shown but cannot be used. It is not
 * read cold again, and the panel says so rather than showing a score.
 */
export function EmailRevisionPanel({
  executionId,
  asset,
  onAssetChange,
}: {
  executionId: string;
  asset: GeneratedAsset;
  onAssetChange?: (asset: GeneratedAsset) => void;
}) {
  const [history, setHistory] = useState<EmailRevisionHistory | null>(null);
  const [instruction, setInstruction] = useState("");
  const [base, setBase] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const field = useRef<HTMLTextAreaElement>(null);

  const apply = useCallback((next: EmailRevisionHistory) => {
    setHistory(next);
    onAssetChange?.(next.asset as GeneratedAsset);
  }, [onAssetChange]);

  const load = useCallback(async () => {
    try {
      const next = await api.getEmailRevisions(executionId, asset.id);
      setHistory(next);
      setBase((current) => current ?? next.selected_revision_id ?? null);
    } catch {
      toast.error("Could not load this email's edit history.");
    }
  }, [executionId, asset.id]);

  useEffect(() => {
    let cancelled = false;
    api.getEmailRevisions(executionId, asset.id)
      .then((next) => {
        if (cancelled) return;
        setHistory(next);
        setBase(next.selected_revision_id ?? null);
      })
      .catch(() => { if (!cancelled) toast.error("Could not load this email's edit history."); });
    return () => { cancelled = true; };
  }, [executionId, asset.id]);

  const running = history?.revisions.some((row) => row.state === "running") ?? false;
  useEffect(() => {
    if (!running) return;
    return startVisiblePolling(load, POLL_MS);
  }, [running, load]);

  const byId = useMemo(
    () => new Map((history?.revisions ?? []).map((row) => [row.id, row])),
    [history],
  );
  const latest = history?.revisions.at(-1) ?? null;
  const pending = latest && ["running", "proposed", "blocked", "unchanged", "failed"].includes(latest.state) ? latest : null;
  const remaining = history ? history.max_revisions - history.revisions.length : 0;

  function contentOf(revisionId: string | null | undefined): string {
    const row = revisionId ? byId.get(revisionId) : undefined;
    return row?.content || history?.original_content || asset.content;
  }

  async function submit() {
    const text = instruction.trim();
    if (!text) return;
    setBusy(true);
    try {
      await api.requestEmailRevision(executionId, asset.id, { instruction: text, base_revision_id: base });
      setInstruction("");
      await load();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not start the proposal.");
    } finally {
      setBusy(false);
    }
  }

  async function decide(action: "accept" | "reject", revisionId: string) {
    setBusy(true);
    try {
      const next = action === "accept"
        ? await api.acceptEmailRevision(executionId, asset.id, revisionId)
        : await api.rejectEmailRevision(executionId, asset.id, revisionId);
      apply(next);
      if (action === "accept") {
        setBase(revisionId);
        toast.success("This version is now the one copied and exported. The original is kept.");
      }
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not record that decision.");
    } finally {
      setBusy(false);
    }
  }

  async function restore() {
    setBusy(true);
    try {
      apply(await api.restoreOriginalEmail(executionId, asset.id));
      setBase(null);
      toast.success("Original restored.");
    } catch {
      toast.error("Could not restore the original.");
    } finally {
      setBusy(false);
    }
  }

  function adjustFurther(revisionId: string) {
    setBase(revisionId);
    field.current?.focus();
  }

  if (!history) {
    return <p className="mt-4 text-sm text-muted-foreground">Loading this email&apos;s edits…</p>;
  }

  return (
    <div className="mt-5 space-y-4 border-t border-hairline pt-5">
      <p className="max-w-[42rem] text-xs leading-relaxed text-muted-foreground">
        Ask for a change - “too long”, “more direct”. Only this email is rewritten, from the plan it
        was written to. Each proposal gets a fresh AI source review; it is not read
        cold again, so it carries no reader score. The original is always kept.
      </p>

      {!history.available && <Notice tone="info">{history.reason}</Notice>}

      {pending && (
        <Proposal
          revision={pending}
          before={contentOf(pending.base_revision_id)}
          busy={busy}
          onAccept={() => void decide("accept", pending.id)}
          onReject={() => void decide("reject", pending.id)}
          onFurther={() => adjustFurther(pending.id)}
        />
      )}

      {history.available && !running && (
        <div className="space-y-2">
          <label className="block space-y-1">
            <span className="text-xs text-muted-foreground">
              What should change?{" "}
              <span className="opacity-80">
                Adjusting {base ? `the proposal “${byId.get(base)?.instruction ?? "…"}”` : "the original"}
              </span>
              {base && (
                <button type="button" className="ml-2 text-violet-300 hover:underline" onClick={() => setBase(null)}>
                  use the original instead
                </button>
              )}
            </span>
            <Textarea
              ref={field}
              value={instruction}
              maxLength={MAX_CHARS}
              onChange={(event) => setInstruction(event.target.value)}
              placeholder="e.g. too long - keep it to three short paragraphs"
              className="min-h-16 max-w-[42rem]"
              disabled={busy || remaining <= 0}
            />
          </label>
          <div className="flex flex-wrap items-center gap-3">
            <Button size="sm" onClick={() => void submit()} disabled={busy || !instruction.trim() || remaining <= 0}>
              Propose a change
            </Button>
            <span className="text-xs text-muted-foreground tabular-nums">
              {remaining > 0 ? `${remaining} proposal(s) left for this email` : "Proposal limit reached"}
            </span>
          </div>
        </div>
      )}

      {(history.revisions.length > 0 || history.selected_revision_id) && (
        <details className="group/history text-sm">
          <summary className="cursor-pointer text-xs text-muted-foreground hover:text-foreground">
            History ({history.revisions.length})
          </summary>
          <ul className="mt-2 space-y-1.5">
            <li className="flex flex-wrap items-center gap-2 rounded-lg bg-white/[0.03] px-3 py-2 ring-1 ring-white/[0.06]">
              <span className="min-w-0 flex-1">Original, as the run delivered it</span>
              {history.selected_revision_id
                ? <Button size="xs" variant="outline" disabled={busy} onClick={() => void restore()}>Restore original</Button>
                : <Badge variant="secondary">In use</Badge>}
            </li>
            {history.revisions.map((row) => (
              <li key={row.id} className="flex flex-wrap items-center gap-2 rounded-lg bg-white/[0.03] px-3 py-2 ring-1 ring-white/[0.06]">
                <span className="min-w-0 flex-1">“{row.instruction}”</span>
                <span className="text-xs text-muted-foreground">{timeAgo(row.created_at)}</span>
                {row.id === history.selected_revision_id
                  ? <Badge>In use</Badge>
                  : <Badge variant="secondary">{STATE_LABEL[row.state] ?? row.state}</Badge>}
                {row.id !== history.selected_revision_id && ["accepted", "rejected"].includes(row.state) && row.content && (
                  <Button size="xs" variant="outline" disabled={busy} onClick={() => void decide("accept", row.id)}>
                    Use this version
                  </Button>
                )}
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}

function Proposal({
  revision, before, busy, onAccept, onReject, onFurther,
}: {
  revision: EmailRevision;
  before: string;
  busy: boolean;
  onAccept: () => void;
  onReject: () => void;
  onFurther: () => void;
}) {
  const parts = useMemo(
    () => (revision.content ? diffWords(before, revision.content) : []),
    [before, revision.content],
  );
  if (revision.state === "running") {
    return (
      <p role="status" className="flex items-center gap-2 text-sm text-muted-foreground">
        <span className="live-dot" aria-hidden="true" /> Writing a proposal for “{revision.instruction}”…
      </p>
    );
  }
  if (revision.state === "failed") {
    return <Notice tone="warning" title="No proposal this time">{revision.error || "The email is unchanged."}</Notice>;
  }
  if (revision.state === "unchanged") {
    return (
      <Notice tone="info" title={`Nothing changed for “${revision.instruction}”`}>
        {revision.error || "The email was left as it was."}
      </Notice>
    );
  }
  const issues = issuesOf(revision);
  const blocking = issues.filter((issue) => issue.severity !== "advisory");
  const advisory = issues.filter((issue) => issue.severity === "advisory");
  const stats = diffStats(parts);
  const blocked = revision.state === "blocked";
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
        <span className="font-medium text-foreground">Proposed for “{revision.instruction}”</span>
        <span className="tabular-nums text-emerald-300">+{stats.added}</span>
        <span className="tabular-nums text-rose-300">−{stats.removed} words</span>
      </div>
      <pre
        aria-label="Changes from the version it was asked of"
        className="max-w-[42rem] whitespace-pre-wrap break-words rounded-xl bg-black/20 p-5 font-sans text-[0.9375rem] leading-7 ring-1 ring-white/[0.07]"
      >
        {parts.map((part, index) => (
          <span
            key={index}
            className={cn(
              part.kind === "added" && "rounded-sm bg-emerald-500/20 text-emerald-50",
              part.kind === "removed" && "rounded-sm bg-rose-500/15 text-rose-200/80 line-through",
            )}
          >
            {part.kind === "added" && <span className="sr-only">[added] </span>}
            {part.kind === "removed" && <span className="sr-only">[removed] </span>}
            {part.text}
          </span>
        ))}
      </pre>
      {blocked ? (
        <Notice tone="danger" title="This proposal failed an automatic check and cannot be used">
          <ul className="space-y-1">{blocking.map((issue) => <li key={issue.detail}>— {issue.detail}</li>)}</ul>
          <p className="mt-1.5 text-xs opacity-80">Your preference is kept, but not at the cost of an unsupported claim. Try rephrasing the request.</p>
        </Notice>
      ) : (
        <p className="text-xs text-emerald-300/90">Passed every blocking check on its own text.</p>
      )}
      {advisory.length > 0 && (
        <Notice tone="info" title="Worth a look">
          <ul className="space-y-1">{advisory.map((issue) => <li key={issue.detail}>— {issue.detail}</li>)}</ul>
        </Notice>
      )}
      {revision.state === "proposed" || blocked ? (
        <div className="flex flex-wrap gap-2">
          <Button size="sm" onClick={onAccept} disabled={busy || blocked}>Accept</Button>
          <Button size="sm" variant="outline" onClick={onReject} disabled={busy}>Decline</Button>
          {!blocked && <Button size="sm" variant="ghost" onClick={onFurther} disabled={busy}>Adjust further</Button>}
        </div>
      ) : null}
    </div>
  );
}
