import { Suspense } from "react";

import { PageLoading } from "@/lib/page-data";
import { BrandSourcesView } from "./sources-view";

export default function Page() {
  return (
    <Suspense fallback={<PageLoading />}>
      <BrandSourcesView />
    </Suspense>
  );
}
