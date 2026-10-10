"use client";

import { api, nullIfMissing } from "@/lib/api-client";
import { PageData, usePageData, useRouteIds } from "@/lib/page-data";
import { BrandSectionHeader } from "../../brand-ui";
import { LinkedInWorkspace } from "./linkedin-workspace";

export function LinkedInView() {
  const { brandId } = useRouteIds();
  //: The audience map is what makes the criteria step worth having - it is
  //: the one description of this brand's buyer that did not come from the
  //: brand's own marketing. A brand nobody has mapped still works: the
  //: proposal falls back to the knowledge base.
  const state = usePageData(
    () => Promise.all([api.listLinkedInRuns(brandId), api.getAudience(brandId).catch(nullIfMissing)]),
    [brandId],
  );
  return (
    <PageData state={state}>
      {([runs, audience]) => (
        <div className="space-y-6">
          <BrandSectionHeader
            title="LinkedIn"
            description="Define your ideal contacts, find matching profiles and prepare a personalised message."
          />
          <LinkedInWorkspace
            key={brandId}
            brandId={brandId}
            initialRuns={runs}
            segments={audience?.map?.segments ?? []}
          />
        </div>
      )}
    </PageData>
  );
}
