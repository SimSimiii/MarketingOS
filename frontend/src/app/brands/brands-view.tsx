"use client";

import { BrandDirectory } from "./brand-directory";
import { api } from "@/lib/api-client";
import { PageData, usePageData } from "@/lib/page-data";

export function BrandsView() {
  const state = usePageData(() => api.listBrandOverviews(), []);
  return <PageData state={state}>{(brands) => <BrandDirectory brands={brands} />}</PageData>;
}
