"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
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

type ContentType = "cart_recovery" | "launch_email" | "linkedin_message";

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
  //: Never rendered - a LinkedIn message is pasted into a message box, where
  //: there is no HTML to tier. Present because the map is exhaustive.
  linkedin_message: "plain",
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
  //: Read by nothing: a LinkedIn campaign's contract comes from its channel,
  //: not from this sentence (see app.marketing.contract.linkedin_contract).
  //: It is still what the Strategist is briefed from and what the run is
  //: titled by, so it says what the run is for.
  linkedin_message:
    "Write one LinkedIn message that opens a conversation with this person - honest, " +
    "specific to what they do, and short enough to be read in the notification.",
};

const MESSAGE_KIND_LABELS: Record<"connection" | "message", string> = {
  connection: "Connection note - 200 characters",
  message: "Direct message - 1,200 characters",
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
  /** A LinkedIn recipient the user picked from a search result. Set, the
   * dialog opens with its LinkedIn half filled in and expanded - the one
   * thing they would otherwise retype from the profile they just read. */
  linkedinName?: string | null;
  linkedinUrl?: string | null;
  /** Their LinkedIn headline, as the search result reported it. It lands in
   * the checked-facts box rather than in a hidden field, because that is the
   * only place the writer may argue from and the user has to be able to
   * correct it before it gets there. */
  linkedinHeadline?: string | null;
  productDescription?: string | null;
  productUrl?: string | null;
  targetMarket?: string | null;
  goals?: string | null;
  senderName?: string | null;
  senderRole?: string | null;
}

interface NewCampaignDialogProps {
  /** Open on mount, for arriving from somewhere that already decided what
   * this campaign is for - a LinkedIn search result, say. */
  autoOpen?: boolean;
  /** Custom trigger element - lets the campaign detail page reuse this same
   * dialog as "generate another type for this brand" instead of the default
   * "New campaign" button. */
  trigger?: React.ReactElement;
  /** Pre-fills brand and product context so re-launching a new deliverable
   * type for a brand that already exists doesn't mean retyping everything. */
  prefill?: NewCampaignDialogPrefill;
}

