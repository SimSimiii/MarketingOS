"use client";

import { useRef, useState } from "react";
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api-client";
import type { Brand, Campaign } from "@/lib/types";

/** Every document needs a home a campaign run can actually find: a brand
 * (reused by every campaign attached to it) or a single campaign (read once,
 * then discarded). There is no unscoped option - a document tied to neither
 * is never read by anything. */
export function AddKnowledgeDialog({
  campaigns,
  brands,
}: {
  campaigns: Campaign[];
  brands: Brand[];
}) {
  const router = useRouter();
  const fileInput = useRef<HTMLInputElement>(null);
  const [open, setOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const defaultScope = brands.length > 0 ? `brand:${brands[0].id}` : "";
  const [scopeValue, setScopeValue] = useState(defaultScope);
  const [title, setTitle] = useState("");
  const [url, setUrl] = useState("");
  const [content, setContent] = useState("");
  const [file, setFile] = useState<File | null>(null);

  function reset() {
    setTitle("");
    setUrl("");
    setContent("");
    setFile(null);
    setScopeValue(defaultScope);
    if (fileInput.current) fileInput.current.value = "";
  }

  function resolveScope(): { campaignId?: string; brandId?: string } {
    const [kind, id] = scopeValue.split(":", 2);
    if (kind === "brand" && id) return { brandId: id };
    if (kind === "campaign" && id) return { campaignId: id };
    return {};
  }

  async function submit(kind: "url" | "text" | "file") {
    if (!scopeValue) {
      toast.error("Pick a brand or a campaign first");
      return;
    }
    setSubmitting(true);
    try {
      const scope = resolveScope();
      if (kind === "file") {
        if (!file) throw new Error("Choose a file first");
        await api.uploadKnowledgeFile(file, scope, title || undefined);
      } else {
        await api.addKnowledgeSource({
          campaign_id: scope.campaignId ?? null,
          brand_id: scope.brandId ?? null,
          title: title || null,
          url: kind === "url" ? url : null,
          content: kind === "text" ? content : null,
        });
      }
      toast.success("Knowledge added");
      setOpen(false);
      reset();
      router.refresh();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to add knowledge");
    } finally {
      setSubmitting(false);
    }
  }

  const scopeAndTitle = (
    <>
      <div className="space-y-2">
        <Label htmlFor="scope">Save to</Label>
        <select
          id="scope"
          value={scopeValue}
          onChange={(e) => setScopeValue(e.target.value)}
          className="h-9 w-full rounded-md border border-input bg-transparent px-3 text-sm"
        >
          <option value="" disabled>
            Choose a brand or campaign…
          </option>
          {brands.length > 0 && (
            <optgroup label="Brands (reused by every campaign)">
              {brands.map((brand) => (
                <option key={brand.id} value={`brand:${brand.id}`}>
                  {brand.name}
                </option>
              ))}
            </optgroup>
          )}
          {campaigns.length > 0 && (
            <optgroup label="Just one campaign">
              {campaigns.map((campaign) => (
                <option key={campaign.id} value={`campaign:${campaign.id}`}>
                  {campaign.name}
                </option>
              ))}
            </optgroup>
          )}
        </select>
      </div>
      <div className="space-y-2">
        <Label htmlFor="title">Title (optional)</Label>
        <Input id="title" value={title} onChange={(e) => setTitle(e.target.value)} />
      </div>
    </>
  );

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<Button>Add knowledge</Button>} />
      <DialogContent className="max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Tell us about your product</DialogTitle>
        </DialogHeader>

        <Tabs defaultValue="url">
          <TabsList>
            <TabsTrigger value="url">Website</TabsTrigger>
            <TabsTrigger value="file">File</TabsTrigger>
            <TabsTrigger value="text">Text</TabsTrigger>
          </TabsList>

          <TabsContent value="url" className="space-y-4 pt-4">
            {scopeAndTitle}
            <div className="space-y-2">
              <Label htmlFor="url">Page address</Label>
              <Input
                id="url"
                type="url"
                placeholder="https://yourproduct.com/pricing"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
              />
            </div>
            <DialogFooter>
              <Button onClick={() => submit("url")} disabled={submitting || !url || !scopeValue}>
                {submitting ? "Reading..." : "Read page"}
              </Button>
            </DialogFooter>
          </TabsContent>

          <TabsContent value="file" className="space-y-4 pt-4">
            {scopeAndTitle}
            <div className="space-y-2">
              <Label htmlFor="file">Document or screenshot</Label>
              <Input
                id="file"
                type="file"
                ref={fileInput}
                accept=".png,.jpg,.jpeg,.webp,.gif,.pdf,.docx,.md,.txt,.json"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
              <p className="text-xs text-muted-foreground">
                Screenshots are read with vision and OCR - we keep what they say, not the file.
              </p>
            </div>
            <DialogFooter>
              <Button onClick={() => submit("file")} disabled={submitting || !file || !scopeValue}>
                {submitting ? "Reading..." : "Read file"}
              </Button>
            </DialogFooter>
          </TabsContent>

          <TabsContent value="text" className="space-y-4 pt-4">
            {scopeAndTitle}
            <div className="space-y-2">
              <Label htmlFor="content">Paste anything useful</Label>
              <Textarea
                id="content"
                rows={8}
                value={content}
                onChange={(e) => setContent(e.target.value)}
              />
            </div>
            <DialogFooter>
              <Button onClick={() => submit("text")} disabled={submitting || !content || !scopeValue}>
                {submitting ? "Saving..." : "Save"}
              </Button>
            </DialogFooter>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
