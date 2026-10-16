"use client";

import { useEffect, useRef, useState } from "react";
import { Check, Copy } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { splitEmail } from "@/lib/email-parts";
import type { AssetType, GeneratedAsset } from "@/lib/types";

const ASSET_LABELS: Record<AssetType, string> = {
  email: "Email",
  linkedin_message: "LinkedIn message",
  social_post: "Social post",
  ad: "Ad",
  blog: "Article",
  landing_page: "Landing page",
};

type View = "text" | "html";

/** One deliverable, with the copy button that is the whole point of it. */
export function AssetCard({ asset }: { asset: GeneratedAsset }) {
  const [copied, setCopied] = useState<View | null>(null);
  const [view, setView] = useState<View>("text");
  const copyTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => () => {
    if (copyTimer.current !== null) clearTimeout(copyTimer.current);
  }, []);

  const html = asset.content_html;

  async function copy(which: View) {
    const payload = which === "html" ? html : asset.content;
    if (!payload) return;
    try {
      await navigator.clipboard.writeText(payload);
      if (copyTimer.current !== null) clearTimeout(copyTimer.current);
      setCopied(which);
      copyTimer.current = setTimeout(() => setCopied(null), 2000);
    } catch {
      toast.error("Could not copy - select the text and copy it manually");
    }
  }

  const role = typeof asset.asset_metadata?.role === "string" ? asset.asset_metadata.role : null;
  const parts = asset.asset_type === "email" ? splitEmail(asset.content) : null;

  return (
    <Card className="rise hover:ring-violet-400/25">
      <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-4">
        <div className="flex min-w-0 flex-1 items-start gap-3.5">
          {asset.position > 0 && (
            <span
              className="brand-mark flex size-10 shrink-0 items-center justify-center rounded-xl font-display text-lg text-white tabular-nums"
              aria-hidden="true"
            >
              {String(asset.position).padStart(2, "0")}
            </span>
          )}
        <div className="min-w-0 space-y-1.5">
          <CardTitle className="text-base leading-snug">{asset.title}</CardTitle>
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="secondary">{ASSET_LABELS[asset.asset_type] ?? asset.asset_type}</Badge>
            {asset.asset_metadata?.sequence_review_pending === true && <Badge variant="secondary">{asset.asset_metadata?.checkpoint === true ? "Recovered draft · " : ""}Sequence review pending</Badge>}
            {asset.position > 0 && <span className="sr-only">Position {asset.position}</span>}
            {role && <span className="text-xs text-muted-foreground">{role}</span>}
            {/* A channel with a hard length is worth showing the length of. */}
            {typeof asset.asset_metadata?.limit === "number" && (
              <span className="text-xs text-muted-foreground tabular-nums">
                {String(asset.asset_metadata.characters ?? asset.content.length)} /{" "}
                {String(asset.asset_metadata.limit)} characters
              </span>
            )}
          </div>
        </div>
        </div>
        <div className="flex items-center gap-2">
          {html && (
            <div
              className="flex h-8 items-center rounded-[0.6rem] bg-black/25 p-0.5 ring-1 ring-white/[0.07]"
              role="group"
              aria-label="Email preview format"
            >
              {(["text", "html"] as const).map((option) => (
                <button
                  key={option}
                  type="button"
                  aria-pressed={view === option}
                  onClick={() => setView(option)}
                  className={cn(
                    "h-full cursor-pointer rounded-[0.45rem] px-3 text-xs font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-ring",
                    view === option
                      ? "bg-white/[0.1] text-foreground shadow-[inset_0_1px_0_0_oklch(1_0_0/8%)]"
                      : "text-muted-foreground hover:text-foreground",
                  )}
                >
                  {option === "text" ? "Text" : "Design"}
                </button>
              ))}
            </div>
          )}
          <Button variant={copied === view ? "secondary" : "outline"} size="sm" onClick={() => copy(view)}>
            {copied === view ? (
              <Check className="text-emerald-300" aria-hidden="true" />
            ) : (
              <Copy aria-hidden="true" />
            )}
            {copied === view ? "Copied" : view === "html" ? "Copy HTML" : parts ? "Copy all" : "Copy"}
          </Button>
          <span role="status" className="sr-only">{copied ? "Copied to clipboard" : ""}</span>
        </div>
      </CardHeader>
      <CardContent>
        {view === "html" && html ? (
          /* `sandbox` with no allow-scripts: the document is ours and carries
           * no script, but it is rendered from model output and a preview
           * pane is not the place to find out otherwise. srcDoc rather than a
           * blob URL keeps it same-origin-null and self-contained. */
          <iframe
            title={`${asset.title} - HTML preview`}
            srcDoc={html}
            sandbox=""
            className="h-[34rem] w-full rounded-xl bg-white ring-1 ring-white/10"
          />
        ) : parts ? (
          /* Subject and preview are shown the way an inbox shows them, each
             with its own copy button, because every sending tool has a field
             for each - copying the whole block meant cutting two lines back
             out of the body after pasting it. */
          <div className="max-w-[42rem] overflow-hidden rounded-xl bg-black/20 shadow-[inset_0_1px_0_0_oklch(1_0_0/4%)] ring-1 ring-white/[0.07]">
            <div className="space-y-2.5 border-b border-hairline bg-white/[0.02] p-4 sm:px-6">
              <CopyField label="Subject" value={parts.subject} emphasis />
              {parts.preview && <CopyField label="Preview" value={parts.preview} />}
            </div>
            <div className="group/body relative">
              <pre className="whitespace-pre-wrap break-words p-5 font-sans text-[0.9375rem] leading-7 text-foreground/95 sm:px-6 sm:py-6">
                {parts.body}
              </pre>
              <div className="absolute right-2 top-2">
                <CopyIconButton value={parts.body} label="Copy the body" />
              </div>
            </div>
          </div>
        ) : (
          /* The one thing on the page the reader is going to send. Set on its
             own surface at a measure a person reads at, rather than as a run
             of text flush against the card's own padding. */
          <pre className="max-w-[42rem] whitespace-pre-wrap break-words rounded-xl bg-black/20 p-5 font-sans text-[0.9375rem] leading-7 text-foreground/95 ring-1 ring-white/[0.07] sm:p-6">
            {asset.content}
          </pre>
        )}
      </CardContent>
    </Card>
  );
}

