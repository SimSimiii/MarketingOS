"use client";

import { useState } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { AssetType, GeneratedAsset } from "@/lib/types";

const ASSET_LABELS: Record<AssetType, string> = {
  email: "Email",
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

  const html = asset.content_html;

  async function copy(which: View) {
    const payload = which === "html" ? html : asset.content;
    if (!payload) return;
    try {
      await navigator.clipboard.writeText(payload);
      setCopied(which);
      setTimeout(() => setCopied(null), 2000);
    } catch {
      toast.error("Could not copy - select the text and copy it manually");
    }
  }

  const role = typeof asset.asset_metadata?.role === "string" ? asset.asset_metadata.role : null;

  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between gap-4">
        <div className="space-y-1">
          <CardTitle className="text-base">{asset.title}</CardTitle>
          <div className="flex items-center gap-2">
            <Badge variant="secondary">{ASSET_LABELS[asset.asset_type] ?? asset.asset_type}</Badge>
            {asset.position > 0 && (
              <span className="text-xs text-muted-foreground">#{asset.position}</span>
            )}
            {role && <span className="text-xs text-muted-foreground">{role}</span>}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {html && (
            <div className="flex rounded-md border p-0.5" role="tablist">
              {(["text", "html"] as const).map((option) => (
                <button
                  key={option}
                  role="tab"
                  aria-selected={view === option}
                  onClick={() => setView(option)}
                  className={`rounded px-2 py-1 text-xs capitalize transition-colors ${
                    view === option
                      ? "bg-secondary text-secondary-foreground"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {option}
                </button>
              ))}
            </div>
          )}
          <Button variant="outline" size="sm" onClick={() => copy(view)}>
            {copied === view ? "Copied" : view === "html" ? "Copy HTML" : "Copy"}
          </Button>
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
            className="h-[32rem] w-full rounded-md border bg-white"
          />
        ) : (
          <pre className="whitespace-pre-wrap break-words font-sans text-sm leading-relaxed">
            {asset.content}
          </pre>
        )}
      </CardContent>
    </Card>
  );
}
