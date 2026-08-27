import { redirect } from "next/navigation";

import { KnowledgeBaseExplorer } from "@/app/brands/[brandId]/knowledge/base/knowledge-base-explorer";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { api } from "@/lib/api-client";
import { formatAbsolute } from "@/lib/format";

/** A one-off campaign's knowledge base.
 *
 * A brand's base moved into that brand's workspace, where the rest of what
 * belongs to it lives, so `?brand=` redirects there. What is left is the case
 * that has no brand to move into: a campaign that was run without one and
 * keeps its knowledge to itself. */
export default async function KnowledgeBasePage({
  searchParams,
}: {
  searchParams: Promise<{ brand?: string; campaign?: string }>;
}) {
  const { brand: brandId, campaign: campaignId } = await searchParams;

  if (brandId) {
    redirect(`/brands/${brandId}/knowledge/base`);
  }
  if (!campaignId) {
    redirect("/brands");
  }

  const [base, campaign] = await Promise.all([
    api.getKnowledgeBase({ campaignId }).catch(() => null),
    api.getCampaign(campaignId).catch(() => null),
  ]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">
          Knowledge base{campaign ? ` — ${campaign.name}` : ""}
        </h1>
        <p className="text-sm text-muted-foreground">
          Everything this one-off campaign established, kept to itself. Attach it to a brand
          instead and the next campaign starts from all of it rather than from an empty page.
        </p>
      </div>

      {base === null ? (
        <Card>
          <CardContent className="space-y-2 p-6 text-sm text-muted-foreground">
            <p className="font-medium text-foreground">Nothing compiled here yet.</p>
            <p>
              Knowledge is compiled on the first run — reading the material costs a model call, so
              it is not paid for until something needs it.
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
            <Stat
              label="Compiled"
              value={`v${base.version}`}
              hint={base.compiled_at ? formatAbsolute(base.compiled_at) : undefined}
            />
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
