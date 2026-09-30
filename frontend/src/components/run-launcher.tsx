"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { ConfirmDialog } from "@/components/confirm-dialog";
import { api } from "@/lib/api-client";
import type { CampaignGenerationAdvice } from "@/lib/types";

/** "discovery only", from `discovery_only` - the words the recommendation
 * stores are identifiers, and the reader should see neither underscores nor
 * the same phrase twice when the readiness happens to agree with it. */
export function adviceHeadline(advice: CampaignGenerationAdvice): { state: string; readiness: string | null } {
  const readiness = advice.readiness.replaceAll("_", " ");
  const state = advice.recommendation?.state.replaceAll("_", " ") ?? readiness;
  return { state, readiness: readiness.toLowerCase() === state.toLowerCase() ? null : readiness };
}

/** The recommendation a run would override, as the body of a confirmation. */
export function AdviceSummary({ advice }: { advice: CampaignGenerationAdvice }) {
  const { state, readiness } = adviceHeadline(advice);
  return (
    <div className="space-y-2">
      <p>
        <span className="font-medium capitalize text-foreground">{state}</span>
        {readiness && <span className="text-muted-foreground"> · {readiness}</span>}
        {" — "}
        {advice.user_message}
      </p>
      {advice.reasons.length > 0 && (
        <ul className="space-y-1 text-xs">
          {advice.reasons.map((reason) => (
            <li key={reason}>— {reason}</li>
          ))}
        </ul>
      )}
      <p className="text-xs">The override is recorded with the new run.</p>
    </div>
  );
}

/**
 * Start or restart a campaign, asking first when the recommendation says not
 * to.
 *
 * Two places restarted a run and both asked through `window.confirm` - an
 * unstyled system box holding a bulleted list typed out as one string, which
 * a browser may also start suppressing after a few uses, silently turning the
 * question into a yes. One implementation, asked in the product's own dialog.
 */
export function useRunLauncher(campaignId: string, mode: "start" | "restart") {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [pendingAdvice, setPendingAdvice] = useState<CampaignGenerationAdvice | null>(null);

  async function launch(generateAnyway: boolean) {
    setBusy(true);
    try {
      const execution =
        mode === "start"
          ? await api.startCampaign(campaignId, generateAnyway)
          : await api.restartCampaign(campaignId, generateAnyway);
      setPendingAdvice(null);
      router.push(`/campaigns/${campaignId}/executions/${execution.id}`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : `Could not ${mode} the campaign`);
      setBusy(false);
    }
  }

  async function run() {
    setBusy(true);
    try {
      const advice = await api.getCampaignGenerationAdvice(campaignId);
      if (advice.override_required) {
        setPendingAdvice(advice);
        setBusy(false);
        return;
      }
    } catch {
      // No advice is not a reason to refuse: the API still decides whether
      // the run may start, and says so if it may not.
    }
    await launch(false);
  }

  const dialog = (
    <ConfirmDialog
      open={pendingAdvice !== null}
      onOpenChange={(open) => {
        if (!open) setPendingAdvice(null);
      }}
      title="Run against the recommendation?"
      description={pendingAdvice ? <AdviceSummary advice={pendingAdvice} /> : null}
      confirmLabel="Generate anyway"
      tone="default"
      pending={busy}
      onConfirm={() => launch(true)}
    />
  );

  return { run, launch, busy, dialog };
}
