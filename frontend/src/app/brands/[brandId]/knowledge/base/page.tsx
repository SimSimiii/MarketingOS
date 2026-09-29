import { Suspense } from "react";

import { PageLoading } from "@/lib/page-data";
import { BrandKnowledgeBaseView } from "./base-view";

export default function Page() {
  return (
    <Suspense fallback={<PageLoading />}>
      <BrandKnowledgeBaseView />
    </Suspense>
  );
}
