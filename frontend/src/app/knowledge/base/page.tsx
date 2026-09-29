import { Suspense } from "react";

import { PageLoading } from "@/lib/page-data";
import { KnowledgeBaseView } from "./one-off-base-view";

export default function Page() {
  return (
    <Suspense fallback={<PageLoading />}>
      <KnowledgeBaseView />
    </Suspense>
  );
}
