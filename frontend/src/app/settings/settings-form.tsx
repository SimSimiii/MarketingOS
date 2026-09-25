"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
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
    /* The account panel below this one has always been cards; this form was a
       stack of fields floating on the page next to them, which read as an
       unfinished half of the same screen. */
    <Card className="max-w-2xl">
      <CardHeader>
        <CardTitle>Workspace defaults</CardTitle>
        <CardDescription>
          Where a campaign takes its starting point from when its brief does not say.
        </CardDescription>
      </CardHeader>
      <form onSubmit={handleSubmit}>
        <CardContent className="space-y-5">
          <div className="space-y-1.5">
            <Label htmlFor="company_name">Company name</Label>
            <Input
              id="company_name"
              className="h-9"
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="brand_voice">Brand voice</Label>
            <Textarea
              id="brand_voice"
              value={brandVoice}
              onChange={(e) => setBrandVoice(e.target.value)}
              rows={4}
            />
            <p className="text-xs leading-relaxed text-muted-foreground">
              How your writing should sound. A brand workspace learns this from your own copy
              instead, when it has some to read.
            </p>
          </div>

          <div className="grid gap-5 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="ai_provider">AI provider</Label>
              <Input id="ai_provider" className="h-9" value={settings.default_ai_provider} disabled />
              <p className="text-xs leading-relaxed text-muted-foreground">
                Campaign presets may route through Claude or GPT using the connected CLI
                subscriptions.
              </p>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="default_model">Default model</Label>
              <Input
                id="default_model"
                className="h-9"
                value={defaultModel}
                onChange={(e) => setDefaultModel(e.target.value)}
              />
              <p className="text-xs leading-relaxed text-muted-foreground">
                A model name from the catalog, not a tier &mdash; a per-role override takes the
                same values.
              </p>
            </div>
          </div>
        </CardContent>
        <CardFooter className="justify-end">
          <Button type="submit" disabled={submitting}>
            {submitting ? "Saving…" : "Save settings"}
          </Button>
        </CardFooter>
      </form>
    </Card>
  );
}
