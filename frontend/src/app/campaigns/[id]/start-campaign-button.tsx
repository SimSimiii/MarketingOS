"use client";

import { Play } from "lucide-react";

import { useRunLauncher } from "@/components/run-launcher";
import { Button } from "@/components/ui/button";
import type { CampaignGenerationAdvice } from "@/lib/types";

/** The campaign page's primary action. The run happens in the background
 * (see execution_manager on the backend) - /start returns at once with a
 * RUNNING execution, so this goes straight to the run's own page. When the
 * page already knows the recommendation says not to run, the button is
 * labelled "Generate anyway" under a notice saying why - pressing it is the
 * override, so it is not asked a second time. */
export function StartCampaignButton({
  campaignId,
  advice,
  hasActiveRun = false,
}: {
  campaignId: string;
  advice: CampaignGenerationAdvice | null;
  hasActiveRun?: boolean;
}) {
  const launcher = useRunLauncher(campaignId, "start");

  return (
    <>
      <Button
        onClick={() => (advice?.override_required ? launcher.launch(true) : launcher.run())}
        disabled={launcher.busy || hasActiveRun}
      >
        <Play aria-hidden="true" />
        {hasActiveRun
          ? "Campaign running"
          : launcher.busy
          ? "Starting…"
          : advice?.override_required
            ? "Generate anyway"
            : "Run campaign"}
      </Button>
      {launcher.dialog}
    </>
  );
}
