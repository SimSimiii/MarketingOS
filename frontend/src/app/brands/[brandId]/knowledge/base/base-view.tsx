"use client";

import Link from "next/link";
import { BrandDisclosure, BrandSectionHeader } from "../../../brand-ui";
import { StatTile } from "@/components/stat-tile";

import { BookOpen, CheckCircle2, Crown, History, Quote } from "lucide-react";

import { KnowledgeBaseExplorer } from "./knowledge-base-explorer";
import { CompileButton } from "./compile-button";
import { EmptyState } from "@/components/empty-state";
import { buttonVariants } from "@/components/ui/button";
import { api, nullIfMissing } from "@/lib/api-client";
import { formatAbsolute } from "@/lib/format";

/** The knowledge base for one business: every fact the compiler established,
 * filed on the shelf that matches the question a buyer would be asking, and
 * priced by what it is worth to a sale.
 *
 * The same index the agents plan and write from. Nothing here is a separate
 * copy for humans - if a fact is missing from this page, the copywriters do
 * not have it either, which is what makes the empty shelf actionable. */
import { PageData, usePageData, useRouteIds } from "@/lib/page-data";

export function BrandKnowledgeBaseView() {
  const { brandId } = useRouteIds();
  const state = usePageData(async () => {
  const base = await api.getKnowledgeBase({ brandId }).catch(nullIfMissing);
  return { base };
  }, [brandId]);

  return (
    <PageData state={state}>
      {({ base }) => {


  if (base === null) {
    return (
      <div className="space-y-4">
        <BrandSectionHeader title="Knowledge base" description="The facts and evidence your campaigns can draw on, organised by buyer question." />
        <EmptyState
          icon={BookOpen}
          title="Nothing compiled for this brand yet"
          description="Add this business's sources, then compile them here to prepare the knowledge used by every campaign."
          action={
            <div className="flex flex-col items-center gap-4">
              <Link
                href={`/brands/${brandId}/knowledge`}
                className={buttonVariants({ variant: "outline", size: "sm" })}
              >
                Add sources
              </Link>
              <CompileButton brandId={brandId} compiled={false} />
            </div>
          }
        />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <BrandSectionHeader title="Knowledge base" description="The facts and evidence your campaigns can draw on, organised by buyer question." actions={<CompileButton brandId={brandId} compiled />} />

      <div className="rise-stagger grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-4">
        <StatTile label="Facts established" value={base.total} icon={CheckCircle2} hint="Everything the compiler could stand behind." />
        <StatTile
          label="Citable in copy"
          value={base.citable_total}
          icon={Quote}
          hint="Only these carry an id a copywriter may quote — the rest is context."
        />
        <StatTile
          label="Strong enough to lead"
          value={base.headline_total}
          icon={Crown}
          hint="Specific, attributed, and checkable by a stranger."
        />
        <StatTile
          label="Compiled"
          value={`v${base.version}`}
          icon={History}
          hint={base.compiled_at ? formatAbsolute(base.compiled_at) : undefined}
        />
      </div>

      {base.open_questions.length > 0 && (
        <BrandDisclosure title={`${base.open_questions.length} unanswered questions`} description="Add sources that answer these questions to strengthen your copy." className="shadow-[var(--shadow-surface),0_0_0_1px_oklch(0.8_0.15_80/25%)]">
          <ul className="list-disc space-y-2 pl-5 text-sm leading-relaxed text-muted-foreground">{base.open_questions.map((question) => <li key={question}>{question}</li>)}</ul>
        </BrandDisclosure>
      )}

      <KnowledgeBaseExplorer base={base} />
    </div>
  );
      }}
    </PageData>
  );
}
