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
import { Button } from "@/components/ui/button";
import { ModelOverridePanel } from "@/components/model-override-panel";
import { RunForecast } from "@/components/run-forecast";
import { api } from "@/lib/api-client";
import { useModelCatalog } from "@/lib/use-model-catalog";
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
  const catalog = useModelCatalog();
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(currentPreset(campaign) as string);

  const stored = campaign.model_overrides ?? {};
  // Open by default when the campaign already has pins, so a run that is not
  // using the preset's models never looks like one that is.
  const [customOpen, setCustomOpen] = useState(Object.keys(stored).length > 0);
  const [overrides, setOverrides] = useState<Record<string, string>>(stored);
  const dirty = JSON.stringify(overrides) !== JSON.stringify(stored);

  async function save(body: Parameters<typeof api.updateCampaignPolicy>[1], success: string) {
    setSaving(true);
    try {
      await api.updateCampaignPolicy(campaign.id, body);
      // Only bumped once the server has it - the forecast is computed from
      // what was stored, not from what was clicked.
      setSaved(`${body.preset ?? currentPreset(campaign)}:${JSON.stringify(overrides)}`);
      toast.success(success);
      router.refresh();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not save");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-3">
      <Select
        value={currentPreset(campaign)}
        onValueChange={(value) =>
          value && save({ preset: value as PolicyPreset }, "Execution preset updated")
        }
        disabled={saving}
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

      {/* The preset decides the shape of a run - how many drafts, which judges,
          what budget. This decides which model does each job, and the two are
          kept separate because choosing a model should not silently change how
          many drafts get written. */}
      {catalog && (
        <div className="rounded-lg border border-border">
          <button
            type="button"
            onClick={() => setCustomOpen((open) => !open)}
            aria-expanded={customOpen}
            className="flex w-full items-center justify-between gap-2 p-3 text-left"
          >
            <span className="min-w-0">
              <span className="block text-sm font-medium">Custom models</span>
              <span className="block text-xs text-muted-foreground">
                {Object.keys(stored).length > 0
                  ? `${Object.keys(stored).length} pinned - Claude and GPT can be mixed in one run`
                  : "Choose the model behind each agent, from Claude or GPT"}
              </span>
            </span>
            <span className="shrink-0 text-xs text-muted-foreground">
              {customOpen ? "Hide" : "Show"}
            </span>
          </button>

          {customOpen && (
            <div className="space-y-3 border-t border-border p-3">
              <ModelOverridePanel
                catalog={catalog}
                value={overrides}
                onChange={setOverrides}
                disabled={saving}
              />
              <div className="flex items-center justify-end gap-2">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  disabled={saving || !dirty}
                  onClick={() => setOverrides(stored)}
                >
                  Discard
                </Button>
                <Button
                  type="button"
                  size="sm"
                  disabled={saving || !dirty}
                  onClick={() => save({ model_overrides: overrides }, "Model choice saved")}
                >
                  Save models
                </Button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Re-fetched on every saved change, so the picker answers the question
          it raises. `saved` changes identity only once the server has the new
          settings, which is what the estimate is computed from. */}
      <RunForecast campaignId={campaign.id} refreshKey={saved} />
    </div>
  );
}
