import Link from "next/link";
import { AlertTriangle, ArrowRight, BookOpen, Building2, CloudOff, Mail, Plus, Sparkles } from "lucide-react";
import { NewCampaignDialog } from "@/app/campaigns/new-campaign-dialog";
import { EmptyState } from "@/components/empty-state";
import { Notice } from "@/components/notice";
import { PageHeader } from "@/components/page-header";
import { StatTile } from "@/components/stat-tile";
import { StatusBadge } from "@/components/status-badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api-server";
import { formatAbsolute, timeAgo } from "@/lib/format";

const STEPS = [
  { title: "Give it the facts", body: "Add your website, documents and product details to a brand workspace.", href: "/brands", icon: Building2 },
  { title: "Set the direction", body: "Describe your audience and what you want your emails to achieve.", href: "/campaigns", icon: Mail },
  { title: "Make it yours", body: "Review the finished emails, copy the text and send through your email platform.", href: "/campaigns", icon: Sparkles },
];

export default async function DashboardPage() {
  const [campaignResult, documentResult, brandResult] = await Promise.allSettled([
    api.listCampaigns(), api.listKnowledgeDocuments(), api.listBrandOverviews(),
  ]);
  const campaigns = campaignResult.status === "fulfilled" ? campaignResult.value : null;
  const documents = documentResult.status === "fulfilled" ? documentResult.value : null;
  const brands = brandResult.status === "fulfilled" ? brandResult.value : null;
  const waiting = brands?.reduce((total, brand) => total + brand.pending_proof + brand.unseen_alerts, 0);
  const stats = [
    { label: "Brand workspaces", value: brands?.length, hint: "Knowledge, positioning and proof", href: "/brands", icon: Building2 },
    { label: "Campaigns", value: campaigns?.length, hint: "From your brief to finished copy", href: "/campaigns", icon: Mail },
    { label: "Campaign sources", value: documents?.length, hint: "Material attached to individual campaigns", href: "/knowledge", icon: BookOpen },
  ];

  return (
    <div className="space-y-8">
      <PageHeader eyebrow="Your email studio" title="A clearer path to better copy." description="Your businesses, your campaigns and your next move. All in one place." actions={<NewCampaignDialog />} />
      <section className="studio-hero relative overflow-hidden rounded-2xl border border-violet-400/15 p-6 sm:p-8">
        <div className="flex flex-wrap items-center justify-between gap-8">
          <div className="max-w-xl">
            <p className="mb-4 flex items-center gap-2 text-xs font-medium text-violet-300"><Sparkles className="size-4" aria-hidden="true" /> GROUNDED IN YOUR BUSINESS</p>
            <h2 className="text-2xl font-medium leading-tight tracking-tight sm:text-3xl">Your expertise.<br /><span className="text-muted-foreground">Ready for their inbox.</span></h2>
            <p className="mt-4 max-w-md text-sm leading-relaxed text-muted-foreground">Turn what makes your product valuable into emails that explain it clearly. Researched, written and reviewed before you send.</p>
          </div>
          <Link href="/brands" className="group flex items-center gap-4 rounded-xl border border-white/10 bg-background/40 p-5 transition-colors hover:border-violet-400/40">
            <span className="flex size-10 items-center justify-center rounded-full bg-violet-500/15 text-violet-300"><Plus className="size-5" aria-hidden="true" /></span>
            <span><span className="block text-sm font-medium">Build your foundation</span><span className="mt-1 block text-xs text-muted-foreground">Open your brand workspaces</span></span>
            <ArrowRight className="size-4 text-violet-300" aria-hidden="true" />
          </Link>
        </div>
      </section>
      {(campaigns === null || documents === null || brands === null) && (
        <Notice tone="warning" title="Some workspace data could not be loaded">
          Refresh to try again. Unavailable counts are shown as a dash.
        </Notice>
      )}
      <div className="rise-stagger grid gap-4 sm:grid-cols-3">
        {stats.map(({ label, value, hint, href, icon }) => (
          <StatTile key={href} label={label} value={value ?? "—"} hint={hint} href={href} icon={icon} />
        ))}
      </div>
      {waiting !== undefined && waiting > 0 && (
        <Link
          href="/brands"
          className="group flex items-center justify-between gap-4 rounded-xl border border-amber-400/25 bg-amber-400/5 p-4 text-sm text-amber-200 transition-colors hover:border-amber-400/50 hover:bg-amber-400/10"
        >
          <span className="flex items-center gap-3">
            <AlertTriangle className="size-4 shrink-0" aria-hidden="true" />
            {waiting} market alert{waiting === 1 ? " or proof item needs" : "s or proof items need"} your review
          </span>
          <ArrowRight
            className="size-4 shrink-0 transition-transform group-hover:translate-x-0.5"
            aria-hidden="true"
          />
        </Link>
      )}
      <div className="grid items-start gap-6 xl:grid-cols-[minmax(0,1fr)_300px]">
        <Card className="gap-0 py-0">
          <CardHeader className="flex flex-row items-center justify-between border-b p-5"><CardTitle>Recent campaigns</CardTitle><Link href="/campaigns" className="flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground">View all<ArrowRight className="size-3.5" aria-hidden="true" /></Link></CardHeader>
          <CardContent className="p-0">
            {campaigns === null ? (
              <EmptyState
                variant="inline"
                icon={CloudOff}
                title="Campaigns are temporarily unavailable"
                description="The API did not answer. Nothing has been lost — reload the page to try again."
              />
            ) : campaigns.length === 0 ? (
              <EmptyState
                variant="inline"
                icon={Mail}
                title="Your next campaign starts here"
                description="Start with a simple brief. A welcome sequence, a product launch, a reason to come back."
                action={<NewCampaignDialog />}
              />
            ) : <div className="divide-y divide-border">{campaigns.slice(0, 5).map((campaign) => (
              <Link key={campaign.id} href={`/campaigns/${campaign.id}`} className="group/row flex items-center gap-4 p-5 transition-colors hover:bg-accent/20">
                <span className="hidden size-10 shrink-0 items-center justify-center rounded-lg border border-border bg-background/40 text-violet-300 sm:flex"><Mail className="size-4" aria-hidden="true" /></span>
                <div className="min-w-0 flex-1"><p className="truncate text-sm font-medium">{campaign.name}</p><p className="mt-1 truncate text-xs text-muted-foreground">{campaign.request}</p><p className="mt-2 text-[11px] text-muted-foreground" title={formatAbsolute(campaign.created_at)}>{timeAgo(campaign.created_at)}</p></div>
                {campaign.last_run_status && <StatusBadge status={campaign.last_run_status} />}<ArrowRight className="size-4 shrink-0 text-muted-foreground transition-transform group-hover/row:translate-x-0.5 group-hover/row:text-violet-300" aria-hidden="true" />
              </Link>
            ))}</div>}
          </CardContent>
        </Card>
        <section aria-labelledby="workflow-title" className="px-1 py-2"><h2 id="workflow-title" className="mb-5 text-xs font-medium uppercase tracking-widest text-muted-foreground">From source to send</h2><ol className="space-y-6">{STEPS.map(({ title, body, href, icon: Icon }, index) => <li key={title}><Link href={href} className="group flex gap-3"><span className="flex size-8 shrink-0 items-center justify-center rounded-lg border border-border text-muted-foreground group-hover:text-violet-300"><Icon className="size-4" aria-hidden="true" /></span><div><h3 className="text-sm font-medium"><span className="mr-2 text-muted-foreground">0{index + 1}</span>{title}</h3><p className="mt-1 text-xs leading-relaxed text-muted-foreground">{body}</p></div></Link></li>)}</ol></section>
      </div>
    </div>
  );
}
