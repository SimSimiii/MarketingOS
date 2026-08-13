import { notFound } from "next/navigation";

import { ExecutionLiveView } from "@/app/campaigns/[id]/executions/[executionId]/execution-live-view";
import { api } from "@/lib/api-client";

export default async function ExecutionResultPage({
  params,
}: {
  params: Promise<{ id: string; executionId: string }>;
}) {
  const { id, executionId } = await params;

  const result = await api.getExecutionResult(executionId).catch((e) => {
    console.error("DEBUG getExecutionResult failed:", e);
    return null;
  });
  if (!result) {
    notFound();
  }

  return (
    <ExecutionLiveView
      executionId={executionId}
      campaignId={id}
      initialStatus={result.status}
      initialAssets={result.assets}
      initialResult={result.result}
      initialErrorMessage={result.error_message}
      startedAt={result.started_at}
      completedAt={result.completed_at}
      finalCostUsd={result.estimated_cost_usd}
    />
  );
}
