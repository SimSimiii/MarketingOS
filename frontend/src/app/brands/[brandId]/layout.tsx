import Link from "next/link";
import { ArrowLeft, ArrowUpRight, Building2, Megaphone } from "lucide-react";
import { notFound } from "next/navigation";

import { BrandNav } from "./brand-nav";
import { BrandSwitcher } from "./brand-switcher";
import { buttonVariants } from "@/components/ui/button";
import { api } from "@/lib/api-server";

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
    <div className="brand-workspace min-w-0 space-y-6">
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
              {brand.website_url ? <a href={brand.website_url} target="_blank" rel="noreferrer noopener" className="mt-1 inline-flex max-w-full items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground"><span className="truncate">{brand.website_url.replace(/^https?:\/\//, "").replace(/\/$/, "")}</span><ArrowUpRight className="size-3 shrink-0" /></a> : <p className="mt-1 text-xs text-muted-foreground">Add your website in Sources to get started.</p>}
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

      {children}
    </div>
  );
}
