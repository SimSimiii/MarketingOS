import { Suspense } from "react";

import { PageLoading } from "@/lib/page-data";
import { BrandOverviewView } from "./overview-view";

export default function Page() {
  return (
    <Suspense fallback={<PageLoading />}>
      <BrandOverviewView />
    </Suspense>
  );
}
