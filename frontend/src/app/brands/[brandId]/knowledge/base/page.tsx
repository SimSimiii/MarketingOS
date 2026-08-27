import Link from "next/link";

import { KnowledgeBaseExplorer } from "./knowledge-base-explorer";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { api } from "@/lib/api-client";
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
            Knowledge is compiled on the first campaign run for this business — reading the
            material costs a model call, so it is not paid for until something needs it. Add its
            website and start a campaign, and this page fills in.
          </p>
          <div className="pt-2">
            <Link
              href={`/brands/${brandId}/knowledge`}
              className={buttonVariants({ variant: "outline", size: "sm" })}
            >
              Add sources
            </Link>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <p className="max-w-2xl text-sm text-muted-foreground">
        Everything we established about this business, on the shelf that matches the question a
        buyer is asking. This is the same index its copywriters work from — no other brand&rsquo;s
        facts are in it, and none of its facts are in theirs.
      </p>

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
            <p className="text-muted-foreground">
              Each of these is a sentence this brand&rsquo;s copy currently cannot write. Uploading
              the page that answers one is the cheapest improvement available to it.
            </p>
          </CardContent>
        </Card>
      )}

      <KnowledgeBaseExplorer base={base} />
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
