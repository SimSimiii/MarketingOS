"use client";

import { BookOpen } from "lucide-react";

import { KnowledgeBaseExplorer } from "@/app/brands/[brandId]/knowledge/base/knowledge-base-explorer";
import { EmptyState } from "@/components/empty-state";
import { Notice } from "@/components/notice";
import { PageHeader } from "@/components/page-header";
import { StatTile } from "@/components/stat-tile";
import { api, nullIfMissing } from "@/lib/api-client";
import { formatAbsolute } from "@/lib/format";

/** A one-off campaign's knowledge base.
 *
 * A brand's base moved into that brand's workspace, where the rest of what
 * belongs to it lives, so `?brand=` redirects there. What is left is the case
 * that has no brand to move into: a campaign that was run without one and
 * keeps its knowledge to itself. */
import { PageData, redirect, usePageData } from "@/lib/page-data";
import { useSearchParams } from "next/navigation";

export function KnowledgeBaseView() {
  const search = useSearchParams();
  const brandId = search.get("brand") ?? undefined;
  const campaignId = search.get("campaign") ?? undefined;
  const state = usePageData(async () => {

  if (brandId) {
    redirect(`/brands/${brandId}/knowledge/base`);
  }
  if (!campaignId) {
    redirect("/brands");
  }

  const [base, campaign] = await Promise.all([
    api.getKnowledgeBase({ campaignId }).catch(nullIfMissing),
    api.getCampaign(campaignId).catch(nullIfMissing),
  ]);
  return { base, campaign };
  }, [brandId, campaignId]);

  return (
    <PageData state={state}>
      {({ base, campaign }) => {


  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="One-off campaign"
        title={`Knowledge base${campaign ? ` — ${campaign.name}` : ""}`}
        description="Everything this one-off campaign established, kept to itself. Attach it to a brand instead and the next campaign starts from all of it rather than from an empty page."
        backTo={
          campaign
            ? { href: `/campaigns/${campaign.id}`, label: campaign.name }
            : { href: "/campaigns", label: "Campaigns" }
        }
      />

      {base === null ? (
        <EmptyState
          icon={BookOpen}
          title="Nothing compiled here yet"
          description="Your material is prepared on the first run, then reused while it stays the same."
        />
      ) : (
        <>
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
            <Notice
              tone="warning"
              title={`Still unanswered · ${base.open_questions.length}`}
            >
              <ul className="list-disc space-y-1 pl-5">
                {base.open_questions.map((question) => (
                  <li key={question}>{question}</li>
                ))}
              </ul>
            </Notice>
          )}

          <KnowledgeBaseExplorer base={base} />
        </>
      )}
    </div>
  );
      }}
    </PageData>
  );
}
