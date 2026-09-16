import Link from "next/link";
import { BrandSectionHeader } from "../../brand-ui";

import { AddKnowledgeDialog } from "@/app/knowledge/add-knowledge-dialog";
import { DeleteDocumentButton } from "@/app/knowledge/delete-document-button";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { api } from "@/lib/api-server";
import { formatAbsolute, timeAgo } from "@/lib/format";

/** The raw material one business is written from.
 *
 * Scoped to the brand rather than listed account-wide, because that is how the
 * compiler reads it: a source attached here is read by every campaign for this
 * brand and by no campaign for any other. A flat list of every document the
 * account holds hides exactly the thing that decides what the copy may say. */
export default async function BrandSourcesPage({
  params,
  searchParams,
}: {
  params: Promise<{ brandId: string }>;
  searchParams: Promise<{ page?: string }>;
}) {
  const { brandId } = await params;
  const query = await searchParams;
  const page = Math.max(1, Math.min(100000, Number.parseInt(query.page ?? "1", 10) || 1));

  const [rows, brand, base] = await Promise.all([
    api.listKnowledgeDocuments({ brandId }, { limit: 51, offset: (page - 1) * 50 }),
    api.getBrand(brandId),
    api.getKnowledgeBase({ brandId }).catch(() => null),
  ]);
  const documents = rows.slice(0, 50);

  return (
    <div className="space-y-4">
      <BrandSectionHeader title="Sources" description={`The pages, documents and screenshots behind ${brand.name}'s campaigns.`} actions={<>
          <Link
            href={`/brands/${brandId}/knowledge/base`}
            className={buttonVariants({ variant: "outline", size: "sm" })}
          >
            {base ? `Knowledge base — ${base.total} facts` : "Knowledge base"}
          </Link>
          <AddKnowledgeDialog brand={brand} />
        </>} />

      <Card>
        <CardContent className="p-0">
          {documents.length === 0 ? (
            <div className="space-y-2 p-6 text-sm text-muted-foreground">
              <p className="font-medium text-foreground">Nothing for this brand yet.</p>
              <p>
                Add its website so the copy uses its own words instead of guesses. Anything you
                add here is read on the next campaign run for this brand — and only for this one.
              </p>
            </div>
          ) : (
            <Table className="brand-source-table">
              <TableHeader>
                <TableRow>
                  <TableHead>Title</TableHead>
                  <TableHead>Source</TableHead>
                  <TableHead>Where it came from</TableHead>
                  <TableHead>Words</TableHead>
                  <TableHead>Added</TableHead>
                  <TableHead><span className="sr-only">Actions</span></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {documents.map((document) => (
                  <TableRow key={document.id}>
                    <TableCell data-label="Title" className="max-w-xs truncate font-medium">
                      {document.title}
                    </TableCell>
                    <TableCell data-label="Source">
                      <Badge variant="secondary">{document.source_type}</Badge>
                    </TableCell>
                    <TableCell data-label="Origin" className="max-w-xs truncate text-muted-foreground">
                      {document.source_url ?? "—"}
                    </TableCell>
                    <TableCell data-label="Words" className="text-muted-foreground tabular-nums">
                      {document.word_count}
                    </TableCell>
                    <TableCell
                      data-label="Added"
                      className="text-muted-foreground"
                      title={formatAbsolute(document.created_at)}
                    >
                      {timeAgo(document.created_at)}
                    </TableCell>
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
      <nav aria-label="Source pages" className="flex justify-between text-sm">
        {page > 1 ? <Link href={`?page=${page - 1}`}>Previous</Link> : <span />}
        <span>Page {page}</span>
        {rows.length > 50 ? <Link href={`?page=${page + 1}`}>Next</Link> : <span />}
      </nav>
    </div>
  );
}
