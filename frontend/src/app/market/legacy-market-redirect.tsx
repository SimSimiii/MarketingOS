"use client";

import { useSearchParams } from "next/navigation";

import { api } from "@/lib/api-client";
import { PageData, redirect, usePageData } from "@/lib/page-data";

export function LegacyMarketRedirect() {
  const brand = useSearchParams().get("brand");
  const state = usePageData(async () => {
    if (brand) redirect(`/brands/${brand}/market`);
    const brands = await api.listBrands();
    return redirect(brands.length === 1 ? `/brands/${brands[0].id}/market` : "/brands");
  }, [brand]);
  return <PageData state={state}>{() => null}</PageData>;
}
