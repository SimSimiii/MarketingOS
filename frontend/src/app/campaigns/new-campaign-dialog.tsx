"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
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
import type { Brand, BrandKnowledge, PolicyPreset } from "@/lib/types";

const NO_BRAND = "__none__";
const NEW_BRAND = "__new__";

const PRESET_LABELS: Record<PolicyPreset, string> = {
  fast: "Fast - cheaper models, shorter budget",
  balanced: "Balanced - the default",
  maximum: "Maximum - best models, most thorough review",
};

type Tone = "professional" | "friendly" | "urgent";

const TONE_LABELS: Record<Tone, string> = {
  professional: "Professional",
  friendly: "Friendly & Casual",
  urgent: "Urgent & Aggressive",
};

//: What each tone means to the writer. Folded straight into `request` below
//: rather than sent as its own field - the writer's prompt only ever sees
//: request.request, never the other campaign fields, so this is the one
//: place a tone instruction actually reaches the copy.
const TONE_INSTRUCTIONS: Record<Tone, string> = {
  professional: "Professional and polished - confident and credible, no slang or hype.",
  friendly:
    "Friendly and casual - warm and conversational, like a text from someone the reader trusts.",
  urgent: "Urgent and aggressive - direct, high-stakes, creates real pressure to act now.",
};

type ContentType = "cart_recovery" | "launch_email";

//: Each template is a sentence the backend's contract parser can read an
//: exact email count out of (see app.marketing.contract.parse_contract) -
//: "exactly 3 emails" / "exactly 1 email" are not decorative, they are what
//: makes the run produce the right number of deliverables.
const CONTENT_TEMPLATES: Record<ContentType, string> = {
  cart_recovery:
    "Write exactly 3 emails for an abandoned cart recovery sequence: a friendly reminder " +
    "sent shortly after checkout was left incomplete, a follow-up that handles the most " +
    "likely reason they hesitated, and a final, honest push to come back and complete the " +
    "purchase.",
  launch_email:
    "Write exactly 1 email announcing the launch of this product to people who have not " +
    "bought it yet - make the case for why it matters now and what to do next.",
};

//: Whether two URLs point at the same page as far as knowledge goes. The
//: crawler stores what it fetched ("https://www.acme.com/"); the user types
//: what they remember ("acme.com"). Comparing those two strings literally is
//: how a brand ends up holding four copies of its own home page.
function sameSource(a: string, b: string): boolean {
  return normalizeSource(a) === normalizeSource(b);
}

