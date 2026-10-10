"use client";

import { useState, type FormEvent } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api-client";
import { refreshPage } from "@/lib/page-data";
import type { Campaign } from "@/lib/types";

const optionalFields = [
  ["product_url", "Product website", 2048],
  ["cta_url", "Call-to-action URL", 2048],
  ["target_market", "Audience", 20000],
  ["goals", "Campaign goals", 20000],
  ["sender_name", "Sender name", 256],
  ["sender_role", "Sender role", 256],
] as const;

/** Editing is available before the first run; duplicate to preserve run history afterwards. */
export function EditBriefDialog({ campaign }: { campaign: Campaign }) {
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const value = (field: string) => String(data.get(field) ?? "").trim();
    setSaving(true);
    try {
      await api.updateCampaignBrief(campaign.id, {
        name: value("name"), request: value("request"),
        product_description: value("product_description"),
        product_url: value("product_url") || null, cta_url: value("cta_url") || null,
        target_market: value("target_market") || null, goals: value("goals") || null,
        sender_name: value("sender_name") || null, sender_role: value("sender_role") || null,
      });
      setOpen(false);
      toast.success("Brief updated. No generation was started.");
      refreshPage();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not update the brief.");
    } finally {
      setSaving(false);
    }
  }

  return <Dialog open={open} onOpenChange={(next) => { if (!saving) setOpen(next); }}>
    <DialogTrigger render={<Button variant="outline" />}>Edit brief</DialogTrigger>
    <DialogContent className="max-h-[85dvh] overflow-y-auto sm:max-w-2xl">
      <DialogHeader>
        <DialogTitle>Edit campaign brief</DialogTitle>
        <DialogDescription>Update this draft before its first run. Your sources and execution preset stay attached.</DialogDescription>
      </DialogHeader>
      <form onSubmit={save} className="space-y-4">
        <div className="space-y-2"><Label htmlFor="edit-name">Campaign name</Label><Input id="edit-name" name="name" required maxLength={256} defaultValue={campaign.name} /></div>
        <div className="space-y-2"><Label htmlFor="edit-request">Instructions</Label><Textarea id="edit-request" name="request" required minLength={10} maxLength={100000} rows={6} defaultValue={campaign.request} /></div>
        <div className="space-y-2"><Label htmlFor="edit-product">Offer description</Label><Textarea id="edit-product" name="product_description" maxLength={100000} rows={3} defaultValue={campaign.product_description} /></div>
        <div className="grid gap-4 sm:grid-cols-2">
          {optionalFields.map(([field, label, maxLength]) => <div key={field} className="space-y-2">
            <Label htmlFor={`edit-${field}`}>{label} <span className="text-muted-foreground">(optional)</span></Label>
            <Input id={`edit-${field}`} name={field} maxLength={maxLength} defaultValue={campaign[field] ?? ""} />
          </div>)}
        </div>
        <DialogFooter>
          <Button type="button" variant="outline" disabled={saving} onClick={() => setOpen(false)}>Cancel</Button>
          <Button type="submit" disabled={saving}>{saving ? "Saving…" : "Save brief"}</Button>
        </DialogFooter>
      </form>
    </DialogContent>
  </Dialog>;
}
