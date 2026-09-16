import Link from "next/link";
import { FolderOpen } from "lucide-react";

import { AddKnowledgeDialog } from "@/app/knowledge/add-knowledge-dialog";
import { DeleteDocumentButton } from "@/app/knowledge/delete-document-button";
import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";
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

/** Sources that belong to a single campaign rather than to a business.
 *
 * A brand's material lives in that brand's workspace, because that is the
 * scope the compiler reads it in. What is left here is the one-off: a campaign
 * run without a brand, whose knowledge is read once and then kept to it. The
 * two are listed apart on purpose - a flat list of every document the account
 * holds hides which campaigns can actually see each one. */
export default async function CampaignSourcesPage() {
  const [documents, campaigns] = await Promise.all([
    api.listKnowledgeDocuments(),
    api.listCampaigns().catch(() => []),
  ]);
  const oneOffs = documents.filter((document) => document.brand_id === null);
  const campaignNames = new Map(campaigns.map((campaign) => [campaign.id, campaign.name]));
  const withoutBrand = campaigns.filter((campaign) => campaign.brand_id === null);

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="One-off material"
        title="Campaign sources"
        description={<>
          Material attached to one campaign and read only by it. A business&rsquo;s own pages,
          documents and screenshots belong to its brand instead, where they are compiled once
          and reused by every campaign for it.
        </>}
        actions={<>
          <Link href="/brands" className={buttonVariants({ variant: "outline", size: "sm" })}>
            Brand knowledge
          </Link>
          <AddKnowledgeDialog campaigns={withoutBrand} />
        </>}
      />

      <Card>
        <CardContent className="p-0">
          {oneOffs.length === 0 ? (
            <EmptyState
              variant="inline"
              icon={FolderOpen}
              title="Nothing here — and that is the good outcome"
              description={<>
                Every source you have added belongs to a brand, which is the arrangement that
                pays off: the next campaign for that business starts from all of it.
              </>}
              action={
                <Link href="/brands" className={buttonVariants({ variant: "outline", size: "sm" })}>
                  Open a brand
                </Link>
              }
            />
          ) : (
            <Table className="stacked-table">
              <TableHeader>
                <TableRow>
                  <TableHead>Title</TableHead>
                  <TableHead>Source</TableHead>
                  <TableHead>Read by</TableHead>
                  <TableHead>Words</TableHead>
                  <TableHead />
                </TableRow>
              </TableHeader>
              <TableBody>
                {oneOffs.map((document) => (
                  <TableRow key={document.id}>
                    <TableCell className="max-w-xs truncate font-medium">
                      {document.title}
                    </TableCell>
                    <TableCell data-label="Source">
                      <Badge variant="secondary">{document.source_type}</Badge>
                    </TableCell>
                    <TableCell data-label="Read by" className="text-muted-foreground">
                      {document.campaign_id ? (
                        <Link
                          href={`/campaigns/${document.campaign_id}`}
                          className="hover:text-foreground hover:underline"
                        >
                          {campaignNames.get(document.campaign_id) ?? "Unknown campaign"}
                        </Link>
                      ) : (
                        <span title="Attached to neither a brand nor a campaign, so no run reads it">
                          Nothing
                        </span>
                      )}
                    </TableCell>
                    <TableCell data-label="Words" className="text-muted-foreground tabular-nums">
                      {document.word_count}
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
