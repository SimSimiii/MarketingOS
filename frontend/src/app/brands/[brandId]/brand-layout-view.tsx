"use client";

import Link from "next/link";
import { ArrowLeft, ArrowUpRight, Building2, Megaphone } from "lucide-react";

import { BrandNav } from "./brand-nav";
import { BrandSwitcher } from "./brand-switcher";
import { DocumentTitle } from "@/components/document-title";
import { buttonVariants } from "@/components/ui/button";
import { ApiError, api } from "@/lib/api-client";
import { NestedPageProvider, PageData, notFound, usePageData, useRouteIds } from "@/lib/page-data";

/** One business, and everything the system knows about it.
 *
 * Knowledge and market are both scoped here rather than to a campaign, for the
 * same reason: they belong to the business and outlive any one run. Scoping
 * them to a *page* instead - one global Market that quietly picks a brand -
 * makes that ownership invisible, and invites the reader to treat a competitor
 * list as a property of the account rather than of the company it describes.
 */
export function BrandLayoutView({ children }: { children: React.ReactNode }) {
  const { brandId } = useRouteIds();

  // All five are keyed by the brand id in the route, so none of them needs the
  // brand record to know what to ask for. Awaiting the guard alone first put a
  // whole round trip in front of the other four, and this layout wraps four
  // routes - on three of them the child page does not refetch the set, so
  // nothing else was already in flight to hide it.
  const state = usePageData(async () => {
    const [brand, allBrands, documents, base, market] = await Promise.all([
      api.getBrand(brandId).catch((error) => {
        if (error instanceof ApiError && error.status === 404) notFound();
        throw error;
      }),
      api.listBrands(),
      api.listKnowledgeDocuments({ brandId }),
      api.getKnowledgeBase({ brandId }).catch((error) => {
        if (error instanceof ApiError && error.status === 404) return null;
        throw error;
      }),
      api.getMarket(brandId),
    ]);
    if (!brand) {
      notFound();
    }
    return { brand, brands: allBrands ?? [brand], documents, base, market };
  }, [brandId]);

  return (
    <PageData state={state}>
      {({ brand, brands, documents, base, market }) => (
    <div className="brand-workspace min-w-0 space-y-6">
      <DocumentTitle title={brand.name} />
      <header className="studio-hero rounded-2xl border border-border p-5 sm:p-6">
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
          <Link href="/brands" className="inline-flex items-center gap-2 text-xs font-medium text-muted-foreground hover:text-foreground"><ArrowLeft className="size-3.5" /> All brands</Link>
          <BrandSwitcher brand={brand} brands={brands} />
        </div>
        <div className="flex flex-wrap items-center justify-between gap-5">
          <div className="flex min-w-0 items-center gap-4">
            <div className="flex size-14 shrink-0 items-center justify-center rounded-2xl border border-violet-400/20 bg-violet-500/15 text-violet-300"><Building2 className="size-6" /></div>
            <div className="min-w-0">
              <p className="mb-1 text-[10px] font-medium uppercase tracking-[0.18em] text-violet-300">Brand workspace</p>
              <h1 className="break-words text-2xl font-semibold tracking-tight sm:text-3xl">{brand.name}</h1>
              {brand.website_url ? <a href={brand.website_url} target="_blank" rel="noreferrer noopener" className="mt-1 inline-flex max-w-full items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground"><span className="truncate">{brand.website_url.replace(/^https?:\/\//, "").replace(/\/$/, "")}</span><ArrowUpRight className="size-3 shrink-0" /></a> : <p className="mt-1 text-xs text-muted-foreground">Sources, knowledge and campaigns for this brand.</p>}
            </div>
          </div>
          <Link href={`/campaigns?brand=${brand.id}`} className={buttonVariants({ variant: "outline", size: "sm" })}><Megaphone className="size-4" /> Campaigns</Link>
        </div>
      </header>

      <BrandNav
        brandId={brand.id}
        counts={{
          sources: documents.length,
          facts: base?.total ?? null,
          rivals: market?.rivals.filter((rival) => !rival.muted).length ?? 0,
          alerts: market?.unseen_alerts ?? 0,
        }}
      />

      <NestedPageProvider>{children}</NestedPageProvider>
    </div>
      )}
    </PageData>
  );
}
