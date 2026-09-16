import Link from "next/link";
import { BrandDisclosure, BrandSectionHeader } from "../../../brand-ui";
import { StatTile } from "@/components/stat-tile";

import { KnowledgeBaseExplorer } from "./knowledge-base-explorer";
import { CompileButton } from "./compile-button";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { api } from "@/lib/api-server";
import { formatAbsolute } from "@/lib/format";

/** The knowledge base for one business: every fact the compiler established,
 * filed on the shelf that matches the question a buyer would be asking, and
 * priced by what it is worth to a sale.
 *
 * The same index the agents plan and write from. Nothing here is a separate
 * copy for humans - if a fact is missing from this page, the copywriters do
 * not have it either, which is what makes the empty shelf actionable. */
export default async function BrandKnowledgeBasePage({
  params,
}: {
  params: Promise<{ brandId: string }>;
}) {
  const { brandId } = await params;
  const base = await api.getKnowledgeBase({ brandId }).catch(() => null);

  if (base === null) {
    return (
      <Card>
        <CardContent className="space-y-2 p-6 text-sm text-muted-foreground">
          <p className="font-medium text-foreground">Nothing compiled for this brand yet.</p>
          <p>
            Add this business&apos;s sources, then compile them here to prepare the knowledge
            used by every campaign.
          </p>
          <div className="pt-2">
            <Link
              href={`/brands/${brandId}/knowledge`}
              className={buttonVariants({ variant: "outline", size: "sm" })}
            >
              Add sources
            </Link>
          </div>
          <CompileButton brandId={brandId} compiled={false} />
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <BrandSectionHeader title="Knowledge base" description="The facts and evidence your campaigns can draw on, organised by buyer question." actions={<CompileButton brandId={brandId} compiled />} />

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <StatTile label="Facts established" value={base.total} />
        <StatTile
          label="Citable in copy"
          value={base.citable_total}
          hint="Only these carry an id a copywriter may quote — the rest is context."
        />
        <StatTile
          label="Strong enough to lead"
          value={base.headline_total}
          hint="Specific, attributed, and checkable by a stranger."
        />
        <StatTile
          label="Compiled"
          value={`v${base.version}`}
          hint={base.compiled_at ? formatAbsolute(base.compiled_at) : undefined}
        />
      </div>

      {base.open_questions.length > 0 && (
        <BrandDisclosure title={`${base.open_questions.length} unanswered questions`} description="Add sources that answer these questions to strengthen your copy." className="border-amber-500/30">
          <ul className="list-disc space-y-2 pl-5 text-sm leading-relaxed text-muted-foreground">{base.open_questions.map((question) => <li key={question}>{question}</li>)}</ul>
        </BrandDisclosure>
      )}

      <KnowledgeBaseExplorer base={base} />
    </div>
  );
}
