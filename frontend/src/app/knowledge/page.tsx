import { Suspense } from "react";

import { PageLoading } from "@/lib/page-data";
import { CampaignSourcesView } from "./sources-view";

export default function Page() {
  return (
    <Suspense fallback={<PageLoading />}>
      <CampaignSourcesView />
    </Suspense>
  );
}
