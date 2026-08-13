"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { api } from "@/lib/api-client";

export function StartCampaignButton({ campaignId }: { campaignId: string }) {
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);

  async function handleClick() {
    setSubmitting(true);
    try {
      // The run happens in the background now (see execution_manager on the
      // backend) - /start returns immediately with a RUNNING execution, not
      // a finished one. Go straight to the live view instead of waiting here.
      const execution = await api.startCampaign(campaignId);
      router.push(`/campaigns/${campaignId}/executions/${execution.id}`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to start campaign");
      setSubmitting(false);
    }
  }

  return (
    <Button onClick={handleClick} disabled={submitting}>
      {submitting ? "Starting..." : "Run campaign"}
    </Button>
  );
}
