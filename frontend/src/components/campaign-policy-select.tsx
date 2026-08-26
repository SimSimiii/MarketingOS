"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
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
import type { Campaign, PolicyPreset } from "@/lib/types";

const PRESET_LABELS: Record<PolicyPreset, string> = {
  fast: "Fast - cheaper models, shorter budget",
  balanced: "Balanced - the default",
  maximum: "Maximum - best models, most thorough review",
};

function currentPreset(campaign: Campaign): PolicyPreset {
  const preset = campaign.policy?.preset;
  return preset === "fast" || preset === "maximum" ? preset : "balanced";
}

export function CampaignPolicySelect({ campaign }: { campaign: Campaign }) {
  const router = useRouter();
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(currentPreset(campaign) as string);

  async function handleChange(value: string | null) {
    if (!value) return;
    setSaving(true);
    try {
      await api.updateCampaignPolicy(campaign.id, { preset: value as PolicyPreset });
      setSaved(value);
      toast.success("Execution preset updated");
      router.refresh();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not update the preset");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-3">
      <Select value={currentPreset(campaign)} onValueChange={handleChange} disabled={saving}>
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
      {/* Re-fetched on every change of preset, so the picker answers the
          question it raises. `saved` changes identity only once the server
          has the new preset, which is what the estimate is computed from. */}
      <RunForecast campaignId={campaign.id} refreshKey={saved} />
    </div>
  );
}
