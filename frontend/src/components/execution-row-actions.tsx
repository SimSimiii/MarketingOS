"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { ConfirmDialog, useConfirm } from "@/components/confirm-dialog";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api-client";
import type { CampaignExecution } from "@/lib/types";

/** Cancel (running/pending) or restart (failed/cancelled) for one execution
 * row in a campaign's Runs table. */
export function ExecutionRowActions({
  execution,
  campaignId,
}: {
  execution: CampaignExecution;
  campaignId: string;
}) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const confirmStop = useConfirm();

  async function handleCancel() {
    setBusy(true);
    try {
      await api.cancelExecution(execution.id);
      confirmStop.setOpen(false);
      toast.success("Stopping - it finishes the model call it's on, then stops for good");
      router.refresh();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not cancel");
    } finally {
      setBusy(false);
    }
  }

  async function handleRestart() {
    setBusy(true);
    try {
      const restarted = await api.restartCampaign(campaignId);
      router.push(`/campaigns/${campaignId}/executions/${restarted.id}`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not restart");
      setBusy(false);
    }
  }

  if (execution.status === "pending" || execution.status === "running") {
    return (
      <>
        <Button variant="ghost" size="sm" disabled={busy} onClick={confirmStop.ask}>
          {busy ? "Stopping..." : "Stop"}
        </Button>
        <ConfirmDialog
          open={confirmStop.open}
          onOpenChange={confirmStop.setOpen}
          title="Stop this campaign?"
          description="It stops as soon as the model call currently in flight finishes - already-finished emails are kept, but nothing further is generated and the run cannot be resumed."
          confirmLabel="Stop campaign"
          pending={busy}
          onConfirm={handleCancel}
        />
      </>
    );
  }
  if (execution.status === "failed" || execution.status === "cancelled") {
    return (
      <Button variant="ghost" size="sm" disabled={busy} onClick={handleRestart}>
        {busy ? "Restarting..." : "Restart"}
      </Button>
    );
  }
  return null;
}
