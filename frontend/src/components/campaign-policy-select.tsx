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

  async function handleChange(value: string | null) {
    if (!value) return;
    setSaving(true);
    try {
      await api.updateCampaignPolicy(campaign.id, { preset: value as PolicyPreset });
      toast.success("Execution preset updated");
      router.refresh();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not update the preset");
    } finally {
      setSaving(false);
    }
  }

  return (
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
  );
}