function normalizeSource(value: string): string {
  const trimmed = value.trim().toLowerCase();
  if (!trimmed) return "";
  const withoutScheme = trimmed.replace(/^https?:\/\//, "").replace(/^www\./, "");
  return withoutScheme.replace(/\/+$/, "");
}

function buildRequest(type: ContentType, tone: Tone): string {
  return `${CONTENT_TEMPLATES[type]}\n\nTone of voice: ${TONE_INSTRUCTIONS[tone]}`;
}

export interface NewCampaignDialogPrefill {
  brandId: string;
  productDescription?: string | null;
  productUrl?: string | null;
  targetMarket?: string | null;
  senderName?: string | null;
  senderRole?: string | null;
}

interface NewCampaignDialogProps {
  /** Custom trigger element - lets the campaign detail page reuse this same
   * dialog as "generate another type for this brand" instead of the default
   * "New campaign" button. */
  trigger?: React.ReactElement;
  /** Pre-fills brand and product context so re-launching a new deliverable
   * type for a brand that already exists doesn't mean retyping everything. */
  prefill?: NewCampaignDialogPrefill;
}

export function NewCampaignDialog({ trigger, prefill }: NewCampaignDialogProps = {}) {
  const router = useRouter();
  const fileInput = useRef<HTMLInputElement>(null);
  const [open, setOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [name, setName] = useState("");
  const [productDescription, setProductDescription] = useState("");
  const [productUrl, setProductUrl] = useState("");
  const [targetMarket, setTargetMarket] = useState("");
  const [senderName, setSenderName] = useState("");
  const [senderRole, setSenderRole] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [policyPreset, setPolicyPreset] = useState<PolicyPreset>("balanced");
  const [tone, setTone] = useState<Tone>("professional");

  const [brands, setBrands] = useState<Brand[]>([]);
  const [brandChoice, setBrandChoice] = useState<string>(NO_BRAND);
  const [newBrandName, setNewBrandName] = useState("");
  const [existingKnowledgeCount, setExistingKnowledgeCount] = useState<number | null>(null);
  //: Which sources this brand already holds, so a product URL that is already
  //: in its knowledge is not crawled and filed a second time - see
  //: handleGenerate.
  const [existingSources, setExistingSources] = useState<string[]>([]);
  //: undefined while unchecked (or not applicable), null once we've checked
  //: and found nothing compiled yet - distinct states so the toggle's default
  //: can tell "still checking" from "there is genuinely nothing to reuse".
  const [brandKnowledge, setBrandKnowledge] = useState<BrandKnowledge | null | undefined>(
    undefined,
  );
  //: Whether to re-read and recompile the brand's knowledge from scratch.
  //: Defaults to true for a brand that has never been compiled (there is
  //: nothing to reuse yet) and flips to false the moment we learn a compiled
  //: version already exists, since reusing it is what brand-scoped knowledge
  //: is for - see handleBrandChange.
  const [forceRecompile, setForceRecompile] = useState(true);
  const knowledgeRequestId = useRef(0);

  useEffect(() => {
    if (!open) return;
    api
      .listBrands()
      .then(setBrands)
      .catch(() => setBrands([]));
  }, [open]);

  function handleOpenChange(nextOpen: boolean) {
    setOpen(nextOpen);
    if (nextOpen && prefill) {
      handleBrandChange(prefill.brandId);
      setProductDescription(prefill.productDescription ?? "");
      setProductUrl(prefill.productUrl ?? "");
      setTargetMarket(prefill.targetMarket ?? "");
      setSenderName(prefill.senderName ?? "");
      setSenderRole(prefill.senderRole ?? "");
    }
  }

  function handleBrandChange(value: string) {
    setBrandChoice(value);
    setExistingKnowledgeCount(null);
    setExistingSources([]);
    setBrandKnowledge(undefined);
    if (value === NO_BRAND || value === NEW_BRAND) {
      // Nothing to reuse either way - a one-off or a brand new brand always
      // compiles fresh on its first run, so default to "regenerate" since
      // that is the only thing that will actually happen.
      setForceRecompile(true);
      return;
    }
    const requestId = ++knowledgeRequestId.current;
    api
      .listKnowledgeDocuments({ brandId: value })
      .then((docs) => {
        if (knowledgeRequestId.current !== requestId) return;
        setExistingKnowledgeCount(docs.length);
        setExistingSources(docs.map((doc) => doc.source_url ?? "").filter(Boolean));
      })
      .catch(() => {
        if (knowledgeRequestId.current !== requestId) return;
        setExistingKnowledgeCount(null);
        setExistingSources([]);
      });
    api
      .getBrandKnowledge(value)
      .then((knowledge) => {
        if (knowledgeRequestId.current !== requestId) return;
        setBrandKnowledge(knowledge);
        // Already compiled - reuse it by default, which is the whole point
        // of attaching a brand instead of paying to recompile every run.
        setForceRecompile(false);
      })
      .catch(() => {
        if (knowledgeRequestId.current !== requestId) return;
        setBrandKnowledge(null);
        // Never compiled for this brand - there is nothing to reuse yet.
        setForceRecompile(true);
      });
  }

  function reset() {
    setName("");
    setProductDescription("");
    setProductUrl("");
    setTargetMarket("");
    setSenderName("");
    setSenderRole("");
    setFiles([]);
    setPolicyPreset("balanced");
    setTone("professional");
    setBrandChoice(NO_BRAND);
    setNewBrandName("");
    setExistingKnowledgeCount(null);
    setExistingSources([]);
    setBrandKnowledge(undefined);
    setForceRecompile(true);
    if (fileInput.current) fileInput.current.value = "";
  }

  function validate(): string | null {
    if (!name.trim()) return "Give the campaign a name.";
    if (!productDescription.trim()) return "Describe the product first.";
    if (brandChoice === NEW_BRAND && !newBrandName.trim()) return "Name the new brand.";
    return null;
  }

  async function handleGenerate(type: ContentType) {
    const error = validate();
    if (error) {
      toast.error(error);
      return;
    }
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
        request: buildRequest(type, tone),
        product_description: productDescription,
        product_url: productUrl || null,
        target_market: targetMarket || null,
        sender_name: senderName || null,
        sender_role: senderRole || null,
        brand_id: brandId,
        policy_preset: policyPreset,
        force_recompile: brandId ? forceRecompile : null,
      });

      // A brand's knowledge is reused across every campaign attached to it,
      // so only feed it in when there is something new to read - re-adding
      // the same page every run would bump the fingerprint and force a
      // recompile, exactly the cost this is meant to avoid. A one-off
      // (no brand) still attaches its knowledge to the campaign as before.
      const scope = brandId ? { brandId } : { campaignId: campaign.id };
      const failures: string[] = [];
      if (productUrl && !alreadyKnownSource) {
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
      }

      const execution = await api.startCampaign(campaign.id);
      setOpen(false);
      reset();
      router.push(`/campaigns/${campaign.id}/executions/${execution.id}`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to create campaign");
    } finally {
      setSubmitting(false);
    }
  }

  function handleManageKnowledge() {
    setOpen(false);
    router.push("/knowledge");
  }

  const usingExistingBrand = brandChoice !== NO_BRAND && brandChoice !== NEW_BRAND;
  //: The brand has already read this page. Crawling it again would cost a
  //: fetch per page to arrive at the same text, and the compiled knowledge it
  //: produced is exactly what "reuse what's already compiled" promises to
  //: keep.
  const alreadyKnownSource =
    usingExistingBrand &&
    productUrl.trim() !== "" &&
    existingSources.some((source) => sameSource(source, productUrl));

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger render={trigger ?? <Button>New campaign</Button>} />
      <DialogContent className="max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>New campaign</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name">Campaign name</Label>
            <Input id="name" value={name} onChange={(e) => setName(e.target.value)} />
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
                    ? `${existingKnowledgeCount} knowledge source${existingKnowledgeCount === 1 ? "" : "s"} already saved for this brand.`
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
              />
            )}
          </div>

          {usingExistingBrand && (
            <div className="space-y-2">
              <Label htmlFor="recompile">Knowledge base</Label>
              <Select
                value={forceRecompile ? "regenerate" : "reuse"}
                onValueChange={(value) => value && setForceRecompile(value === "regenerate")}
                disabled={brandKnowledge === undefined}
              >
                <SelectTrigger id="recompile" className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="reuse" disabled={!brandKnowledge}>
                    Reuse what&apos;s already compiled
                  </SelectItem>
                  <SelectItem value="regenerate">Regenerate from scratch</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                {brandKnowledge === undefined
                  ? "Checking whether this brand has a compiled knowledge base..."
                  : brandKnowledge
                    ? forceRecompile
                      ? `Every source will be re-read, replacing the v${brandKnowledge.version} knowledge base compiled ${new Date(brandKnowledge.compiled_at).toLocaleDateString()}.`
                      : `Reusing the v${brandKnowledge.version} knowledge base compiled ${new Date(brandKnowledge.compiled_at).toLocaleDateString()} - the cheaper, default path.`
                    : "This brand has never been compiled - it will be generated fresh on this run."}
              </p>
            </div>
          )}

          <div className="space-y-2">
            <Label htmlFor="product_description">What is your product?</Label>
            <Textarea
              id="product_description"
              rows={3}
              value={productDescription}
              onChange={(e) => setProductDescription(e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="product_url">
              {usingExistingBrand ? "Add another page (optional)" : "Product URL (optional)"}
            </Label>
            <Input
              id="product_url"
              type="url"
              placeholder="https://yourproduct.com"
              value={productUrl}
              onChange={(e) => setProductUrl(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              {alreadyKnownSource
                ? "This brand has already read this page - it won't be crawled again, so the compiled knowledge stays reusable."
                : "We read the page and use your own words in the copy."}
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

          {/* Two fields, and the cheapest conversion in the form. Left empty,
              every email in the campaign is signed by the company - a
              signature readers have learned to skim past because it is a
              broadcast. The writer is never allowed to invent a name to fill
              this, so this is the only way one gets there. */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label htmlFor="sender_name">Who is it from? (optional)</Label>
              <Input
                id="sender_name"
                placeholder="Marco"
                value={senderName}
                onChange={(e) => setSenderName(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="sender_role">Their role (optional)</Label>
              <Input
                id="sender_role"
                placeholder="founder"
                value={senderRole}
                onChange={(e) => setSenderRole(e.target.value)}
              />
            </div>
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

          <div className="space-y-2">
            <Label htmlFor="tone">Brand tone</Label>
            <Select value={tone} onValueChange={(value) => value && setTone(value as Tone)}>
              <SelectTrigger id="tone" className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {(Object.keys(TONE_LABELS) as Tone[]).map((option) => (
                  <SelectItem key={option} value={option}>
                    {TONE_LABELS[option]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <DialogFooter className="flex-col items-stretch gap-3 sm:flex-col sm:items-stretch">
          <div className="space-y-2">
            <p className="text-sm font-medium">What do you want to create?</p>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              <Button
                type="button"
                size="lg"
                className="h-auto flex-col items-start gap-0.5 py-3 text-left"
                disabled={submitting}
                onClick={() => handleGenerate("cart_recovery")}
              >
                <span className="font-semibold">Abandoned Cart Sequence</span>
                <span className="text-xs font-normal opacity-80">3 emails</span>
              </Button>
              <Button
                type="button"
                size="lg"
                className="h-auto flex-col items-start gap-0.5 py-3 text-left"
                disabled={submitting}
                onClick={() => handleGenerate("launch_email")}
              >
                <span className="font-semibold">Launch Email</span>
                <span className="text-xs font-normal opacity-80">1 email</span>
              </Button>
              <Button
                type="button"
                variant="outline"
                size="lg"
                className="h-auto flex-col items-start gap-0.5 py-3 text-left"
                disabled
                title="Not built yet - the pipeline only knows how to write emails today."
              >
                <span className="flex items-center gap-2 font-semibold">
                  3 Facebook Ad Posts
                  <Badge variant="secondary">Coming soon</Badge>
                </span>
                <span className="text-xs font-normal opacity-80">Not available yet</span>
              </Button>
              <Button
                type="button"
                variant="outline"
                size="lg"
                className="h-auto flex-col items-start gap-0.5 py-3 text-left"
                disabled={submitting}
                onClick={handleManageKnowledge}
              >
                <span className="font-semibold">Manage Knowledge Base</span>
                <span className="text-xs font-normal opacity-80">
                  Add sources without generating anything
                </span>
              </Button>
            </div>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
