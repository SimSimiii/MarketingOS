import { notFound } from "next/navigation";

import { ExecutionLiveView } from "@/app/campaigns/[id]/executions/[executionId]/execution-live-view";
import { api } from "@/lib/api-client";

export default async function ExecutionResultPage({
  params,
}: {
  params: Promise<{ id: string; executionId: string }>;
}) {
  const { id, executionId } = await params;

  // The brand, so answers to the run's own questions can be kept with the
  // business rather than with this one campaign - what a company charges is
  // true of the company, and the next campaign should not have to ask again.
  // Fetched beside the result rather than behind it: the campaign id comes from
  // the route, so nothing here needs the result to know what to ask for.
  const [result, campaign] = await Promise.all([
    api.getExecutionResult(executionId).catch(() => null),
    api.getCampaign(id).catch(() => null),
  ]);
  if (!result) {
    notFound();
  }

  return (
    <ExecutionLiveView
      executionId={executionId}
      campaignId={id}
      brandId={campaign?.brand_id ?? null}
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
