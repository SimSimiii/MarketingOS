"use client";

import { Download } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import type { GeneratedAsset } from "@/lib/types";

/** A local text download works even when clipboard permission is unavailable. */
export function ExportAllButton({ assets }: { assets: GeneratedAsset[] }) {
  if (assets.length === 0) return null;

  function download() {
    const text = [...assets].sort((a, b) => a.position - b.position).map((asset) => {
      const review = asset.asset_metadata?.sequence_review_pending === true
        ? "Sequence review pending.\n\n" : "";
      return `${asset.title}\n${"-".repeat(asset.title.length)}\n\n${review}${asset.content}`;
    }).join("\n\n\n");
    const url = URL.createObjectURL(new Blob(["\uFEFF", text], { type: "text/plain;charset=utf-8" }));
    try {
      const link = document.createElement("a");
      link.href = url;
      link.download = "marketingos-drafts.txt";
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch {
      toast.error("Could not download the drafts. Try copying them instead.");
    } finally {
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    }
  }

  return <Button type="button" variant="outline" size="sm" onClick={download}>
    <Download className="size-4" aria-hidden="true" />Download text
  </Button>;
}
