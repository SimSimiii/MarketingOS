import { Suspense } from "react";

import { PageLoading } from "@/lib/page-data";
import { DashboardView } from "./dashboard-view";

export default function Page() {
  return (
    <Suspense fallback={<PageLoading />}>
      <DashboardView />
    </Suspense>
  );
}