/** One labelled line of the email - subject, preview - and a way to copy it
 * alone. */
function CopyField({ label, value, emphasis = false }: { label: string; value: string; emphasis?: boolean }) {
  return (
    <div className="flex items-start gap-3">
      <span className="w-16 shrink-0 pt-0.5 text-[0.625rem] font-medium uppercase tracking-[0.16em] text-muted-foreground">
        {label}
      </span>
      <p className={emphasis ? "min-w-0 flex-1 text-[0.9375rem] font-semibold" : "min-w-0 flex-1 text-sm text-muted-foreground"}>
        {value}
      </p>
      <CopyIconButton value={value} label={`Copy the ${label.toLowerCase()}`} />
    </div>
  );
}

function CopyIconButton({ value, label }: { value: string; label: string }) {
  const [copied, setCopied] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => () => {
    if (timer.current !== null) clearTimeout(timer.current);
  }, []);

  async function copy() {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      if (timer.current !== null) clearTimeout(timer.current);
      timer.current = setTimeout(() => setCopied(false), 1500);
    } catch {
      toast.error("Could not copy - select the text and copy it manually");
    }
  }

  return (
    <Button
      variant="ghost"
      size="icon-xs"
      onClick={copy}
      aria-label={copied ? "Copied" : label}
      title={label}
      className="shrink-0 text-muted-foreground hover:text-foreground"
    >
      {copied ? <Check className="text-emerald-400" aria-hidden="true" /> : <Copy aria-hidden="true" />}
    </Button>
  );
}
