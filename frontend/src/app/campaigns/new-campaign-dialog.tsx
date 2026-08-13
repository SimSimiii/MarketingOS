"use client";

import { useEffect, useRef, useState } from "react";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api-client";
import type { Brand, PolicyPreset } from "@/lib/types";

const PLACEHOLDER = "Write me 3 emails that convince my subscribers to buy my product";
const NO_BRAND = "__none__";
const NEW_BRAND = "__new__";

const PRESET_LABELS: Record<PolicyPreset, string> = {
  fast: "Fast - cheaper models, shorter budget",
  balanced: "Balanced - the default",
  maximum: "Maximum - best models, most thorough review",
};

export function NewCampaignDialog() {
  const router = useRouter();
  const fileInput = useRef<HTMLInputElement>(null);
  const [open, setOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [name, setName] = useState("");
  const [campaignRequest, setCampaignRequest] = useState("");
  const [productDescription, setProductDescription] = useState("");
  const [productUrl, setProductUrl] = useState("");
  const [targetMarket, setTargetMarket] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [policyPreset, setPolicyPreset] = useState<PolicyPreset>("balanced");

  const [brands, setBrands] = useState<Brand[]>([]);
  const [brandChoice, setBrandChoice] = useState<string>(NO_BRAND);
  const [newBrandName, setNewBrandName] = useState("");
  const [existingKnowledgeCount, setExistingKnowledgeCount] = useState<number | null>(null);
  const knowledgeRequestId = useRef(0);

  useEffect(() => {
    if (!open) return;
    api
      .listBrands()
      .then(setBrands)
      .catch(() => setBrands([]));
  }, [open]);

  function handleBrandChange(value: string) {
    setBrandChoice(value);
    setExistingKnowledgeCount(null);
    if (value === NO_BRAND || value === NEW_BRAND) return;
    const requestId = ++knowledgeRequestId.current;
    api
      .listKnowledgeDocuments({ brandId: value })
      .then((docs) => {
        if (knowledgeRequestId.current === requestId) setExistingKnowledgeCount(docs.length);
      })
      .catch(() => {
        if (knowledgeRequestId.current === requestId) setExistingKnowledgeCount(null);
      });
  }

  function reset() {
    setName("");
    setCampaignRequest("");
    setProductDescription("");
    setProductUrl("");
    setTargetMarket("");
    setFiles([]);
    setPolicyPreset("balanced");
    setBrandChoice(NO_BRAND);
    setNewBrandName("");
    setExistingKnowledgeCount(null);
    if (fileInput.current) fileInput.current.value = "";
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    try {
      let brandId: string | null = null;
      if (brandChoice === NEW_BRAND) {
        const brand = await api.createBrand({
          name: newBrandName || name,
          website_url: productUrl || null,
        });
        brandId = brand.id;
      } else if (brandChoice !== NO_BRAND) {
        brandId = brandChoice;
      }

      const campaign = await api.createCampaign({
        name,
        request: campaignRequest,
        product_description: productDescription,
        product_url: productUrl || null,
        target_market: targetMarket || null,
        brand_id: brandId,
        policy_preset: policyPreset,
      });

      // A brand's knowledge is reused across every campaign attached to it,
      // so only feed it in when there is something new to read - re-adding
      // the same page every run would bump the fingerprint and force a
      // recompile, exactly the cost this is meant to avoid. A one-off
      // (no brand) still attaches its knowledge to the campaign as before.
      const scope = brandId ? { brandId } : { campaignId: campaign.id };
      const failures: string[] = [];
      if (productUrl) {
        await api
          .addKnowledgeSource({
            campaign_id: scope.campaignId ?? null,
            brand_id: scope.brandId ?? null,
            url: productUrl,
          })
          .catch(() => failures.push(productUrl));
      }
      for (const file of files) {
        await api.uploadKnowledgeFile(file, scope).catch(() => failures.push(file.name));
      }

      if (failures.length > 0) {
        toast.warning(`Campaign created, but we could not read: ${failures.join(", ")}`);
      } else {
        toast.success("Campaign created");
      }
      setOpen(false);
      reset();
      router.push(`/campaigns/${campaign.id}`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to create campaign");
    } finally {
      setSubmitting(false);
    }
  }

  const usingExistingBrand = brandChoice !== NO_BRAND && brandChoice !== NEW_BRAND;

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<Button>New campaign</Button>} />
      <DialogContent className="max-h-[85vh] overflow-y-auto">
        <form onSubmit={handleSubmit} className="space-y-4">
          <DialogHeader>
            <DialogTitle>What do you need?</DialogTitle>
          </DialogHeader>

          <div className="space-y-2">
            <Label htmlFor="request">Your request</Label>
            <Textarea
              id="request"
              rows={3}
              placeholder={PLACEHOLDER}
              value={campaignRequest}
              onChange={(e) => setCampaignRequest(e.target.value)}
              required
              minLength={10}
            />
            <p className="text-xs text-muted-foreground">
              Ask in your own words. Say how many pieces you want and who they are for.
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="name">Campaign name</Label>
            <Input id="name" value={name} onChange={(e) => setName(e.target.value)} required />
          </div>

          <div className="space-y-2">
            <Label htmlFor="brand">Brand</Label>
            <Select value={brandChoice} onValueChange={(value) => value && handleBrandChange(value)}>
              <SelectTrigger id="brand" className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={NO_BRAND}>One-off - don&apos;t save this knowledge</SelectItem>
                {brands.map((brand) => (
                  <SelectItem key={brand.id} value={brand.id}>
                    {brand.name}
                  </SelectItem>
                ))}
                <SelectItem value={NEW_BRAND}>+ New brand</SelectItem>
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              {usingExistingBrand
                ? existingKnowledgeCount === null
                  ? "Checking what's already saved..."
                  : existingKnowledgeCount > 0
                    ? `${existingKnowledgeCount} knowledge source${existingKnowledgeCount === 1 ? "" : "s"} already saved for this brand - reused, not recompiled.`
                    : "Nothing saved for this brand yet - add a source below."
                : brandChoice === NEW_BRAND
                  ? "Knowledge you add below is saved to this brand and reused by every future campaign for it."
                  : "Knowledge you add below is used for this campaign only, then discarded."}
            </p>
            {brandChoice === NEW_BRAND && (
              <Input
                placeholder="Brand name"
                value={newBrandName}
                onChange={(e) => setNewBrandName(e.target.value)}
                required
              />
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="product_description">What is your product?</Label>
            <Textarea
              id="product_description"
              rows={3}
              value={productDescription}
              onChange={(e) => setProductDescription(e.target.value)}
              required
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="product_url">
              {usingExistingBrand ? "Add another page (optional)" : "Your website (optional)"}
            </Label>
            <Input
              id="product_url"
              type="url"
              placeholder="https://yourproduct.com"
              value={productUrl}
              onChange={(e) => setProductUrl(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              We read the page and use your own words in the copy.
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="assets">
              {usingExistingBrand
                ? "Additional screenshots or documents (optional)"
                : "Screenshots or documents (optional)"}
            </Label>
            <Input
              id="assets"
              type="file"
              multiple
              ref={fileInput}
              accept=".png,.jpg,.jpeg,.webp,.gif,.pdf,.docx,.md,.txt"
              onChange={(e) => setFiles(Array.from(e.target.files ?? []))}
            />
            {files.length > 0 && (
              <p className="text-xs text-muted-foreground">
                {files.map((file) => file.name).join(", ")}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="target_market">Who are you selling to? (optional)</Label>
            <Input
              id="target_market"
              value={targetMarket}
              onChange={(e) => setTargetMarket(e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="policy_preset">Execution preset</Label>
            <Select
              value={policyPreset}
              onValueChange={(value) => value && setPolicyPreset(value as PolicyPreset)}
            >
              <SelectTrigger id="policy_preset" className="w-full">
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

          <DialogFooter>
            <Button type="submit" disabled={submitting}>
              {submitting ? "Creating..." : "Create campaign"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