export function NewCampaignDialog({ trigger, prefill, autoOpen }: NewCampaignDialogProps = {}) {
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
  //: Who this campaign writes to on LinkedIn. Empty until the user opens the
  //: LinkedIn half of the form or arrives from a search result - an email
  //: campaign never fills any of it in.
  const [recipientName, setRecipientName] = useState("");
  const [recipientUrl, setRecipientUrl] = useState("");
  const [recipientContext, setRecipientContext] = useState("");
  //: Whether what is in that box arrived from a search result rather than
  //: from the user. It decides which warning sits under it: a suggestion and
  //: a checked fact are not the same thing, and the whole field's rule is
  //: that only the second may be argued from.
  const [contextFromSearch, setContextFromSearch] = useState(false);
  const [messageKind, setMessageKind] = useState<"connection" | "message">("message");
  const [messageLanguage, setMessageLanguage] = useState("English");
  const [linkedInOpen, setLinkedInOpen] = useState(false);
  const modelCatalog = useModelCatalog(open);

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

  const opened = useRef(false);
  useEffect(() => {
    if (!autoOpen || opened.current) return;
    opened.current = true;
    handleOpenChange(true);
    // handleOpenChange is stable enough for a once-only open, and listing it
    // would re-run this on every render of a dialog that is already open.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoOpen]);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    api
      .listBrands()
      .then((result) => { if (!cancelled) setBrands(result); })
      .catch(() => { if (!cancelled) setBrands([]); });
    return () => { cancelled = true; };
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
      if (prefill.linkedinUrl) {
        setRecipientName(prefill.linkedinName ?? "");
        setRecipientUrl(prefill.linkedinUrl);
        //: The one recipient-specific fact this product has, handed over
        //: rather than dropped. A writer given a name and a URL and nothing
        //: else has only the product to write about, and writes about it.
        if (prefill.linkedinHeadline) {
          setRecipientContext(`Their LinkedIn headline: ${prefill.linkedinHeadline}`);
          setContextFromSearch(true);
        }
        setLinkedInOpen(true);
      }
    }
  }

  function handleBrandChange(value: string) {
    const requestId = ++knowledgeRequestId.current;
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
    ++knowledgeRequestId.current;
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
    setRecipientName("");
    setRecipientUrl("");
    setRecipientContext("");
    setContextFromSearch(false);
    setMessageKind("message");
    setMessageLanguage("English");
    setLinkedInOpen(false);
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

  function validate(type: ContentType): string | null {
    if (!name.trim()) return "Give the campaign a name.";
    if (brandChoice === NEW_BRAND && !newBrandName.trim()) return "Name the new brand.";
    if (type === "linkedin_message") {
      // Checked here as well as by the API: a message is written to one named
      // person, and the writer is never allowed to invent who that is.
      if (!recipientName.trim()) return "Name the person this message is for.";
      if (!/^https:\/\/([a-z0-9-]+\.)?linkedin\.com\/(in|company)\/[^/]+\/?$/i.test(recipientUrl.trim()))
        return "Paste their LinkedIn profile or company URL (https://www.linkedin.com/in/...).";
    }
    return null;
  }

  async function handleGenerate(type: ContentType) {
    const error = validate(type);
    if (error) {
      // A form that rejects a field it is hiding is a form nobody can fix.
      if (type === "linkedin_message") setLinkedInOpen(true);
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
        product_description: productDescription.trim(),
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
        //: What makes this a LinkedIn run rather than an email one. Null for
        //: every other deliverable, which is what the pipeline reads as
        //: "this is email work".
        channel:
          type === "linkedin_message"
            ? {
                recipient_name: recipientName.trim(),
                recipient_url: recipientUrl.trim(),
                confirmed_context: recipientContext.trim(),
                language: messageLanguage.trim() || "English",
                kind: messageKind,
              }
            : null,
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

  const showProspectPicker = mappedAudienceSelected && selectedProspects.length > 0;

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger render={trigger ?? <Button>New campaign</Button>} />
      {/* A form this long needs three bands, not one scroll: the title stays
          put, the fields scroll, and the things you can actually launch stay
          on screen the whole way down. */}
      <DialogContent className="flex max-h-[90vh] w-full flex-col gap-0 overflow-hidden p-0 sm:max-w-3xl">
        <DialogHeader className="gap-1 border-b border-border px-5 py-4 pr-12">
          <DialogTitle>New campaign</DialogTitle>
          <DialogDescription>
            Name it, point it at what it should read, and say who it is for. Everything else
            already has a default.
          </DialogDescription>
        </DialogHeader>

        <div className="min-h-0 flex-1 space-y-6 overflow-y-auto px-5 py-5">
          <FormSection title="Campaign">
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="name">Campaign name</Label>
                <Input id="name" value={name} onChange={(e) => setName(e.target.value)} />
              </div>

              <div className="space-y-2">
                <Label htmlFor="brand">Brand</Label>
                <Select
                  value={brandChoice}
                  onValueChange={(value) => value && handleBrandChange(value)}
                >
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
                {brandChoice === NEW_BRAND && (
                  <Input
                    placeholder="Brand name"
                    value={newBrandName}
                    onChange={(e) => setNewBrandName(e.target.value)}
                  />
                )}
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
              </div>
            </div>
          </FormSection>

          <FormSection title="Who it is for">
            <div className="grid gap-4 sm:grid-cols-2">
              <div className={showProspectPicker ? "space-y-2" : "space-y-2 sm:col-span-2"}>
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
                        {segment.name} — {segment.assessment.priority === "explore_first" ? "Explore first" : segment.assessment.priority === "incompatible" ? "Incompatible" : "Hypothesis"}
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
              </div>

              {showProspectPicker && (
                <div className="space-y-2">
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
                  className={`rounded-md p-3 text-xs sm:col-span-2 ${
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
          </FormSection>

          {/* Its own band, and collapsed until it is wanted: an email
              campaign never answers any of this, and a LinkedIn one cannot
              run without the first two fields. */}
          <FormSection title="LinkedIn message">
            <div className="rounded-lg border border-border">
              <button
                type="button"
                onClick={() => setLinkedInOpen((open) => !open)}
                aria-expanded={linkedInOpen}
                className="flex w-full items-center justify-between gap-2 p-3 text-left"
              >
                <span className="min-w-0">
                  <span className="block text-sm font-medium">Write to one person on LinkedIn</span>
                  <span className="block text-xs text-muted-foreground">
                    {recipientName
                      ? `To ${recipientName} - ${MESSAGE_KIND_LABELS[messageKind].toLowerCase()}`
                      : "Only for the LinkedIn deliverable below. Everything above still applies - same knowledge, same audience, same Strategist."}
                  </span>
                </span>
                <span className="shrink-0 text-xs text-muted-foreground">
                  {linkedInOpen ? "Hide" : "Show"}
                </span>
              </button>
              {linkedInOpen && (
                <div className="grid gap-4 border-t border-border p-3 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="recipient_name">Who is it to?</Label>
                    <Input
                      id="recipient_name"
                      placeholder="Alice Martin"
                      value={recipientName}
                      onChange={(e) => setRecipientName(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="recipient_url">Their LinkedIn URL</Label>
                    <Input
                      id="recipient_url"
                      type="url"
                      placeholder="https://www.linkedin.com/in/..."
                      value={recipientUrl}
                      onChange={(e) => setRecipientUrl(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2 sm:col-span-2">
                    <Label htmlFor="recipient_context">Facts you have checked about them (optional)</Label>
                    <Textarea
                      id="recipient_context"
                      rows={2}
                      placeholder="Only what you can confirm - a search suggestion is not evidence."
                      value={recipientContext}
                      onChange={(e) => {
                        setRecipientContext(e.target.value);
                        setContextFromSearch(false);
                      }}
                    />
                    {contextFromSearch ? (
                      /* It came off a search result, so it is a lead and not a
                         fact yet. Said in the same words the search result
                         itself used, and in the same colour, because it is the
                         same warning: open their profile, correct the line,
                         cut anything you cannot see there. */
                      <p className="text-xs text-amber-300">
                        Prefilled from the search result and not checked by anyone. Open their
                        profile, fix what is wrong and cut what you cannot see - the writer argues
                        from this line as though you had confirmed it.
                      </p>
                    ) : (
                      <p className="text-xs text-muted-foreground">
                        The only recipient-specific thing the writer may argue from, and what
                        separates a message from a broadcast. Left empty, it introduces itself
                        honestly instead of guessing what they need.
                      </p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="message_kind">Format</Label>
                    <Select
                      value={messageKind}
                      onValueChange={(value) => value && setMessageKind(value as "connection" | "message")}
                    >
                      <SelectTrigger id="message_kind" className="w-full">
                        <SelectValue>
                          {(value: string) => MESSAGE_KIND_LABELS[value as "connection" | "message"]}
                        </SelectValue>
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="connection">{MESSAGE_KIND_LABELS.connection}</SelectItem>
                        <SelectItem value="message">{MESSAGE_KIND_LABELS.message}</SelectItem>
                      </SelectContent>
                    </Select>
                    <p className="text-xs text-muted-foreground">
                      Our editorial limits, not a claim about what LinkedIn accepts.
                    </p>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="message_language">Language</Label>
                    <Input
                      id="message_language"
                      value={messageLanguage}
                      onChange={(e) => setMessageLanguage(e.target.value)}
                    />
                  </div>
                </div>
              )}
            </div>
          </FormSection>

          <FormSection title="What it reads">
            <div className="grid gap-4 sm:grid-cols-2">
              {usingExistingBrand && (
                <div className="space-y-2 sm:col-span-2">
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

              <div className="space-y-2 sm:col-span-2">
                <Label htmlFor="product_description">Additional context (optional)</Label>
                <Textarea
                  id="product_description"
                  aria-describedby="product_description_hint"
                  placeholder="Anything specific to this campaign that isn't in your sources…"
                  rows={3}
                  value={productDescription}
                  onChange={(e) => setProductDescription(e.target.value)}
                />
                <p id="product_description_hint" className="text-xs text-muted-foreground">
                  {usingExistingBrand
                    ? "We'll use this brand's knowledge base and saved sources. Add only any extra details for this campaign."
                    : "We'll use the sources you add. You can include extra details here if needed."}
                </p>
              </div>
            </div>
          </FormSection>

          <FormSection title="How it reads">
            <div className="grid gap-4 sm:grid-cols-2">
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

              {/* Two fields, and the cheapest conversion in the form. Left empty,
                  every email in the campaign is signed by the company - a
                  signature readers have learned to skim past because it is a
                  broadcast. The writer is never allowed to invent a name to fill
                  this, so this is the only way one gets there. */}
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
          </FormSection>

          <FormSection title="How it runs">
            <div className="space-y-4">
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
            </div>
          </FormSection>
        </div>

        <DialogFooter className="mx-0 mb-0 flex-col items-stretch gap-3 px-5 py-4 sm:flex-col sm:items-stretch">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-sm font-medium">What do you want to create?</p>
            {/* Not a deliverable - it leaves the form - so it does not sit in the
                same row as the buttons that start a run. */}
            <Button
              type="button"
              variant="ghost"
              size="sm"
              disabled={submitting}
              onClick={handleManageKnowledge}
            >
              Manage knowledge base
            </Button>
          </div>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-4">
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
              size="lg"
              className="h-auto flex-col items-start gap-0.5 py-3 text-left"
              disabled={submitting}
              onClick={() => handleGenerate("linkedin_message")}
            >
              <span className="font-semibold">
                {requiresOverride ? "Generate anyway: LinkedIn Message" : "LinkedIn Message"}
              </span>
              <span className="text-xs font-normal opacity-80">
                1 message{recipientName ? ` to ${recipientName}` : " - needs a recipient"}
              </span>
            </Button>
            <Button
              type="button"
              variant="outline"
              size="lg"
              className="h-auto flex-col items-start gap-0.5 py-3 text-left"
              disabled
              title="Not built yet - the pipeline only knows how to write emails and LinkedIn messages today."
            >
              <span className="flex items-center gap-2 font-semibold">
                3 Facebook Ad Posts
                <Badge variant="secondary">Coming soon</Badge>
              </span>
              <span className="text-xs font-normal opacity-80">Not available yet</span>
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/** One labelled band of the campaign form. The dialog asks sixteen questions;
 * grouping them is the difference between a form and a wall. */
function FormSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-3">
      <h3 className="border-b border-border/60 pb-1.5 text-xs font-medium tracking-wide text-muted-foreground uppercase">
        {title}
      </h3>
      {children}
    </section>
  );
}
