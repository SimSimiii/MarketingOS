import Link from "next/link";

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
import { api } from "@/lib/api-client";
import { formatAbsolute, timeAgo } from "@/lib/format";

/** The raw material one business is written from.
 *
 * Scoped to the brand rather than listed account-wide, because that is how the
 * compiler reads it: a source attached here is read by every campaign for this
 * brand and by no campaign for any other. A flat list of every document the
 * account holds hides exactly the thing that decides what the copy may say. */
export default async function BrandSourcesPage({
  params,
}: {
  params: Promise<{ brandId: string }>;
}) {
  const { brandId } = await params;

  const [documents, brand, base] = await Promise.all([
    api.listKnowledgeDocuments({ brandId }),
    api.getBrand(brandId),
    api.getKnowledgeBase({ brandId }).catch(() => null),
  ]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <p className="max-w-xl text-sm text-muted-foreground">
          Everything the copywriters read before they write for {brand.name}: its pages,
          documents and screenshots. Compiled once and reused by every campaign for this brand.
        </p>
        <div className="flex flex-wrap items-center gap-2">
          <Link
            href={`/brands/${brandId}/knowledge/base`}
            className={buttonVariants({ variant: "outline", size: "sm" })}
          >
            {base ? `Knowledge base — ${base.total} facts` : "Knowledge base"}
          </Link>
          <AddKnowledgeDialog brand={brand} />
        </div>
      </div>

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
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Title</TableHead>
                  <TableHead>Source</TableHead>
                  <TableHead>Where it came from</TableHead>
                  <TableHead>Words</TableHead>
                  <TableHead>Added</TableHead>
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
                    <TableCell className="max-w-xs truncate text-muted-foreground">
                      {document.source_url ?? "—"}
                    </TableCell>
                    <TableCell className="text-muted-foreground tabular-nums">
                      {document.word_count}
                    </TableCell>
                    <TableCell
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
    </div>
  );
}
