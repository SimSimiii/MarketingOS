"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { ConfirmDialog, useConfirm } from "@/components/confirm-dialog";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api-client";
import type { Campaign } from "@/lib/types";

type Action = "archive" | "unarchive" | "duplicate" | "delete";

/** Archive/unarchive/duplicate/delete for one campaign - used on both the
 * campaigns list (compact) and a campaign's own detail page. */
export function CampaignActions({
  campaign,
  redirectOnDeleteTo,
}: {
  campaign: Campaign;
  /** Where to navigate once deleted - e.g. the campaigns list, when this
   * renders on the campaign's own detail page (a plain refresh would just
   * refetch a now-404 page). Omit to stay put and refresh (list rows). */
  redirectOnDeleteTo?: string;
}) {
  const router = useRouter();
  const [busy, setBusy] = useState<Action | null>(null);
  const confirmDelete = useConfirm();

  async function handleArchiveToggle() {
    const archiving = campaign.status === "active";
    setBusy(archiving ? "archive" : "unarchive");
    try {
      if (archiving) await api.archiveCampaign(campaign.id);
      else await api.unarchiveCampaign(campaign.id);
      toast.success(archiving ? "Campaign archived" : "Campaign restored");
      router.refresh();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Something went wrong");
    } finally {
      setBusy(null);
    }
  }

  async function handleDuplicate() {
    setBusy("duplicate");
    try {
      const clone = await api.duplicateCampaign(campaign.id);
      toast.success("Campaign duplicated");
      router.push(`/campaigns/${clone.id}`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not duplicate");
      setBusy(null);
    }
  }

  async function handleDelete() {
    setBusy("delete");
    try {
      await api.deleteCampaign(campaign.id);
      confirmDelete.setOpen(false);
      toast.success("Campaign deleted");
      if (redirectOnDeleteTo) router.push(redirectOnDeleteTo);
      else router.refresh();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not delete");
      setBusy(null);
    }
  }

  return (
    <div className="flex items-center gap-1.5">
      <Button variant="ghost" size="sm" disabled={busy !== null} onClick={handleArchiveToggle}>
        {campaign.status === "active"
          ? busy === "archive"
            ? "Archiving..."
            : "Archive"
          : busy === "unarchive"
            ? "Restoring..."
            : "Unarchive"}
      </Button>
      <Button variant="ghost" size="sm" disabled={busy !== null} onClick={handleDuplicate}>
        {busy === "duplicate" ? "Duplicating..." : "Duplicate"}
      </Button>
      <Button
        variant="ghost"
        size="sm"
        className="text-destructive hover:text-destructive"
        disabled={busy !== null}
        onClick={confirmDelete.ask}
      >
        Delete
      </Button>

      <ConfirmDialog
        open={confirmDelete.open}
        onOpenChange={confirmDelete.setOpen}
        title={`Delete "${campaign.name}"?`}
        description="Every run, deliverable and attached document goes with it. This cannot be undone - archive instead if you only want it out of the way."
        confirmLabel="Delete campaign"
        pending={busy === "delete"}
        onConfirm={handleDelete}
      />
    </div>
  );
}
