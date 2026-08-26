import Link from "next/link";

import { AddKnowledgeDialog } from "@/app/knowledge/add-knowledge-dialog";
import { BrandKnowledgeDialog } from "@/app/knowledge/brand-knowledge-dialog";
import { DeleteDocumentButton } from "@/app/knowledge/delete-document-button";
import { NewBrandDialog } from "@/app/knowledge/new-brand-dialog";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { api } from "@/lib/api-client";
import type { Brand, BrandKnowledge } from "@/lib/types";

export default async function KnowledgePage() {
  const [documents, campaigns, brands] = await Promise.all([
    api.listKnowledgeDocuments(),
    api.listCampaigns().catch(() => []),
    api.listBrands().catch(() => []),
  ]);
  const campaignNames = new Map(campaigns.map((campaign) => [campaign.id, campaign.name]));
  const brandNames = new Map(brands.map((brand) => [brand.id, brand.name]));
  const brandKnowledge = new Map<string, BrandKnowledge>(
    (
      await Promise.all(
        brands.map(async (brand) => {
          const knowledge = await api.getBrandKnowledge(brand.id).catch(() => null);
          return [brand.id, knowledge] as const;
        }),
      )
    ).filter((entry): entry is [string, BrandKnowledge] => entry[1] !== null),
  );

  function locationLabel(document: { campaign_id: string | null; brand_id: string | null }) {
    if (document.brand_id) return brandNames.get(document.brand_id) ?? "Unknown brand";
    if (document.campaign_id) return campaignNames.get(document.campaign_id) ?? "—";
    return "Unattached";
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Product knowledge</h1>
          <p className="text-sm text-muted-foreground">
            Everything the copywriters read before they write: your pages, documents and
            screenshots.
          </p>
        </div>
        <div className="flex gap-2">
          <NewBrandDialog />
          <AddKnowledgeDialog campaigns={campaigns} brands={brands} />
        </div>
      </div>

      <div className="space-y-2">
        <h2 className="text-sm font-medium text-muted-foreground">Brands</h2>
        {brands.length === 0 ? (
          <Card>
            <CardContent className="p-6 text-sm text-muted-foreground">
              No brands yet. Register one so a campaign can reuse compiled knowledge instead of
              paying to recompile it every run.
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {brands.map((brand: Brand) => {
              const knowledge = brandKnowledge.get(brand.id);
              const docCount = documents.filter((d) => d.brand_id === brand.id).length;
              return (
                <Card key={brand.id}>
                  <CardHeader>
                    <CardTitle className="text-base">{brand.name}</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-1 text-sm text-muted-foreground">
                    <p>
                      {docCount} source{docCount === 1 ? "" : "s"}
                    </p>
                    {knowledge ? (
                      <>
                        <p>
                          Compiled v{knowledge.version} - {knowledge.evidence_count} fact
                          {knowledge.evidence_count === 1 ? "" : "s"} to cite
                        </p>
                        {knowledge.gaps.length > 0 && (
                          <p className="text-amber-600 dark:text-amber-500">
                            {knowledge.gaps.length} gap{knowledge.gaps.length === 1 ? "" : "s"}{" "}
                            still unanswered
                          </p>
                        )}
                        <div className="flex flex-wrap gap-2 pt-1">
                          <Link
                            href={`/knowledge/base?brand=${brand.id}`}
                            className={buttonVariants({ variant: "outline", size: "sm" })}
                          >
                            Knowledge base
                          </Link>
                          <BrandKnowledgeDialog brandId={brand.id} brandName={brand.name} />
                        </div>
                      </>
                    ) : (
                      <p>Not compiled yet - happens on the first campaign run.</p>
                    )}
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </div>

      <Card>
        <CardContent className="p-0">
          {documents.length === 0 ? (
            <p className="p-6 text-sm text-muted-foreground">
              Nothing yet. Add your website so the copy uses your own words instead of guesses.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Title</TableHead>
                  <TableHead>Source</TableHead>
                  <TableHead>Saved to</TableHead>
                  <TableHead>Words</TableHead>
                  <TableHead />
                </TableRow>
              </TableHeader>
              <TableBody>
                {documents.map((document) => (
                  <TableRow key={document.id}>
                    <TableCell className="max-w-xs truncate font-medium">
                      {document.title}
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary">{document.source_type}</Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {document.brand_id && <Badge variant="outline">Brand</Badge>}{" "}
                      {locationLabel(document)}
                    </TableCell>
                    <TableCell className="text-muted-foreground">{document.word_count}</TableCell>
                    <TableCell className="text-right">
                      <DeleteDocumentButton documentId={document.id} />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
