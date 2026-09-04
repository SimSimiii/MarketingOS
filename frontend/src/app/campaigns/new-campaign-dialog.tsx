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
import { ModelOverridePanel } from "@/components/model-override-panel";
import { api } from "@/lib/api-client";
import { useModelCatalog } from "@/lib/use-model-catalog";
import type {
  AudienceRead,
  Brand,
  BrandKnowledge,
  EmailTier,
  MappedSegment,
  PolicyPreset,
  Prospect,
} from "@/lib/types";

const NO_BRAND = "__none__";
const NEW_BRAND = "__new__";

//: Written to whoever the company's own material describes - the default,
//: and what every campaign did before demand could be mapped.
const NO_SEGMENT = "__default__";
//: The user describes the buyer in their own words. Kept in the same control
//: as the mapped segments rather than beside it: "who is this for" is one
//: question with one answer, and a form that asks it twice - once as a
//: dropdown and once as a text box - invites somebody to answer both and
//: leaves the run to guess which they meant.
const CUSTOM_AUDIENCE = "__custom__";
const NO_PROSPECT = "__audience_level__";

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

const TIER_LABELS: Record<EmailTier, string> = {
  plain: "Plain - typography only, looks like a person wrote it",
  branded: "Branded - logo, colour, a real button and a footer",
};

//: What each deliverable should look like unless the user says otherwise.
//:
//: The tier is not a global preference, and treating it as one is how every
//: email in a product ends up either a mailshot or a plain-text note. A cart
//: recovery and a launch announcement are mail the reader expects from a
//: company, and looking like one is the honest signal; a cold sequence is one
//: person writing to another, where a template scores worse with filters and
//: converts worse. So the choice follows the thing being made, and the user
//: can still override it.
const TIER_FOR_TYPE: Record<ContentType, EmailTier> = {
  cart_recovery: "branded",
  launch_email: "branded",
};

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

function audienceKey(value: string): string {
  return value.toLocaleLowerCase().trim().split(/\s+/).join(" ");
}

