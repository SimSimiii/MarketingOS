"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api-client";
import type { UserSettings } from "@/lib/types";

export function SettingsForm({ settings }: { settings: UserSettings }) {
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [companyName, setCompanyName] = useState(settings.company_name ?? "");
  const [brandVoice, setBrandVoice] = useState(settings.brand_voice ?? "");
  const [defaultModel, setDefaultModel] = useState(settings.default_model);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    try {
      await api.updateSettings({
        company_name: companyName || null,
        brand_voice: brandVoice || null,
        default_model: defaultModel,
      });
      toast.success("Settings saved");
      router.refresh();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to save settings");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="max-w-lg space-y-4">
      <div className="space-y-2">
        <Label htmlFor="company_name">Company name</Label>
        <Input
          id="company_name"
          value={companyName}
          onChange={(e) => setCompanyName(e.target.value)}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="brand_voice">Brand voice</Label>
        <Textarea
          id="brand_voice"
          value={brandVoice}
          onChange={(e) => setBrandVoice(e.target.value)}
          rows={4}
        />
      </div>

      <div className="space-y-2">
        <Label>AI provider</Label>
        <Input value={settings.default_ai_provider} disabled />
        <p className="text-xs text-muted-foreground">
          Only Claude is implemented in this MVP; other providers require a new AIProvider
          implementation.
        </p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="default_model">Default model</Label>
        <Input
          id="default_model"
          value={defaultModel}
          onChange={(e) => setDefaultModel(e.target.value)}
        />
      </div>

      <Button type="submit" disabled={submitting}>
        {submitting ? "Saving..." : "Save settings"}
      </Button>
    </form>
  );
}
