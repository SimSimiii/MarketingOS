import { Suspense } from "react";

import { PageLoading } from "@/lib/page-data";
import { BrandsView } from "./brands-view";

export default function BrandsPage() {
  return (
    <Suspense fallback={<PageLoading />}>
      <BrandsView />
    </Suspense>
  );
}
