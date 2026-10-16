"use client";

import Link from "next/link";
import { ChevronLeft, ChevronRight, FileText, Globe, Image as ImageIcon, Files } from "lucide-react";
import { BrandSectionHeader } from "../../brand-ui";
import { EmptyState } from "@/components/empty-state";

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
import { api, nullIfMissing } from "@/lib/api-client";
import { formatAbsolute, timeAgo } from "@/lib/format";

/** The raw material one business is written from.
 *
 * Scoped to the brand rather than listed account-wide, because that is how the
 * compiler reads it: a source attached here is read by every campaign for this
 * brand and by no campaign for any other. A flat list of every document the
 * account holds hides exactly the thing that decides what the copy may say. */
import { PageData, usePageData, useRouteIds } from "@/lib/page-data";
import { useSearchParams } from "next/navigation";

export function BrandSourcesView() {
  const { brandId } = useRouteIds();
  const search = useSearchParams();
  const page = Math.max(1, Math.min(100000, Number.parseInt(search.get("page") ?? "1", 10) || 1));
  const state = usePageData(async () => {

  const [rows, brand, base] = await Promise.all([
    api.listKnowledgeDocuments({ brandId }, { limit: 51, offset: (page - 1) * 50 }),
    api.getBrand(brandId),
    api.getKnowledgeBase({ brandId }).catch(nullIfMissing),
  ]);
  return { rows, brand, base };
  }, [brandId, page]);

  return (
    <PageData state={state}>
      {({ rows, brand, base }) => {

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

      <Card className="gap-0 py-0">
        <CardContent className="p-0">
          {documents.length === 0 ? (
            <EmptyState
              variant="inline"
              icon={Files}
              title="Nothing for this brand yet"
              description="Add its website so the copy uses its own words instead of guesses. Anything you add here is read on the next campaign run for this brand — and only for this one."
              action={<AddKnowledgeDialog brand={brand} />}
            />
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
                    <TableCell data-label="Title" className="max-w-xs font-medium">
                      <span className="flex min-w-0 items-center gap-3">
                        <span className="hidden size-8 shrink-0 items-center justify-center rounded-lg border border-white/[0.07] bg-white/[0.03] text-violet-300 md:flex">
                          <SourceIcon type={document.source_type} />
                        </span>
                        <span className="truncate">{document.title}</span>
                      </span>
                    </TableCell>
                    <TableCell data-label="Source">
                      <Badge variant="secondary">{document.source_type.replace("_", " ")}</Badge>
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
      {(page > 1 || rows.length > 50) && (
        <nav aria-label="Source pages" className="flex items-center justify-between gap-3 text-sm">
          {page > 1 ? (
            <Link href={`?page=${page - 1}`} className={buttonVariants({ variant: "outline", size: "sm" })}>
              <ChevronLeft aria-hidden="true" />
              Previous
            </Link>
          ) : <span />}
          <span className="text-xs text-muted-foreground tabular-nums">Page {page}</span>
          {rows.length > 50 ? (
            <Link href={`?page=${page + 1}`} className={buttonVariants({ variant: "outline", size: "sm" })}>
              Next
              <ChevronRight aria-hidden="true" />
            </Link>
          ) : <span />}
        </nav>
      )}
    </div>
  );
      }}
    </PageData>
  );
}

/** What kind of thing a source is, at a glance: a page, a picture, a file. */
function SourceIcon({ type }: { type: string }) {
  const kind = type.toLowerCase();
  if (kind.includes("url") || kind.includes("web") || kind.includes("page")) {
    return <Globe className="size-4" aria-hidden="true" />;
  }
  if (kind.includes("image") || kind.includes("screenshot")) {
    return <ImageIcon className="size-4" aria-hidden="true" />;
  }
  return <FileText className="size-4" aria-hidden="true" />;
}
