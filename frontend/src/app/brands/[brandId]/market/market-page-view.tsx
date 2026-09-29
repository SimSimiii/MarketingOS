"use client";

import { MarketView } from "./market-view";
import { api } from "@/lib/api-client";
import { PageData, notFound, usePageData, useRouteIds } from "@/lib/page-data";

/** One brand's market.
 *
 * A market belongs to a business, not to a campaign and not to the account:
 * two brands have different competitors, different proof and different claims
 * that are theirs alone. Scoping this to the brand in the URL is what makes
 * the competitor list a property of the company it describes rather than of
 * whichever brand a global page happened to pick first. */
export function BrandMarketView() {
  const { brandId } = useRouteIds();
  const state = usePageData(async () => {
  const brand = await api.getBrand(brandId).catch(() => null);
  if (!brand) {
    notFound();
  }

  const [market, proof, radar, audience, job] = await Promise.all([
    api.getMarket(brandId),
    api.listProof(brandId).catch(() => []),
    api.listRadar(brandId).catch(() => []),
    api
      .getAudience(brandId)
      .catch(() => ({
        brand_id: brandId,
        map: null,
        prospects: [],
        research: [],
        relevance: [],
        capability_profile: null,
        note: "",
      })),
    api.getMarketJob(brandId).catch(() => null),
  ]);
  return { brand, market, proof, radar, audience, job };
  }, [brandId]);

  return (
    <PageData state={state}>
      {({ brand, market, proof, radar, audience, job }) => (
    <MarketView
      brand={brand}
      initialMarket={market}
      initialProof={proof}
      initialRadar={radar}
      initialAudience={audience}
      initialJob={job}
    />
      )}
    </PageData>
  );
}
