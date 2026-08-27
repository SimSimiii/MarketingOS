import { redirect } from "next/navigation";

import { api } from "@/lib/api-client";

/** The market used to live here, account-wide, quietly showing whichever brand
 * happened to be first. It belongs to a business, so it moved inside one.
 *
 * Kept as a redirect rather than deleted: links and bookmarks to `/market`
 * exist, and dropping them on a 404 would be a worse answer than the one this
 * page is here to correct. */
export default async function LegacyMarketPage({
  searchParams,
}: {
  searchParams: Promise<{ brand?: string }>;
}) {
  const { brand } = await searchParams;
  if (brand) {
    redirect(`/brands/${brand}/market`);
  }

  const brands = await api.listBrands().catch(() => []);
  redirect(brands.length === 1 ? `/brands/${brands[0].id}/market` : "/brands");
}
