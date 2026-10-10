"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api-client";
import { refreshPage } from "@/lib/page-data";

/** `primary` for the page's own call to action; `autoOpen` for arriving from
 * the command palette's "New brand". */
export function NewBrandDialog({ primary = false, autoOpen = false }: { primary?: boolean; autoOpen?: boolean } = {}) {
  const router = useRouter();
  const [open, setOpen] = useState(autoOpen);
  const [submitting, setSubmitting] = useState(false);
  const [name, setName] = useState("");
  const [websiteUrl, setWebsiteUrl] = useState("");

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!name.trim()) {
      toast.error("Give the brand a name.");
      return;
    }
    setSubmitting(true);
    try {
      const brand = await api.createBrand({ name: name.trim(), website_url: websiteUrl.trim() || null });
      toast.success("Brand created");
      setOpen(false);
      setName("");
      setWebsiteUrl("");
      // Straight into the new workspace: a brand with nothing in it is not a
      // row worth returning to a list for - the next thing to do is add its
      // material, and that lives inside it.
      router.push(`/brands/${brand.id}/knowledge`);
      refreshPage();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to create brand");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<Button variant={primary ? "default" : "outline"}>New brand</Button>} />
      <DialogContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <DialogHeader>
            <DialogTitle>Register a business</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            A brand gets its own workspace: its sources, its compiled knowledge base and its
            market. Knowledge you attach to it is compiled once and reused by every campaign for
            it, instead of being recompiled from scratch each time.
          </p>
          <div className="space-y-2">
            <Label htmlFor="brand_name">Name</Label>
            <Input id="brand_name" value={name} onChange={(e) => setName(e.target.value)} required />
          </div>
          <div className="space-y-2">
            <Label htmlFor="brand_url">Website (optional)</Label>
            <Input
              id="brand_url"
              type="url"
              placeholder="https://yourproduct.com"
              value={websiteUrl}
              onChange={(e) => setWebsiteUrl(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">This saves the website address. Add its pages as sources in the next step.</p>
          </div>
          <DialogFooter>
            <Button type="submit" disabled={submitting || !name.trim()}>
              {submitting ? "Creating..." : "Create brand"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
