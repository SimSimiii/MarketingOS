import { Suspense } from "react";

import { PageLoading } from "@/lib/page-data";
import { CampaignsView } from "./campaigns-view";

export default function Page() {
  return (
    <Suspense fallback={<PageLoading />}>
      <CampaignsView />
    </Suspense>
  );
}
