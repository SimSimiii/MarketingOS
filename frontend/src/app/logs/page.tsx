import { Suspense } from "react";

import { PageLoading } from "@/lib/page-data";
import { LogsView } from "./logs-view";

export default function Page() {
  return (
    <Suspense fallback={<PageLoading />}>
      <LogsView />
    </Suspense>
  );
}
