import { Suspense } from "react";

import { LegacyMarketRedirect } from "./legacy-market-redirect";

/** The market used to live here, account-wide, quietly showing whichever brand
 * happened to be first. It belongs to a business, so it moved inside one.
 *
 * Kept as a redirect rather than deleted: links and bookmarks to `/market`
 * exist, and dropping them on a 404 would be a worse answer than the one this
 * page is here to correct. */
export default function LegacyMarketPage() {
  return (
    <Suspense>
      <LegacyMarketRedirect />
    </Suspense>
  );
}
