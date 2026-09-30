"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Archive, ArchiveRestore, Copy, MoreHorizontal, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { ConfirmDialog, useConfirm } from "@/components/confirm-dialog";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { api } from "@/lib/api-client";
import type { Campaign } from "@/lib/types";
import { refreshPage } from "@/lib/page-data";

type Action = "archive" | "unarchive" | "duplicate" | "delete";

/** Archive/unarchive/duplicate/delete for one campaign - used on both the
 * campaigns list and a campaign's own detail page.
 *
 * One menu rather than three text buttons. As buttons they were the widest
 * column in the campaigns table, which pushed the table past the edge of a
 * 1440px screen and hid them - the actions were on the page and nobody could
 * see them. Beside the detail page's primary action they were three more
 * things of equal weight to "Run campaign". */
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
      refreshPage();
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
      else refreshPage();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not delete");
      setBusy(null);
    }
  }

  const archiving = campaign.status === "active";

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger
          render={
            <Button
              variant="ghost"
              size="icon-sm"
              aria-label={`Actions for ${campaign.name}`}
              disabled={busy !== null}
            />
          }
        >
          <MoreHorizontal aria-hidden="true" />
        </DropdownMenuTrigger>
        <DropdownMenuContent>
          <DropdownMenuItem onClick={handleDuplicate}>
            <Copy aria-hidden="true" />
            {busy === "duplicate" ? "Duplicating…" : "Duplicate"}
          </DropdownMenuItem>
          <DropdownMenuItem onClick={handleArchiveToggle}>
            {archiving ? <Archive aria-hidden="true" /> : <ArchiveRestore aria-hidden="true" />}
            {archiving ? "Archive" : "Restore from archive"}
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem variant="destructive" onClick={confirmDelete.ask}>
            <Trash2 aria-hidden="true" />
            Delete…
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <ConfirmDialog
        open={confirmDelete.open}
        onOpenChange={confirmDelete.setOpen}
        title={`Delete "${campaign.name}"?`}
        description="Every run, deliverable and attached document goes with it. This cannot be undone - archive instead if you only want it out of the way."
        confirmLabel="Delete campaign"
        pending={busy === "delete"}
        onConfirm={handleDelete}
      />
    </>
  );
}
