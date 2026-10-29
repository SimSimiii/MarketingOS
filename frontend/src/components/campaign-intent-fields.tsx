"use client";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import type { CampaignIntent } from "@/lib/types";

export function CampaignIntentFields({ value, onChange }: {
  value: CampaignIntent | null; onChange: (intent: CampaignIntent) => void;
}) {
  const intent = value ?? { objective: "custom", objective_source: "inferred", reader_relationship: "unknown", relationship_source: "inferred" };
  const change = (patch: Partial<CampaignIntent>) => onChange({ ...intent, ...patch });
  return <div className="space-y-4">
    <div className="grid gap-4 sm:grid-cols-2">
      <div className="space-y-2">
        <Label htmlFor="campaign-objective">Campaign objective</Label>
        <select id="campaign-objective" className="w-full rounded-md border bg-background p-2 text-sm" value={intent.objective ?? "custom"}
          onChange={(event) => change({ objective: event.target.value as CampaignIntent["objective"], objective_source: "user" })}>
          <option value="custom">Follow my instructions</option><option value="announcement">Present or announce an offering</option>
          <option value="acquisition">Start a conversation or evaluation</option><option value="activation">Help with a first action</option>
          <option value="recovery">Resume an incomplete action</option><option value="nurture">Develop interest over time</option>
        </select>
      </div>
      <div className="space-y-2">
        <Label htmlFor="reader-relationship">Relationship with the reader</Label>
        <select id="reader-relationship" className="w-full rounded-md border bg-background p-2 text-sm" value={intent.reader_relationship ?? "unknown"}
          onChange={(event) => change({ reader_relationship: event.target.value as CampaignIntent["reader_relationship"], relationship_source: "user" })}>
          <option value="unknown">Not specified</option><option value="cold">First contact</option><option value="subscriber">Subscriber</option>
          <option value="prospect">Prospect already in contact</option><option value="customer">Existing customer</option>
        </select>
      </div>
    </div>
    <div className="space-y-2">
      <Label htmlFor="announcement-facts">Announcement or offer facts <span className="text-muted-foreground">(optional)</span></Label>
      <Textarea id="announcement-facts" rows={2} maxLength={6000} value={intent.announcement ?? ""}
        onChange={(event) => change({ announcement: event.target.value })} placeholder="What is being introduced or changed? Include a release date only if established." />
      <p className="text-xs text-muted-foreground">The Launch button sets the objective. These facts establish what is actually new.</p>
    </div>
    <div className="space-y-2">
      <Label htmlFor="reason-now">Why this timing matters <span className="text-muted-foreground">(optional)</span></Label>
      <Input id="reason-now" maxLength={4000} value={intent.reason_now ?? ""} onChange={(event) => change({ reason_now: event.target.value })}
        placeholder="An established event, availability change or useful occasion" />
    </div>
  </div>;
}
