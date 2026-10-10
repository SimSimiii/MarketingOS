"use client";

import Link from "next/link";
import { Archive, ChevronLeft, ChevronRight, Mail } from "lucide-react";

import { NewCampaignDialog } from "@/app/campaigns/new-campaign-dialog";
import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";
import { CampaignTable } from "@/app/campaigns/campaign-table";
import { buttonVariants } from "@/components/ui/button";
import { api } from "@/lib/api-client";
import { PageData, usePageData } from "@/lib/page-data";
import { useSearchParams } from "next/navigation";

export function CampaignsView() {
  const search = useSearchParams();
  const archived = search.get("archived") ?? undefined;
  const requestedPage = search.get("page") ?? undefined;
  const brandId = search.get("brand") ?? undefined;
  const includeArchived = archived === "1";
  const page = Math.max(1, Math.min(100000, Number.parseInt(requestedPage ?? "1", 10) || 1));
  const pageSize = 50;
  const state = usePageData(async () => {
  const [all, brands] = await Promise.all([
    api.listCampaigns(includeArchived, { limit: pageSize + 1, offset: (page - 1) * pageSize, brandId }),
    api.listBrands(),
  ]);
  return { all, brands };
  }, [includeArchived, page, brandId]);

  return (
    <PageData state={state}>
      {({ all, brands }) => {

  // A campaign belongs to a business, so this list can be read as one
  // business's work rather than as everything the account has ever run.
  const brand = brands.find((item) => item.id === brandId) ?? null;
  const campaigns = all.filter((campaign) => !campaign.channel).slice(0, pageSize);
  const pageHref = (target: number) => {
    const query = new URLSearchParams({ page: String(target) });
    if (includeArchived) query.set("archived", "1");
    if (brandId) query.set("brand", brandId);
    return `/campaigns?${query}`;
  };
  const brandNames = new Map(brands.map((item) => [item.id, item.name]));
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Email studio"
        title={`Campaigns${brand ? ` — ${brand.name}` : ""}`}
        description={brand ? "Everything this business has asked for, written from its own knowledge base." : "From the first brief to the final email. Manage your work here."}
        backTo={brand ? { href: `/brands/${brand.id}`, label: brand.name } : undefined}
        actions={<>
          {brand && (
            <Link
              href={`/campaigns${includeArchived ? "?archived=1" : ""}`}
              className={buttonVariants({ variant: "ghost", size: "sm" })}
            >
              All brands
            </Link>
          )}
          <Link
            href={
              includeArchived
                ? `/campaigns${brand ? `?brand=${brand.id}` : ""}`
                : `/campaigns?${brand ? `brand=${brand.id}&` : ""}archived=1`
            }
            aria-pressed={includeArchived}
            className={buttonVariants({ variant: includeArchived ? "secondary" : "outline", size: "sm" })}
          >
            <Archive className="size-3.5" aria-hidden="true" />
            {includeArchived ? "Hide archived" : "Show archived"}
          </Link>
          <NewCampaignDialog
            autoOpen={search.get("new") === "1"}
            defaultBrandId={brandId}
          />
        </>}
      />

      <CampaignTable
        campaigns={campaigns}
        brandNames={brandNames}
        paged={page > 1 || all.length > pageSize}
        empty={
          <EmptyState
            variant="inline"
            icon={Mail}
            title={includeArchived ? "Nothing here yet" : "No campaigns yet"}
            description={<>
              Describe your product once, then ask in your own words — “write me 3 emails
              that make people buy”. You get finished copy, reviewed for conversion before you
              see it.
            </>}
            action={<NewCampaignDialog />}
          />
        }
      />
      {(page > 1 || all.length > pageSize) && (
        <nav
          aria-label="Campaign pages"
          className="flex items-center justify-between gap-3 text-sm"
        >
          {page > 1 ? (
            <Link href={pageHref(page - 1)} className={buttonVariants({ variant: "outline", size: "sm" })}>
              <ChevronLeft className="size-3.5" aria-hidden="true" />
              Previous
            </Link>
          ) : (
            <span />
          )}
          <span className="text-xs text-muted-foreground tabular-nums">Page {page}</span>
          {all.length > pageSize ? (
            <Link href={pageHref(page + 1)} className={buttonVariants({ variant: "outline", size: "sm" })}>
              Next
              <ChevronRight className="size-3.5" aria-hidden="true" />
            </Link>
          ) : (
            <span />
          )}
        </nav>
      )}
    </div>
  );
      }}
    </PageData>
  );
}
