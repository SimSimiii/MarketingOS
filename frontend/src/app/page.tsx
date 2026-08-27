import Link from "next/link";

import { NewCampaignDialog } from "@/app/campaigns/new-campaign-dialog";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api-client";

const STEPS = [
  {
    title: "1. Describe your product",
    body: "Drop in your website, a PDF or a screenshot of your landing page. We read them - no summarising, no guessing.",
  },
  {
    title: "2. Ask for what you need",
    body: "In your own words: “write me 3 emails that make people buy”. That sentence is the brief.",
  },
  {
    title: "3. Copy and send",
    body: "Researched, written, then reviewed for conversion before you ever see it. Finished copy, not drafts.",
  },
];

export default async function DashboardPage() {
  const [campaigns, documents, brands] = await Promise.all([
    api.listCampaigns().catch(() => []),
    api.listKnowledgeDocuments().catch(() => []),
    api.listBrandOverviews().catch(() => []),
  ]);
  // What is waiting for a person, summed across businesses but never merged
  // into one: each number belongs to a brand, and the link goes to the list
  // that says which.
  const waiting = brands.reduce(
    (total, brand) => total + brand.pending_proof + brand.unseen_alerts,
    0,
  );

  return (
    <div className="space-y-8">
      <div className="flex items-start justify-between gap-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            Marketing copy, without hiring a copywriter
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Tell MarketingOS about your product and what you need. It researches, writes and
            reviews - you copy and paste.
          </p>
        </div>
        <NewCampaignDialog />
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        {STEPS.map((step) => (
          <Card key={step.title}>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">{step.title}</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">{step.body}</CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <Link href="/brands" className="block">
          <Card className="h-full transition-colors hover:bg-accent/40">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Brands</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-semibold">{brands.length}</p>
              <p className="mt-1 text-xs text-muted-foreground">
                {waiting > 0
                  ? `${waiting} thing${waiting === 1 ? "" : "s"} waiting for you across them`
                  : "Each with its own knowledge base and market"}
              </p>
            </CardContent>
          </Card>
        </Link>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Campaigns</CardTitle>
          </CardHeader>
          <CardContent className="text-3xl font-semibold">{campaigns.length}</CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Knowledge sources
            </CardTitle>
          </CardHeader>
          <CardContent className="text-3xl font-semibold">{documents.length}</CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Recent campaigns</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {campaigns.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Nothing yet. Start with what you need - three emails is a good first ask.
            </p>
          ) : (
            campaigns.slice(0, 5).map((campaign) => (
              <Link
                key={campaign.id}
                href={`/campaigns/${campaign.id}`}
                className="block rounded-md border border-border px-4 py-3 transition-colors hover:bg-accent/40"
              >
                <p className="font-medium">{campaign.name}</p>
                <p className="truncate text-sm text-muted-foreground">{campaign.request}</p>
              </Link>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}
