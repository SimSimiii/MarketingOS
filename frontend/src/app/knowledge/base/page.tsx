import Link from "next/link";

import { KnowledgeBaseExplorer } from "@/app/knowledge/base/knowledge-base-explorer";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { api } from "@/lib/api-client";
import { formatAbsolute } from "@/lib/format";
import type { Brand } from "@/lib/types";

/** The knowledge base for one business: every fact the compiler established,
 * filed on the shelf that matches the question a buyer would be asking, and
 * priced by what it is worth to a sale.
 *
 * The same index the agents plan and write from. Nothing here is a separate
 * copy for humans - if a fact is missing from this page, the copywriters do
 * not have it either, which is what makes the empty shelf actionable. */
export default async function KnowledgeBasePage({
  searchParams,
}: {
  searchParams: Promise<{ brand?: string; campaign?: string }>;
}) {
  const { brand: brandId, campaign: campaignId } = await searchParams;
  const brands = await api.listBrands().catch(() => []);

  if (!brandId && !campaignId) {
    return <BrandPicker brands={brands} />;
  }

  const base = await api
    .getKnowledgeBase({ brandId, campaignId })
    .catch(() => null);
  const brand = brands.find((item) => item.id === brandId);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            Knowledge base{brand ? ` — ${brand.name}` : ""}
          </h1>
          <p className="text-sm text-muted-foreground">
            Everything we established about this business, on the shelf that matches the question
            a buyer is asking. This is the same index the copywriters work from.
          </p>
        </div>
        <Link href="/knowledge" className={buttonVariants({ variant: "outline", size: "sm" })}>
          Back to sources
        </Link>
      </div>

      {base === null ? (
        <Card>
          <CardContent className="space-y-2 p-6 text-sm text-muted-foreground">
            <p className="font-medium text-foreground">Nothing compiled here yet.</p>
            <p>
              Knowledge is compiled on the first campaign run for this business — reading the
              material costs a model call, so it is not paid for until something needs it. Add
              your website and start a campaign, and this page fills in.
            </p>
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="flex flex-wrap gap-3">
            <Stat label="Facts established" value={base.total} />
            <Stat
              label="Citable in copy"
              value={base.citable_total}
              hint="Only these carry an id a copywriter may quote — the rest is context."
            />
            <Stat
              label="Strong enough to lead"
              value={base.headline_total}
              hint="Specific, attributed, and checkable by a stranger."
            />
            <Stat label="Compiled" value={`v${base.version}`} hint={
              base.compiled_at ? formatAbsolute(base.compiled_at) : undefined
            } />
          </div>

          {base.open_questions.length > 0 && (
            <Card className="border-amber-500/40">
              <CardContent className="space-y-2 p-4 text-sm">
                <p className="font-medium">
                  Still unanswered
                  <Badge variant="outline" className="ml-2">
                    {base.open_questions.length}
                  </Badge>
                </p>
                <ul className="list-disc space-y-1 pl-5 text-muted-foreground">
                  {base.open_questions.map((question) => (
                    <li key={question}>{question}</li>
                  ))}
                </ul>
                <p className="text-muted-foreground">
                  Each of these is a sentence the copy currently cannot write. Uploading the page
                  that answers one is the cheapest improvement available to this account.
                </p>
              </CardContent>
            </Card>
          )}

          <KnowledgeBaseExplorer base={base} />
        </>
      )}
    </div>
  );
}

function Stat({
  label,
  value,
  hint,
}: {
  label: string;
  value: number | string;
  hint?: string;
}) {
  return (
    <Card className="min-w-40 flex-1">
      <CardContent className="p-4">
        <p className="text-2xl font-semibold tabular-nums">{value}</p>
        <p className="text-sm text-muted-foreground">{label}</p>
        {hint && <p className="mt-1 text-xs text-muted-foreground/80">{hint}</p>}
      </CardContent>
    </Card>
  );
}

function BrandPicker({ brands }: { brands: Brand[] }) {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Knowledge base</h1>
        <p className="text-sm text-muted-foreground">
          Pick a business to read what we know about it.
        </p>
      </div>
      {brands.length === 0 ? (
        <Card>
          <CardContent className="p-6 text-sm text-muted-foreground">
            No brands yet. Register one on{" "}
            <Link href="/knowledge" className="underline underline-offset-2">
              Product knowledge
            </Link>{" "}
            and its knowledge base appears here after the first campaign run.
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {brands.map((brand) => (
            <Card key={brand.id}>
              <CardContent className="space-y-2 p-4">
                <p className="font-medium">{brand.name}</p>
                {brand.website_url && (
                  <p className="truncate text-sm text-muted-foreground">{brand.website_url}</p>
                )}
                <Link
                  href={`/knowledge/base?brand=${brand.id}`}
                  className={buttonVariants({ variant: "outline", size: "sm" })}
                >
                  Open knowledge base
                </Link>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
