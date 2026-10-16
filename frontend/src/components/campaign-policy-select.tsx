"use client";

import { useState } from "react";
import { toast } from "sonner";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { RunForecast } from "@/components/run-forecast";
import { api } from "@/lib/api-client";
import type { Campaign, EmailTier, PolicyPreset } from "@/lib/types";
import { refreshPage } from "@/lib/page-data";

const PRESET_LABELS: Record<PolicyPreset, string> = {
  fast: "Fast - fewer review passes, shorter budget",
  balanced: "Balanced - the default",
  maximum: "Maximum - most variants and thorough review",
};

const TIER_LABELS: Record<EmailTier, string> = {
  plain: "Plain - typography only, looks like a person wrote it",
  branded: "Branded - logo, colour, a real button and a footer",
};

function currentPreset(campaign: Campaign): PolicyPreset {
  const preset = campaign.policy?.preset;
  return preset === "fast" || preset === "maximum" ? preset : "balanced";
}

/** What this campaign's emails will actually render as.
 *
 * An absent tier renders plain, so an unset one and an explicit "plain" are
 * the same picture to the reader; showing them as different states would
 * invent a distinction the output does not have. */
function currentTier(campaign: Campaign): EmailTier {
  return campaign.policy?.email_tier === "branded" ? "branded" : "plain";
}

export function CampaignPolicySelect({ campaign }: { campaign: Campaign }) {
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(currentPreset(campaign) as string);

  async function save(body: Parameters<typeof api.updateCampaignPolicy>[1], success: string) {
    setSaving(true);
    try {
      await api.updateCampaignPolicy(campaign.id, body);
      // Only bumped once the server has it - the forecast is computed from
      // what was stored, not from what was clicked.
      setSaved(`${body.preset ?? currentPreset(campaign)}:${body.email_tier ?? currentTier(campaign)}`);
      toast.success(success);
      refreshPage();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not save");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="space-y-1.5">
      <p className="text-xs font-medium text-foreground/80">Review depth</p>
      <Select
        value={currentPreset(campaign)}
        onValueChange={(value) =>
          value && save({ preset: value as PolicyPreset }, "Execution preset updated")
        }
        disabled={saving}
        items={PRESET_LABELS}
      >
        <SelectTrigger className="w-full">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {(Object.keys(PRESET_LABELS) as PolicyPreset[]).map((preset) => (
            <SelectItem key={preset} value={preset}>
              {PRESET_LABELS[preset]}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      </div>

      {/* Presentation, not shape: it changes nothing about how the run is
          bought, which is why it does not move the forecast below. Offered
          after the run rather than only on the creation form because it is the
          one decision a user revises once they have seen the emails, and
          re-running a campaign is cheap where re-creating it is not. */}
      <div className="space-y-1.5">
        <p className="text-xs font-medium text-foreground/80">Email look</p>
        <Select
          value={currentTier(campaign)}
          onValueChange={(value) =>
            value && save({ email_tier: value as EmailTier }, "Look updated")
          }
          disabled={saving}
          items={TIER_LABELS}
        >
          <SelectTrigger className="w-full">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="plain">{TIER_LABELS.plain}</SelectItem>
            <SelectItem value="branded">{TIER_LABELS.branded}</SelectItem>
          </SelectContent>
        </Select>
        {currentTier(campaign) === "branded" && (
          <p className="text-xs leading-relaxed text-muted-foreground">
            {campaign.brand_id
              ? "Set the logo, colour and footer on the brand page, or it renders as plain."
              : "Nothing to brand it with until this campaign is attached to a brand."}
          </p>
        )}
      </div>

      {/* Re-fetched on every saved change, so the picker answers the question
          it raises. `saved` changes identity only once the server has the new
          settings, which is what the estimate is computed from. */}
      <RunForecast campaignId={campaign.id} refreshKey={saved} />
    </div>
  );
}
