"use client";

import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import type { GeneratedAsset } from "@/lib/types";

/** The core ask is "write me 3 emails" - so the common case is wanting all of
 * them at once, not clicking Copy three times. Separated by a rule and their
 * titles so the sequence survives the paste. */
export function CopyAllButton({ assets }: { assets: GeneratedAsset[] }) {
  const [copied, setCopied] = useState(false);

  async function copyAll() {
    const combined = assets
      .map((asset) => `${asset.title}\n${"-".repeat(asset.title.length)}\n\n${asset.content}`)
      .join("\n\n\n");
    try {
      await navigator.clipboard.writeText(combined);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error("Could not copy - select the text and copy it manually");
    }
  }

  if (assets.length < 2) return null;

  return (
    <Button variant="outline" size="sm" onClick={copyAll}>
      {copied ? "Copied all" : `Copy all ${assets.length}`}
    </Button>
  );
}
