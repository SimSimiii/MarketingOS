"use client";

import { BrandSectionHeader } from "../../brand-ui";
import { BrandStyleForm } from "../brand-style-form";
import { api } from "@/lib/api-client";
import { PageData, usePageData, useRouteIds } from "@/lib/page-data";

export function BrandIdentityView() {
  const { brandId } = useRouteIds();
  const state = usePageData(() => api.getBrand(brandId), [brandId]);
  return (
    <PageData state={state}>
      {(brand) => (
        <div className="space-y-6">
          <BrandSectionHeader title="Brand identity" description="Set the visual details used in your branded emails." />
          <BrandStyleForm brand={brand} />
        </div>
      )}
    </PageData>
  );
}
