import Link from "next/link";

import { NewBrandDialog } from "@/app/brands/new-brand-dialog";
import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api-client";
import { timeAgo } from "@/lib/format";

/** The businesses this account works for.
 *
 * The entry point to everything scoped to one of them: its sources, its
 * compiled knowledge base, its market. None of those are account-wide - two
 * businesses have different competitors, different proof and different gaps,
 * and a page that averages them describes nobody.
 */
export default async function BrandsPage() {
  const brands = await api.listBrandOverviews();

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Your businesses" title="Brand workspaces" description="The knowledge, market context and proof behind every campaign. A dedicated home for each business." actions={<NewBrandDialog />} />

      {brands.length === 0 ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Register your first business</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-muted-foreground">
            <p>
              Knowledge attached to a brand is compiled once and reused by every campaign for it,
              instead of being recompiled from scratch each run. Its market is kept the same way:
              the competitors you curate and the proof you approve are still there for the fifth
              campaign.
            </p>
            <p>
              A one-off campaign can still run without one — it just keeps everything it learns to
              itself.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {brands.map((brand) => (
            <Card key={brand.id}>
              <CardHeader className="pb-3">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <CardTitle className="text-base">
                      <Link href={`/brands/${brand.id}`} className="hover:underline">
                        {brand.name}
                      </Link>
                    </CardTitle>
                    {brand.website_url && (
                      <p className="truncate text-sm text-muted-foreground">
                        {brand.website_url}
                      </p>
                    )}
                  </div>
                  <div className="flex shrink-0 gap-1">
                    {brand.unseen_alerts > 0 && (
                      <Badge variant="default">{brand.unseen_alerts} to act on</Badge>
                    )}
                    {brand.pending_proof > 0 && (
                      <Badge variant="outline">{brand.pending_proof} proof waiting</Badge>
                    )}
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <dl className="grid grid-cols-2 gap-4 rounded-xl border border-border bg-background/40 p-4 text-sm sm:grid-cols-4">
                  <Figure label="Sources" value={brand.sources} />
                  <Figure
                    label="Knowledge"
                    value={brand.knowledge_version ? `v${brand.knowledge_version}` : "—"}
                    hint={
                      brand.compiled_at
                        ? `compiled ${timeAgo(brand.compiled_at)}`
                        : "compiles on the first run"
                    }
                  />
                  <Figure
                    label="Competitors"
                    value={brand.rivals}
                    hint={brand.scanned_at ? `scanned ${timeAgo(brand.scanned_at)}` : "never scanned"}
                  />
                  <Figure label="Campaigns" value={brand.campaigns} />
                </dl>
                <div className="flex flex-wrap gap-2">
                  <Link
                    href={`/brands/${brand.id}`}
                    className={buttonVariants({ size: "sm" })}
                  >
                    Open workspace
                  </Link>
                  <Link
                    href={`/brands/${brand.id}/knowledge/base`}
                    className={buttonVariants({ variant: "outline", size: "sm" })}
                  >
                    Knowledge base
                  </Link>
                  <Link
                    href={`/brands/${brand.id}/market`}
                    className={buttonVariants({ variant: "outline", size: "sm" })}
                  >
                    Market
                  </Link>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

function Figure({
  label,
  value,
  hint,
}: {
  label: string;
  value: number | string;
  hint?: string;
}) {
  return (
    <div>
      <dd className="text-xl font-semibold tabular-nums">{value}</dd>
      <dt className="text-xs text-muted-foreground">{label}</dt>
      {hint && <p className="text-xs text-muted-foreground/70">{hint}</p>}
    </div>
  );
}
