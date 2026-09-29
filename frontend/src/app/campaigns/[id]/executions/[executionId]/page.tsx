import { Suspense } from "react";

import { PageLoading } from "@/lib/page-data";
import { ExecutionResultView } from "./execution-page-view";

/**
 * One exported page for every campaign, built for the placeholder "_": ids
 * cannot be known at build time. The CloudFront function in
 * frontend/template.yaml serves it for every real id, and the view reads the
 * real one from the address bar - see useRouteIds in lib/page-data.
 */
export function generateStaticParams() {
  return [{ id: "_", executionId: "_" }];
}

export default function Page() {
  return (
    <Suspense fallback={<PageLoading />}>
      <ExecutionResultView />
    </Suspense>
  );
}
