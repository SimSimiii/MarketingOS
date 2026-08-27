import Link from "next/link";
import { notFound } from "next/navigation";

import { BrandNav } from "./brand-nav";
import { BrandSwitcher } from "./brand-switcher";
import { buttonVariants } from "@/components/ui/button";
import { api } from "@/lib/api-client";

/** One business, and everything the system knows about it.
 *
 * Knowledge and market are both scoped here rather than to a campaign, for the
 * same reason: they belong to the business and outlive any one run. Scoping
 * them to a *page* instead - one global Market that quietly picks a brand -
 * makes that ownership invisible, and invites the reader to treat a competitor
 * list as a property of the account rather than of the company it describes.
 */
export default async function BrandLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ brandId: string }>;
}) {
  const { brandId } = await params;

  // All five are keyed by the brand id in the route, so none of them needs the
  // brand record to know what to ask for. Awaiting the guard alone first put a
  // whole round trip in front of the other four, and this layout wraps four
  // routes - on three of them the child page does not refetch the set, so
  // nothing else was already in flight to hide it.
  const [brand, allBrands, documents, base, market] = await Promise.all([
    api.getBrand(brandId).catch(() => null),
    api.listBrands().catch(() => null),
    api.listKnowledgeDocuments({ brandId }).catch(() => []),
    api.getKnowledgeBase({ brandId }).catch(() => null),
    api.getMarket(brandId).catch(() => null),
  ]);
  if (!brand) {
    notFound();
  }
  const brands = allBrands ?? [brand];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold tracking-tight">{brand.name}</h1>
            <Link
              href="/brands"
              className="text-xs text-muted-foreground underline-offset-2 hover:underline"
            >
              All brands
            </Link>
          </div>
          {brand.website_url ? (
            <a
              href={brand.website_url}
              target="_blank"
              rel="noreferrer noopener"
              className="text-sm text-muted-foreground hover:underline"
            >
              {brand.website_url}
            </a>
          ) : (
            <p className="text-sm text-muted-foreground">
              No website on file — add one so a scan knows where to start.
            </p>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <BrandSwitcher brand={brand} brands={brands} />
          <Link
            href={`/campaigns?brand=${brand.id}`}
            className={buttonVariants({ variant: "outline", size: "sm" })}
          >
            Campaigns
          </Link>
        </div>
      </div>

      <BrandNav
        brandId={brand.id}
        counts={{
          sources: documents.length,
          facts: base?.total ?? null,
          rivals: market?.rivals.filter((rival) => !rival.muted).length ?? 0,
          alerts: market?.unseen_alerts ?? 0,
        }}
      />

      {children}
    </div>
  );
}
