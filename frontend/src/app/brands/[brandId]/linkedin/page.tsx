import { api } from "@/lib/api-server";
import { PageHeader } from "@/components/page-header";
import { LinkedInWorkspace } from "./linkedin-workspace";

export default async function LinkedInPage({ params }: { params: Promise<{ brandId: string }> }) {
  const { brandId } = await params;
  //: The audience map is what makes the criteria step worth having - it is
  //: the one description of this brand's buyer that did not come from the
  //: brand's own marketing. A brand nobody has mapped still works: the
  //: proposal falls back to the knowledge base.
  const [runs, audience] = await Promise.all([
    api.listLinkedInRuns(brandId),
    api.getAudience(brandId).catch(() => null),
  ]);
  return <div className="space-y-6">
    <PageHeader
      eyebrow="Prospecting"
      title="LinkedIn"
      description="Work out who is worth writing to, then find them. Writing to one of them is a campaign."
    />
    <LinkedInWorkspace
      key={brandId}
      brandId={brandId}
      initialRuns={runs}
      segments={audience?.map?.segments ?? []}
    />
  </div>;
}