export interface NewCampaignDialogPrefill {
  brandId: string;
  productDescription?: string | null;
  productUrl?: string | null;
  targetMarket?: string | null;
  goals?: string | null;
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
  const [goals, setGoals] = useState("");
  const [senderName, setSenderName] = useState("");
  const [senderRole, setSenderRole] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [policyPreset, setPolicyPreset] = useState<PolicyPreset>("balanced");
  const [tone, setTone] = useState<Tone>("professional");
  //: Per-agent model pins, empty until the operator opens the panel. Sent
  //: as null when empty so a campaign created without touching it stores
  //: nothing rather than an empty object.
  const [modelOverrides, setModelOverrides] = useState<Record<string, string>>({});
  const [customModelsOpen, setCustomModelsOpen] = useState(false);
  const modelCatalog = useModelCatalog();

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
  //: The buyers somebody mapped for this brand, and which of them this
  //: campaign is written to. Empty for a brand nobody has mapped, which is
  //: most of them - the picker only appears when there is a real choice.
  const [segments, setSegments] = useState<MappedSegment[]>([]);
  const [audienceData, setAudienceData] = useState<AudienceRead | null>(null);
  const [audienceSegment, setAudienceSegment] = useState<string>(NO_SEGMENT);
  const [prospectChoice, setProspectChoice] = useState<string>(NO_PROSPECT);
  //: Where the button goes. The writer is told it does not know this and
  //: writes the words on the link instead, so it is asked for here - without
  //: it a branded email renders a styled link rather than a button, because a
  //: button that goes nowhere is worse than no button.
  const [ctaUrl, setCtaUrl] = useState("");
  //: Null until the user picks one, so each deliverable's own default
  //: applies - see TIER_FOR_TYPE. A stored choice would quietly make every
  //: later campaign look like the first one they made.
  const [emailTier, setEmailTier] = useState<EmailTier | null>(null);
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
      // A prefilled description is the answer to the same question, so the
      // control opens on it rather than on the default with a hidden value.
      if (prefill.targetMarket) setAudienceSegment(CUSTOM_AUDIENCE);
      setGoals(prefill.goals ?? "");
      setSenderName(prefill.senderName ?? "");
      setSenderRole(prefill.senderRole ?? "");
    }
  }

  function handleBrandChange(value: string) {
    setBrandChoice(value);
    setExistingKnowledgeCount(null);
    setExistingSources([]);
    setBrandKnowledge(undefined);
    setSegments([]);
    setAudienceData(null);
    setProspectChoice(NO_PROSPECT);
    // A typed description belongs to the campaign, not to the brand, so
    // changing brand keeps it. A *mapped* segment belongs to the brand that
    // was mapped, and cannot survive the switch.
    setAudienceSegment((current) => (current === CUSTOM_AUDIENCE ? current : NO_SEGMENT));
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
    //: A one-off has nowhere to keep a map between runs, so this only ever
    //: runs for a saved brand. A failure is silent on purpose: an unmapped
    //: audience is the normal state and is not worth a toast on a form.
    api
      .getAudience(value)
      .then((audience) => {
        if (knowledgeRequestId.current !== requestId) return;
        setSegments(audience.map?.segments ?? []);
        setAudienceData(audience);
      })
      .catch(() => {
        if (knowledgeRequestId.current !== requestId) return;
        setSegments([]);
        setAudienceData(null);
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
    setModelOverrides({});
    setCustomModelsOpen(false);
    setBrandChoice(NO_BRAND);
    setNewBrandName("");
    setExistingKnowledgeCount(null);
    setExistingSources([]);
    setBrandKnowledge(undefined);
    setSegments([]);
    setAudienceData(null);
    setAudienceSegment(NO_SEGMENT);
    setProspectChoice(NO_PROSPECT);
    setCtaUrl("");
    setEmailTier(null);
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
        // One question, one answer: whichever half of the control was used
        // is sent and the other is null, so nothing downstream has to decide
        // which of two audiences the user meant.
        target_market:
          audienceSegment === CUSTOM_AUDIENCE ? targetMarket.trim() || null : null,
        goals: goals.trim() || null,
        sender_name: senderName || null,
        sender_role: senderRole || null,
        brand_id: brandId,
        //: Only meaningful for a brand whose demand was mapped, and only when
        //: the user picked one - otherwise the run is written to the audience
        //: the company's own material describes, as it always was.
        audience_segment:
          brandId && audienceSegment !== NO_SEGMENT && audienceSegment !== CUSTOM_AUDIENCE
            ? audienceSegment
            : null,
        prospect_id:
          brandId && prospectChoice !== NO_PROSPECT ? prospectChoice : null,
        cta_url: ctaUrl.trim() || null,
        email_tier: emailTier ?? TIER_FOR_TYPE[type],
        policy_preset: policyPreset,
        model_overrides: Object.keys(modelOverrides).length > 0 ? modelOverrides : null,
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

      const execution = await api.startCampaign(campaign.id, requiresOverride);
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
  const selectedSegment = segments.find((segment) => segment.name === audienceSegment);
  const selectedProspects = (audienceData?.prospects ?? []).filter(
    (prospect) => prospect.segment === audienceSegment && prospect.status !== "dismissed",
  );
  const selectedProspect: Prospect | undefined = selectedProspects.find(
    (prospect) => prospect.id === prospectChoice,
  );
  const selectedRelevance = audienceData?.relevance.find(
    (item) => audienceKey(item.audience_name) === audienceKey(audienceSegment),
  );
  const recommendation = selectedRelevance?.dossier?.recommendation ?? null;
  const mappedAudienceSelected =
    audienceSegment !== NO_SEGMENT && audienceSegment !== CUSTOM_AUDIENCE;
  const audienceNeedsOverride =
    mappedAudienceSelected &&
    (selectedRelevance?.status !== "current" ||
      !recommendation ||
      recommendation.readiness === "DISCOVERY_ONLY" ||
      recommendation.readiness === "NO_GO");
  const companyNeedsOverride = Boolean(
    selectedProspect?.qualification &&
      selectedProspect.qualification.classification !== "QUALIFIED",
  );
  const companyUnqualified = Boolean(selectedProspect && !selectedProspect.qualification);
  const narrowCompanyOutside = Boolean(
    recommendation?.readiness === "GO_NARROW" &&
      selectedProspect &&
      selectedProspect.qualification?.classification !== "QUALIFIED",
  );
  const requiresOverride =
    audienceNeedsOverride || companyNeedsOverride || companyUnqualified || narrowCompanyOutside;
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

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="tier">How it looks</Label>
              <Select
                value={emailTier ?? ""}
                onValueChange={(value) => value && setEmailTier(value as EmailTier)}
              >
                <SelectTrigger id="tier" className="w-full">
                  <SelectValue placeholder="Follow the deliverable">
                    {(value: string) =>
                      value ? TIER_LABELS[value as EmailTier] : "Follow the deliverable"
                    }
                  </SelectValue>
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="plain">{TIER_LABELS.plain}</SelectItem>
                  <SelectItem value="branded">{TIER_LABELS.branded}</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                {emailTier === "branded"
                  ? usingExistingBrand
                    ? "Set the logo, colour and footer on the brand page, or it renders as plain."
                    : "Nothing to brand it with until this campaign is attached to a brand."
                  : emailTier === "plain"
                    ? "One person writing to another. The right answer for cold outreach."
                    : "Cart recovery and launches come out branded; anything cold stays plain."}
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="cta-url">Where the button goes (optional)</Label>
              <Input
                id="cta-url"
                type="url"
                placeholder="https://yourproduct.com/cart"
                value={ctaUrl}
                onChange={(e) => setCtaUrl(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                The writer never invents a link. Without one here the brand&rsquo;s website is
                used, and with neither the call to action stays a marked slot for you to fill.
              </p>
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="audience">Who this is for</Label>
            <Select
              value={audienceSegment}
              onValueChange={(value) => {
                if (!value) return;
                setAudienceSegment(value);
                setProspectChoice(NO_PROSPECT);
              }}
            >
              <SelectTrigger id="audience" className="w-full">
                {/* The trigger renders the raw value, so a sentinel would read
                    as "__default__" to a user. Every other select in this form
                    gets away with it because its values are already words. */}
                <SelectValue>
                  {(value: string) =>
                    value === NO_SEGMENT
                      ? "Whoever your own material describes"
                      : value === CUSTOM_AUDIENCE
                        ? "Let me describe them"
                        : value
                  }
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={NO_SEGMENT}>Whoever your own material describes</SelectItem>
                {segments.map((segment) => (
                  <SelectItem key={segment.name} value={segment.name}>
                    {segment.name} — {Math.round(segment.fit * 100)}%
                    {segment.unobvious ? " · not on your site" : ""}
                  </SelectItem>
                ))}
                <SelectItem value={CUSTOM_AUDIENCE}>Let me describe them</SelectItem>
              </SelectContent>
            </Select>

            {audienceSegment === CUSTOM_AUDIENCE && (
              <Input
                id="target_market"
                autoFocus
                placeholder="Independent repair shops that resell refurbished laptops"
                value={targetMarket}
                onChange={(e) => setTargetMarket(e.target.value)}
              />
            )}

            <p className="text-xs text-muted-foreground">
              {audienceSegment === CUSTOM_AUDIENCE
                ? "What you write here outranks what the compiler inferred — you know something about this campaign that no crawl of your site could."
                : audienceSegment !== NO_SEGMENT
                  ? selectedSegment?.angle
                    ? `The copy will open on: ${selectedSegment.angle}`
                    : "The whole sequence will be planned against this buyer."
                  : usingExistingBrand && segments.length === 0
                    ? "Nobody has mapped this brand's audience yet. Market → Audience finds the buyers your own site does not name, and they show up in this list."
                    : "Every email will be planned against the buyer your website names — the opening line, the objection it answers, and the reader who grades every draft."}
            </p>

            {mappedAudienceSelected && selectedProspects.length > 0 && (
              <div className="space-y-2 pt-1">
                <Label htmlFor="prospect">Specific company (optional)</Label>
                <Select
                  value={prospectChoice}
                  onValueChange={(value) => value && setProspectChoice(value)}
                >
                  <SelectTrigger id="prospect" className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value={NO_PROSPECT}>Audience-level campaign</SelectItem>
                    {selectedProspects.map((prospect) => (
                      <SelectItem key={prospect.id} value={prospect.id}>
                        {prospect.name} — {prospect.qualification?.classification ?? "UNVERIFIED"}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  Choosing a company makes its evidence-backed qualification part of the
                  generation preflight. Leaving this at audience level never treats every found
                  company as eligible.
                </p>
              </div>
            )}

            {mappedAudienceSelected && (
              <div
                className={`rounded-md p-3 text-xs ${
                  requiresOverride
                    ? "bg-amber-500/10 text-amber-200"
                    : "bg-primary/10 text-foreground/80"
                }`}
              >
                <p className="font-medium">
                  {recommendation
                    ? selectedRelevance?.status === "current"
                      ? `${recommendation.state.replaceAll("_", " ")} · ${recommendation.readiness.replaceAll("_", " ")}`
                      : "DISCOVERY ONLY · dossier is stale"
                    : "DISCOVERY ONLY · no current V2 dossier"}
                </p>
                <p className="mt-1">
                  {selectedProspect
                    ? `${selectedProspect.name}: ${selectedProspect.qualification?.classification ?? "UNVERIFIED"}.`
                    : selectedRelevance?.status === "current"
                      ? recommendation?.recommended_next_action ||
                        "Build the audience's V2 relevance dossier before treating it as qualified."
                      : "Rebuild the audience's V2 relevance dossier before treating it as qualified."}
                </p>
                {requiresOverride && (
                  <p className="mt-1">
                    Generation remains available, but the action below changes to “Generate
                    anyway” and the override is recorded with the run.
                  </p>
                )}
              </div>
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

          {/* The last line of render_context() that no form filled. The
              strategist is told the product, the audience and the sender; what
              the campaign is *for* was the one input it had to infer, and a
              sequence planned toward "trial signups" escalates differently
              from one planned toward a reply. Optional, and omitted when
              blank, so a run that says nothing here plans exactly as before. */}
          <div className="space-y-2">
            <Label htmlFor="goals">What do you want out of it? (optional)</Label>
            <Input
              id="goals"
              placeholder="Trial signups"
              value={goals}
              onChange={(e) => setGoals(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              The outcome the sequence is planned toward, not the copy&apos;s subject. It
              decides what each email escalates to and what the last one asks for.
            </p>
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

          {/* Separate from the preset on purpose: the preset decides the shape
              of a run (how many drafts, which judges, what budget), this
              decides which model does each job. Folding them together would
              mean picking a model silently changed how many drafts get
              written. */}
          {modelCatalog && (
            <div className="rounded-lg border border-border">
              <button
                type="button"
                onClick={() => setCustomModelsOpen((open) => !open)}
                aria-expanded={customModelsOpen}
                className="flex w-full items-center justify-between gap-2 p-3 text-left"
              >
                <span className="min-w-0">
                  <span className="block text-sm font-medium">Custom models</span>
                  <span className="block text-xs text-muted-foreground">
                    {Object.keys(modelOverrides).length > 0
                      ? `${Object.keys(modelOverrides).length} pinned - Claude and GPT can be mixed in one run`
                      : "Optional. Choose the model behind each agent, from Claude or GPT."}
                  </span>
                </span>
                <span className="shrink-0 text-xs text-muted-foreground">
                  {customModelsOpen ? "Hide" : "Show"}
                </span>
              </button>
              {customModelsOpen && (
                <div className="border-t border-border p-3">
                  <ModelOverridePanel
                    catalog={modelCatalog}
                    value={modelOverrides}
                    onChange={setModelOverrides}
                    disabled={submitting}
                  />
                </div>
              )}
            </div>
          )}

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
                <span className="font-semibold">
                  {requiresOverride ? "Generate anyway: Cart Sequence" : "Abandoned Cart Sequence"}
                </span>
                <span className="text-xs font-normal opacity-80">3 emails</span>
              </Button>
              <Button
                type="button"
                size="lg"
                className="h-auto flex-col items-start gap-0.5 py-3 text-left"
                disabled={submitting}
                onClick={() => handleGenerate("launch_email")}
              >
                <span className="font-semibold">
                  {requiresOverride ? "Generate anyway: Launch Email" : "Launch Email"}
                </span>
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
