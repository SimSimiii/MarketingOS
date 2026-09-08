"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import type {
  AudienceDefinition,
  AudienceEvidenceReference,
  AudienceRead,
  AudienceResearch,
  CampaignRecommendation,
  CapabilityState,
  CompanyQualification,
  Contact,
  ContractClaim,
  MappedSegment,
  MapOptions,
  Prospect,
  ProductCapabilityProfile,
  RelevanceBand,
  RelevanceEvidence,
  RelevanceStatus as RelevanceDossierStatus,
  SegmentKind,
  UserAudienceInput,
} from "@/lib/types";

/** What each kind of segment is, in one phrase.
 *
 * The labels carry the whole argument of this page. A user looking at eight
 * segments they already knew has learned nothing; these say, per row, which
 * ones came from somewhere their own website could not have. */
const KIND_LABELS: Record<SegmentKind, string> = {
  core: "who you already sell to",
  adjacent: "same problem, different industry",
  influencer: "feels the pain, does not sign",
  channel: "would resell you to their own clients",
  triggered: "something just happened to them",
  unintended: "using it for something you did not design",
};

const CONTACT_ICONS: Record<Contact["kind"], string> = {
  email: "✉",
  phone: "☎",
  form: "▤",
  social: "◎",
};

function percent(fit: number): string {
  return `${Math.round(fit * 100)}%`;
}

function researchabilityLabel(value: MappedSegment["researchability"]): string {
  return value === "unresearchable" ? "Unresearchable" : `${value} researchability`;
}

function audienceKey(value: string): string {
  return value.toLocaleLowerCase().trim().split(/\s+/).join(" ");
}

function ResearchEvidenceLinks({
  evidence,
  research,
}: {
  evidence: AudienceEvidenceReference[];
  research: AudienceResearch;
}) {
  const sources = new Map(research.sources.map((source) => [source.id, source]));
  return (
    <span className="ml-1 inline-flex flex-wrap gap-1">
      {evidence.map((item, index) => {
        const source = sources.get(item.source_id);
        return source ? (
          <a
            key={`${item.source_id}-${index}`}
            href={source.final_url}
            target="_blank"
            rel="noreferrer noopener"
            title={`${item.quote} — ${source.title}`}
            className="rounded bg-primary/10 px-1 text-primary underline-offset-2 hover:underline"
          >
            [{item.source_id}] &ldquo;{item.quote}&rdquo; · {source.title}
          </a>
        ) : null;
      })}
    </span>
  );
}

function ResearchResult({ research }: { research: AudienceResearch }) {
  const mix = [1, 2, 3]
    .map((tier) => `T${tier} ${research.sources.filter((source) => source.tier === tier).length}`)
    .join(" · ");

  return (
    <details className="rounded-md border border-border/70 bg-background/40 p-3 text-xs">
      <summary className="cursor-pointer font-medium text-foreground">
        Research v{research.version} · {research.sources.length} sources · {mix}
      </summary>
      <div className="mt-3 space-y-3 text-muted-foreground">
        <p>
          Researched {new Date(research.researched_at).toLocaleDateString()} ·{" "}
          {research.dropped_claims} unverifiable item
          {research.dropped_claims === 1 ? "" : "s"} dropped
        </p>

        {research.situation && (
          <div>
            <p className="font-medium text-foreground/80">Sourced situation</p>
            <p>
              {research.situation.text}
              <ResearchEvidenceLinks evidence={research.situation.evidence} research={research} />
            </p>
          </div>
        )}

        {research.problems.length > 0 && (
          <div>
            <p className="font-medium text-foreground/80">Verified problems</p>
            <ul className="mt-1 space-y-1">
              {research.problems.map((problem) => (
                <li key={problem.id}>
                  <span className="font-medium text-foreground/70">{problem.id}</span>{" "}
                  {problem.statement} · {problem.corroboration} domain
                  {problem.corroboration === 1 ? "" : "s"}
                  <ResearchEvidenceLinks evidence={problem.evidence} research={research} />
                  {problem.cost && <span> · {problem.cost}</span>}
                </li>
              ))}
            </ul>
          </div>
        )}

        {research.incumbent_behaviour.length > 0 && (
          <div>
            <p className="font-medium text-foreground/80">What they do now</p>
            <ul className="mt-1 space-y-1">
              {research.incumbent_behaviour.map((item, index) => (
                <li key={`${index}-${item.text}`}>
                  — {item.text}
                  <ResearchEvidenceLinks evidence={item.evidence} research={research} />
                </li>
              ))}
            </ul>
          </div>
        )}

        {research.triggers.length > 0 && (
          <div>
            <p className="font-medium text-foreground/80">Observed triggers</p>
            <ul className="mt-1 space-y-1">
              {research.triggers.map((item, index) => (
                <li key={`${index}-${item.text}`}>
                  — {item.text}
                  <ResearchEvidenceLinks evidence={item.evidence} research={research} />
                </li>
              ))}
            </ul>
          </div>
        )}

        {research.sophistication && research.sophistication_basis && (
          <div>
            <p className="font-medium text-foreground/80">Observed awareness</p>
            <p className="capitalize">
              {research.sophistication.replaceAll("_", " ")} ·{" "}
              <span className="normal-case">{research.sophistication_basis.text}</span>
              <ResearchEvidenceLinks
                evidence={research.sophistication_basis.evidence}
                research={research}
              />
            </p>
          </div>
        )}

        {research.buyer_phrases.length > 0 && (
          <div>
            <p className="font-medium text-foreground/80">Buyer language</p>
            <ul className="mt-1 space-y-1">
              {research.buyer_phrases.map((phrase, index) => (
                <li key={`${index}-${phrase.text}`}>
                  &ldquo;{phrase.text}&rdquo;
                  <ResearchEvidenceLinks evidence={[phrase.evidence]} research={research} />
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </details>
  );
}

const BAND_ORDER: RelevanceBand[] = ["LEAD", "SUPPORT", "CONTEXT", "WITHHOLD"];
const STALE_REASON: Record<string, string> = {
  knowledge_changed: "Product Knowledge changed",
  audience_research_changed: "Audience Research changed",
  market_scan_changed: "Market Scan changed",
  capability_profile_changed: "Product Capability Profile changed",
  company_qualification_changed: "Company qualifications changed",
};

const QUALIFICATION_VARIANT: Record<
  CompanyQualification["classification"],
  "default" | "secondary" | "destructive" | "outline"
> = {
  QUALIFIED: "default",
  ADJACENT: "secondary",
  EXCLUDED: "destructive",
  UNVERIFIED: "outline",
};

function DefinitionReceipt({ definition }: { definition: AudienceDefinition }) {
  const required = [
    ...definition.required_structural_signals,
    ...definition.required_workflow_signals,
  ];
  return (
    <details className="rounded-md border border-border/70 bg-background/40 p-3 text-xs">
      <summary className="cursor-pointer font-medium text-foreground">
        Qualification definition · schema v{definition.schema_version}
      </summary>
      <div className="mt-3 grid gap-3 text-muted-foreground sm:grid-cols-2">
        <div>
          <p className="font-medium text-foreground/80">Required company signals</p>
          {required.length > 0 ? (
            <ul className="mt-1 space-y-1">
              {required.map((item) => (
                <li key={item.code}>— {item.code}: {item.description}</li>
              ))}
            </ul>
          ) : (
            <p className="mt-1">None declared.</p>
          )}
        </div>
        <div>
          <p className="font-medium text-foreground/80">Required capabilities</p>
          <p className="mt-1">
            {definition.required_product_capabilities.join(" · ") || "None declared."}
          </p>
        </div>
        <div>
          <p className="font-medium text-foreground/80">Eligible subsegments</p>
          <p className="mt-1">{definition.eligible_subsegments.join(" · ") || "Not narrowed."}</p>
        </div>
        <div>
          <p className="font-medium text-foreground/80">Hard exclusions</p>
          {definition.hard_disqualifiers.length > 0 ? (
            <ul className="mt-1 space-y-1">
              {definition.hard_disqualifiers.map((item) => (
                <li key={item.code}>— {item.code}: {item.description}</li>
              ))}
            </ul>
          ) : (
            <p className="mt-1">None declared.</p>
          )}
        </div>
      </div>
    </details>
  );
}

function CapabilityProfileCard({
  brandId,
  initialProfile,
}: {
  brandId: string;
  initialProfile: ProductCapabilityProfile | null;
}) {
  const [profile, setProfile] = useState(initialProfile);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [states, setStates] = useState<Record<string, CapabilityState>>(
    Object.fromEntries(
      (initialProfile?.capabilities ?? []).map((item) => [item.id, item.state]),
    ),
  );

  async function derive() {
    setSaving(true);
    try {
      const next = await api.deriveCapabilityProfile(brandId);
      setProfile(next);
      setStates(Object.fromEntries(next.capabilities.map((item) => [item.id, item.state])));
      toast.success(`Capability profile v${next.version} is current`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not derive the profile");
    } finally {
      setSaving(false);
    }
  }

  async function save() {
    if (!profile) return;
    setSaving(true);
    try {
      const next = await api.saveCapabilityProfile(brandId, {
        capabilities: profile.capabilities.map((item) => ({
          ...item,
          state: states[item.id] ?? item.state,
        })),
        constraints: profile.constraints,
        claims: profile.claims,
      });
      setProfile(next);
      setStates(Object.fromEntries(next.capabilities.map((item) => [item.id, item.state])));
      setEditing(false);
      toast.success(`Saved capability profile v${next.version}`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not save the profile");
    } finally {
      setSaving(false);
    }
  }

  if (!profile) {
    return (
      <Card className="border-amber-500/30">
        <CardHeader className="flex flex-row items-center justify-between gap-3">
          <div>
            <CardTitle className="text-base">Product Capability Profile</CardTitle>
            <p className="mt-1 text-xs text-muted-foreground">
              No evidence-backed profile exists yet. Compile product knowledge first.
            </p>
          </div>
          <Button size="sm" variant="outline" onClick={derive} disabled={saving}>
            {saving ? "Checking…" : "Derive from evidence"}
          </Button>
        </CardHeader>
      </Card>
    );
  }

  const verified = profile.capabilities.filter((item) => item.state === "verified").length;
  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between gap-3">
        <div>
          <CardTitle className="text-base">Product Capability Profile v{profile.version}</CardTitle>
          <p className="mt-1 text-xs text-muted-foreground">
            {verified} of {profile.capabilities.length} capabilities verified · knowledge v
            {profile.knowledge_version}. Verified states and customer-facing claims require
            ledger evidence.
          </p>
        </div>
        <div className="flex gap-2">
          {editing ? (
            <>
              <Button size="sm" variant="ghost" onClick={() => setEditing(false)} disabled={saving}>
                Cancel
              </Button>
              <Button size="sm" onClick={save} disabled={saving}>
                {saving ? "Saving…" : "Save new version"}
              </Button>
            </>
          ) : (
            <>
              <Button size="sm" variant="ghost" onClick={derive} disabled={saving}>
                Refresh evidence
              </Button>
              <Button size="sm" variant="outline" onClick={() => setEditing(true)}>
                Edit states
              </Button>
            </>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-4 text-xs">
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {profile.capabilities.map((capability) => {
            const state = states[capability.id] ?? capability.state;
            return (
              <div key={capability.id} className="rounded-md border border-border/70 p-2">
                <div className="flex items-start justify-between gap-2">
                  <span className="font-medium">{capability.label}</span>
                  {editing ? (
                    <select
                      aria-label={`${capability.label} state`}
                      value={state}
                      onChange={(event) =>
                        setStates((current) => ({
                          ...current,
                          [capability.id]: event.target.value as CapabilityState,
                        }))
                      }
                      className="rounded border border-border bg-background px-1 py-0.5 text-[10px]"
                    >
                      <option value="verified">verified</option>
                      <option value="unsupported">unsupported</option>
                      <option value="unknown">unknown</option>
                    </select>
                  ) : (
                    <Badge variant={state === "verified" ? "default" : "outline"}>{state}</Badge>
                  )}
                </div>
                <p className="mt-1 font-mono text-[10px] text-muted-foreground">{capability.id}</p>
                {capability.note && <p className="mt-1 text-muted-foreground">{capability.note}</p>}
                {capability.evidence.map((item) => (
                  <details key={item.evidence_id} className="mt-2 text-muted-foreground">
                    <summary className="cursor-pointer">[{item.evidence_id}] {item.claim}</summary>
                    <blockquote className="mt-1 border-l-2 border-border pl-2">
                      &ldquo;{item.quote}&rdquo;
                    </blockquote>
                    <p>Source: {item.source_identifier || "product knowledge"}</p>
                  </details>
                ))}
              </div>
            );
          })}
        </div>
        {profile.constraints.length > 0 && (
          <div>
            <p className="font-medium">Scope boundaries</p>
            <ul className="mt-1 space-y-1 text-muted-foreground">
              {profile.constraints.map((item) => (
                <li key={item.id}>— {item.statement}</li>
              ))}
            </ul>
          </div>
        )}
        {profile.claims.length > 0 && (
          <div>
            <p className="font-medium">Claim inventory</p>
            <ul className="mt-1 space-y-1 text-muted-foreground">
              {profile.claims.map((claim, index) => (
                <li key={`${claim.text}-${index}`}>
                  <Badge variant="outline" className="mr-1">{claim.visibility}</Badge>
                  {claim.text} {claim.evidence_ids.length > 0 && `· ${claim.evidence_ids.join(", ")}`}
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

/**
 * One quote and where it came from. A missing quote is stated as missing
 * rather than rendered as an empty pair of quotation marks — an empty
 * blockquote reads as evidence that says nothing, which is a different and
 * much worse claim than evidence we never captured.
 */
function EvidenceQuote({
  quote,
  source,
}: {
  quote?: string | null;
  source?: string | null;
}) {
  const text = quote?.trim();
  const origin = source?.trim();
  return (
    <>
      {text ? (
        <blockquote className="mt-1 border-l-2 border-border pl-2 text-muted-foreground">
          &ldquo;{text}&rdquo;
        </blockquote>
      ) : (
        <p className="mt-1 border-l-2 border-dashed border-border/60 pl-2 italic text-muted-foreground/70">
          No quote recorded for this evidence.
        </p>
      )}
      {origin ? (
        /^https?:\/\//.test(origin) ? (
          <a
            href={origin}
            target="_blank"
            rel="noreferrer noopener"
            className="mt-1 block break-all text-primary hover:underline"
          >
            {origin}
          </a>
        ) : (
          <p className="mt-1 text-muted-foreground">Source: {origin}</p>
        )
      ) : (
        <p className="mt-1 italic text-muted-foreground/70">Source not recorded.</p>
      )}
    </>
  );
}

function DossierEvidenceReference({ evidence }: { evidence?: RelevanceEvidence }) {
  if (!evidence) return null;
  return (
    <details className="mt-1 rounded-md border border-border/60 bg-background/40 p-2">
      <summary className="cursor-pointer font-medium text-foreground/90">
        [{evidence.id}] {evidence.claim}
      </summary>
      <div className="mt-2 space-y-1 text-muted-foreground">
        <p className="capitalize">
          {evidence.category} · {evidence.kind} · {evidence.value_band}
        </p>
        <EvidenceQuote quote={evidence.verbatim} source={evidence.source} />
      </div>
    </details>
  );
}

function QualificationReceipt({ qualification }: { qualification: CompanyQualification }) {
  return (
    <div className="rounded-md border border-border/70 bg-background/40 p-3 text-xs">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-medium">Qualification receipt</span>
        <span className="text-muted-foreground">
          structure {qualification.audience_structure_fit} · capability {qualification.product_capability_fit}
          {" · "}evidence {qualification.evidence_completeness} · reachability {qualification.reachability}
        </span>
      </div>
      {qualification.reason_codes.length > 0 && (
        <p className="mt-2 text-muted-foreground">
          Reasons: {qualification.reason_codes.join(" · ")}
        </p>
      )}
      {qualification.hard_disqualifiers_triggered.length > 0 && (
        <p className="mt-2 text-destructive">
          Hard disqualifiers: {qualification.hard_disqualifiers_triggered.join(" · ")}
        </p>
      )}
      {qualification.capability_matches.length > 0 && (
        <div className="mt-2 space-y-2">
          {qualification.capability_matches.map((match, index) => (
            <div key={`${match.capability_id}-${index}`} className="rounded bg-muted/30 p-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="font-medium">
                  {match.display_name} <span className="font-mono text-[10px] text-muted-foreground">{match.capability_id}</span>
                </p>
                <Badge variant={match.product_capability_state === "unsupported" ? "destructive" : "outline"}>
                  product: {match.product_capability_state}
                </Badge>
              </div>
              <EvidenceQuote quote={match.quote} source={match.source_url} />
              <p className="mt-1 font-mono text-[10px] text-muted-foreground">
                {match.reason_code}
              </p>
            </div>
          ))}
        </div>
      )}
      {qualification.unmapped_requirements.length > 0 && (
        <div className="mt-2 space-y-2">
          {qualification.unmapped_requirements.map((requirement, index) => (
            <div key={`${requirement.raw_requirement}-${index}`} className="rounded bg-amber-500/10 p-2">
              <p className="font-medium">Unmapped requirement: {requirement.raw_requirement}</p>
              <EvidenceQuote quote={requirement.quote} source={requirement.source_url} />
            </div>
          ))}
        </div>
      )}
      {qualification.evidence.length > 0 && (
        <div className="mt-2 space-y-2">
          {qualification.evidence.map((signal, index) => (
            <div key={`${signal.code}-${index}`} className="rounded bg-muted/30 p-2">
              <p className="font-medium">
                {signal.code} = {signal.value} · {signal.grounding}
              </p>
              {signal.quote && (
                <blockquote className="mt-1 border-l-2 border-border pl-2 text-muted-foreground">
                  &ldquo;{signal.quote}&rdquo;
                </blockquote>
              )}
              {signal.source_identifier && (
                /^https?:\/\//.test(signal.source_identifier) ? (
                  <a
                    href={signal.source_identifier}
                    target="_blank"
                    rel="noreferrer noopener"
                    className="mt-1 block break-all text-primary hover:underline"
                  >
                    {signal.source_identifier}
                  </a>
                ) : (
                  <p className="mt-1 text-muted-foreground">Source: {signal.source_identifier}</p>
                )
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ClaimList({
  title,
  note,
  tone,
  empty,
  claims,
}: {
  title: string;
  note: string;
  tone: string;
  empty: string;
  claims: ContractClaim[];
}) {
  return (
    <div>
      <p className={cn("font-medium", tone)}>
        {title} · {claims.length}
      </p>
      <p className="text-[11px] text-muted-foreground/80">{note}</p>
      <ul className="mt-1 space-y-1">
        {claims.map((claim) => (
          <li key={claim.id} title={claim.reason}>
            — {claim.text}
          </li>
        ))}
        {claims.length === 0 && (
          <li className="italic text-muted-foreground/70">{empty}</li>
        )}
      </ul>
    </div>
  );
}

/**
 * The claim contract, as three mutually exclusive sets plus the inventory they
 * were drawn from. The separation is the point: forbidden is what is not true
 * of us, withheld is what we are choosing not to spend here, and only the
 * campaign-safe set is ever handed to a writer.
 */
function ClaimContractView({
  recommendation,
}: {
  recommendation: CampaignRecommendation;
}) {
  const contract = recommendation.claim_contract;

  if (!contract) {
    // Persisted before the contract existed. Show what this dossier actually
    // has rather than inventing a contract for it, and say so.
    return (
      <div className="space-y-2">
        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <p className="font-medium text-foreground/80">
              Allowed claims · {recommendation.allowed_claims.length}
            </p>
            <ul className="mt-1 space-y-1">
              {recommendation.allowed_claims.map((claim) => (
                <li key={claim}>— {claim}</li>
              ))}
              {recommendation.allowed_claims.length === 0 && (
                <li className="italic text-muted-foreground/70">None licensed.</li>
              )}
            </ul>
          </div>
          <div>
            <p className="font-medium text-foreground/80">
              Forbidden claims · {recommendation.forbidden_claims.length}
            </p>
            <ul className="mt-1 space-y-1">
              {recommendation.forbidden_claims.map((claim) => (
                <li key={claim}>— {claim}</li>
              ))}
              {recommendation.forbidden_claims.length === 0 && (
                <li className="italic text-muted-foreground/70">None added.</li>
              )}
            </ul>
          </div>
        </div>
        <p className="italic text-muted-foreground/70">
          This dossier was built before the claim contract, so its two lists are not
          guaranteed to be disjoint. Regenerate it to get the stricter separation.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="grid gap-3 sm:grid-cols-3">
        <ClaimList
          title="Campaign-safe claims"
          note="The only claims the writer receives."
          tone="text-foreground/80"
          empty="None licensed for this audience."
          claims={contract.campaign_allowed_claims}
        />
        <ClaimList
          title="Forbidden"
          note="Not true of us. Never sayable."
          tone="text-destructive"
          empty="None added."
          claims={contract.forbidden_claims}
        />
        <ClaimList
          title="Withheld"
          note="Arguable, deliberately unspent here."
          tone="text-amber-500"
          empty="Nothing held back."
          claims={contract.withheld_claims}
        />
      </div>
      {contract.warnings.length > 0 && (
        <details className="rounded-md border border-amber-500/40 bg-amber-500/5 p-2">
          <summary className="cursor-pointer font-medium text-amber-500">
            Contract warnings · {contract.warnings.length}
          </summary>
          <ul className="mt-2 space-y-1">
            {contract.warnings.map((warning) => (
              <li key={warning}>— {warning}</li>
            ))}
          </ul>
        </details>
      )}
      <details className="rounded-md border border-border/60 bg-background/40 p-2">
        <summary className="cursor-pointer font-medium text-foreground/90">
          Full verified product facts · {contract.verified_product_claims.length}
        </summary>
        <p className="mt-1 text-[11px] text-muted-foreground/80">
          Everything the product knowledge establishes, campaign-safe or not. This is
          the inventory the three sets above were drawn from, not a list of things
          this campaign may say.
        </p>
        <ul className="mt-2 space-y-1">
          {contract.verified_product_claims.map((claim) => (
            <li key={claim.id} title={claim.reason}>
              — {claim.text}
              {claim.evidence_ids.length > 0 && (
                <span className="ml-1 font-mono text-[10px] text-muted-foreground">
                  [{claim.evidence_ids.join(", ")}]
                </span>
              )}
            </li>
          ))}
          {contract.verified_product_claims.length === 0 && (
            <li className="italic text-muted-foreground/70">
              No product claims recorded.
            </li>
          )}
        </ul>
      </details>
    </div>
  );
}

function DossierResult({
  research,
  relevance,
}: {
  research: AudienceResearch;
  relevance: RelevanceDossierStatus;
}) {
  const dossier = relevance.dossier;
  if (!dossier) return null;
  const evidence = new Map(dossier.evidence.map((item) => [item.id, item]));
  const problems = new Map(research.problems.map((problem) => [problem.id, problem]));

  return (
    <details className="rounded-md border border-primary/30 bg-primary/5 p-3 text-xs">
      <summary className="flex cursor-pointer list-none flex-wrap items-center gap-2 font-medium">
        Relevance dossier v{relevance.generation_version}
        <Badge variant={relevance.status === "stale" ? "destructive" : "secondary"}>
          {relevance.status}
        </Badge>
      </summary>
      <div className="mt-3 space-y-4 text-muted-foreground">
        {dossier.recommendation && (
          <div
            className={cn(
              "space-y-3 rounded-md border p-3",
              dossier.recommendation.readiness === "NO_GO" ||
                dossier.recommendation.readiness === "DISCOVERY_ONLY"
                ? "border-amber-500/50 bg-amber-500/10"
                : "border-primary/40 bg-primary/10",
            )}
          >
            {/*
              One label. `readiness` is the same verdict under a second name —
              the two were rendered side by side and read as "NOT RECOMMENDEDNO
              GO", which looked like two findings rather than one.
            */}
            <div className="flex flex-wrap items-center gap-2">
              <Badge
                variant={
                  dossier.recommendation.state === "NOT_RECOMMENDED"
                    ? "destructive"
                    : "default"
                }
              >
                {dossier.recommendation.state.replaceAll("_", " ")}
              </Badge>
            </div>
            <ul className="space-y-1">
              {dossier.recommendation.reasons.map((reason) => (
                <li key={reason}>— {reason}</li>
              ))}
            </ul>
            {dossier.recommendation.eligible_subsegment && (
              <p>Eligible subsegment: {dossier.recommendation.eligible_subsegment}</p>
            )}
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
              {(
                [
                  ["Qualified", dossier.recommendation.qualified_companies],
                  ["Adjacent", dossier.recommendation.adjacent_companies],
                  ["Excluded", dossier.recommendation.excluded_companies],
                  ["Unverified", dossier.recommendation.unverified_companies],
                ] as const
              ).map(([label, companies]) => (
                <div key={label} className="rounded bg-background/50 p-2">
                  <p className="font-medium text-foreground/80">{label} · {companies.length}</p>
                  {companies.map((company) => (
                    <p key={company.prospect_id} className="mt-1">
                      {company.name}
                      {company.hard_disqualifiers_triggered.length > 0 &&
                        ` · ${company.hard_disqualifiers_triggered.join(", ")}`}
                    </p>
                  ))}
                </div>
              ))}
            </div>
            <ClaimContractView recommendation={dossier.recommendation} />
            {dossier.recommendation.unresolved_objections.length > 0 && (
              <p>
                Unresolved objections: {dossier.recommendation.unresolved_objections.join(" · ")}
              </p>
            )}
            <p className="font-medium text-foreground/80">
              Next: {dossier.recommendation.recommended_next_action}
            </p>
            {dossier.recommendation.override_risk && (
              <p className="text-amber-300">Override risk: {dossier.recommendation.override_risk}</p>
            )}
          </div>
        )}
        {dossier.orientation && (
          <p className="text-sm font-medium text-foreground">{dossier.orientation}</p>
        )}

        <div className="space-y-1 font-mono text-[10px]">
          <p>Knowledge v{dossier.knowledge_version} · {dossier.knowledge_id}</p>
          <p>
            Audience research v{dossier.audience_research_version} ·{" "}
            {dossier.audience_research_id}
          </p>
          <p>Market scan v{dossier.market_scan_version} · {dossier.market_scan_id}</p>
          {dossier.capability_profile_id && (
            <p>
              Capability profile v{dossier.capability_profile_version} · {dossier.capability_profile_id}
            </p>
          )}
          {dossier.qualification_fingerprint && (
            <p>Qualification set · {dossier.qualification_fingerprint}</p>
          )}
          <p className="font-sans">
            Built {new Date(dossier.built_at).toLocaleString()}
          </p>
        </div>

        {relevance.stale_reasons.length > 0 && (
          <div className="rounded-md bg-destructive/10 p-2 text-destructive">
            <p className="font-medium">Refresh needed</p>
            <ul className="mt-1 space-y-0.5">
              {relevance.stale_reasons.map((reason) => (
                <li key={reason}>— {STALE_REASON[reason] ?? reason.replaceAll("_", " ")}</li>
              ))}
            </ul>
          </div>
        )}

        {BAND_ORDER.map((band) => {
          const items = dossier.ranked_relevance.filter((item) => item.band === band);
          if (items.length === 0) return null;
          return (
            <div key={band}>
              <p className="font-medium text-foreground/80">{band}</p>
              <ul className="mt-1 space-y-2">
                {items.map((item) => (
                  <li key={item.evidence_id}>
                    <p>
                      {item.why}
                      {item.territory && (
                        <Badge variant="outline" className="ml-1 capitalize">
                          {item.territory.replaceAll("_", " ")}
                        </Badge>
                      )}
                    </p>
                    {item.problem_ids.length > 0 && (
                      <p className="mt-0.5">
                        Problems: {item.problem_ids.join(", ")}
                      </p>
                    )}
                    <DossierEvidenceReference evidence={evidence.get(item.evidence_id)} />
                  </li>
                ))}
              </ul>
            </div>
          );
        })}

        {dossier.problem_fits.length > 0 && (
          <div>
            <p className="font-medium text-foreground/80">Problem fits</p>
            <ul className="mt-1 space-y-2">
              {dossier.problem_fits.map((fit) => (
                <li key={fit.problem_id} className="rounded-md bg-background/40 p-2">
                  <p>
                    <Badge variant="outline">{fit.verdict}</Badge>{" "}
                    <span className="text-foreground/80">
                      {fit.problem_id} · {problems.get(fit.problem_id)?.statement}
                    </span>
                  </p>
                  {fit.why && <p className="mt-1">{fit.why}</p>}
                  {fit.caveat && <p className="mt-1 text-amber-300">Caveat: {fit.caveat}</p>}
                  {fit.materiality_basis && <p className="mt-1">{fit.materiality_basis}</p>}
                  {fit.evidence_ids.map((id) => (
                    <DossierEvidenceReference key={id} evidence={evidence.get(id)} />
                  ))}
                </li>
              ))}
            </ul>
          </div>
        )}

        {dossier.segment_objections.length > 0 && (
          <div>
            <p className="font-medium text-foreground/80">Segment-specific objections</p>
            <ul className="mt-1 space-y-2">
              {dossier.segment_objections.map((objection) => (
                <li key={objection.objection}>
                  <p className="text-foreground/80">{objection.objection}</p>
                  <p>
                    {objection.answer
                      ? `Licensed answer: ${objection.answer}`
                      : "No licensed answer in the current product material."}
                  </p>
                  {objection.evidence_ids.map((id) => (
                    <DossierEvidenceReference key={id} evidence={evidence.get(id)} />
                  ))}
                </li>
              ))}
            </ul>
          </div>
        )}

        {dossier.silences.length > 0 && (
          <div>
            <p className="font-medium text-foreground/80">Unsupported audience needs</p>
            <ul className="mt-1 space-y-2">
              {dossier.silences.map((silence) => (
                <li key={silence.problem_id}>
                  <p className="text-foreground/80">
                    {silence.problem_id} · {problems.get(silence.problem_id)?.statement}
                  </p>
                  <p>{silence.reason}</p>
                  {silence.question && <p className="text-amber-300">Ask: {silence.question}</p>}
                </li>
              ))}
            </ul>
          </div>
        )}

        <div>
          <p>
            Validation: {dossier.validation_counts.dropped_items} dropped ·{" "}
            {dossier.validation_counts.normalized_items} normalized
          </p>
          {dossier.validation_warnings.length > 0 && (
            <ul className="mt-1 space-y-0.5">
              {dossier.validation_warnings.map((warning) => (
                <li key={warning}>— {warning}</li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </details>
  );
}

/** The audience form.
 *
 * Four required lines, and they are four rather than one free-text paragraph
 * because they are exactly what the backend's admission check reads as a
 * situation rather than a category. `signals` and `where` sit beside them
 * marked for what they unlock: they are what a research pass actually spends
 * its search on, and an audience without them saves fine and comes back with a
 * receipt saying so. That receipt is the same code path a mapped audience goes
 * through, which is why nothing here re-implements the rule. */
const KIND_OPTIONS: SegmentKind[] = [
  "core",
  "adjacent",
  "influencer",
  "channel",
  "triggered",
  "unintended",
];

const SOPHISTICATION_OPTIONS: { value: string; label: string }[] = [
  { value: "unaware", label: "Does not know they have the problem" },
  { value: "problem_aware", label: "Knows the problem, not the solutions" },
  { value: "solution_aware", label: "Knows solutions like this exist" },
  { value: "product_aware", label: "Knows this product" },
  { value: "most_aware", label: "Ready to decide" },
];

type AudienceDraft = Record<string, string>;

const EMPTY_DRAFT: AudienceDraft = {
  name: "",
  organization: "",
  workflow: "",
  need: "",
  signals: "",
  where: "",
  kind: "core",
  sophistication: "problem_aware",
  who: "",
  why_them: "",
  trigger: "",
  pains: "",
  objection: "",
  angle: "",
  population: "",
  buyer_role: "",
  user_role: "",
  current_alternative: "",
};

/** One line per entry, blanks dropped. Blank entries are typing rather than
 * content, and admission counts signals — a blank one would count. */
function listOf(value: string): string[] {
  return value
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
}

function draftOf(segment: MappedSegment): AudienceDraft {
  return {
    ...EMPTY_DRAFT,
    name: segment.name,
    organization: segment.organization,
    workflow: segment.workflow,
    need: segment.need,
    signals: segment.signals.join("\n"),
    where: segment.where.join("\n"),
    kind: segment.kind,
    sophistication: segment.sophistication,
    who: segment.who,
    why_them: segment.why_them,
    trigger: segment.trigger,
    pains: segment.pains.join("\n"),
    objection: segment.objection,
    angle: segment.angle,
    population: segment.population,
    buyer_role: segment.buyer_role,
    user_role: segment.user_role,
    current_alternative: segment.current_alternative,
  };
}

function requestOf(draft: AudienceDraft): Partial<UserAudienceInput> {
  return {
    ...draft,
    kind: draft.kind as SegmentKind,
    signals: listOf(draft.signals),
    where: listOf(draft.where),
    pains: listOf(draft.pains),
  } as Partial<UserAudienceInput>;
}

const FIELD_CLASS = "w-full rounded-md border bg-background p-2 text-sm";

function AudienceField({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block space-y-1">
      <span className="text-sm font-medium">{label}</span>
      {children}
      {hint && <span className="block text-xs text-muted-foreground">{hint}</span>}
    </label>
  );
}

function AudienceForm({
  brandId,
  initial,
  onSaved,
  onCancel,
}: {
  brandId: string;
  initial?: MappedSegment;
  onSaved: () => void;
  onCancel: () => void;
}) {
  const [draft, setDraft] = useState<AudienceDraft>(
    initial ? draftOf(initial) : EMPTY_DRAFT,
  );
  const [saving, setSaving] = useState(false);
  const editing = Boolean(initial);
  const ready = ["name", "organization", "workflow", "need"].every((key) =>
    draft[key].trim(),
  );

  function set(key: string) {
    return (
      event: React.ChangeEvent<
        HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement
      >,
    ) => setDraft((current) => ({ ...current, [key]: event.target.value }));
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!ready || saving) return;
    setSaving(true);
    try {
      const body = requestOf(draft);
      const saved = editing
        ? await api.updateAudience(brandId, body)
        : await api.addAudience(brandId, body);
      // The receipt, not a cheerful confirmation: the useful thing to know on
      // save is whether this can be researched yet, and if not, exactly what
      // is missing. The words are the backend's own.
      if (saved.researchable) {
        toast.success(`${saved.name} is ready to research.`);
      } else {
        toast(`${saved.name} saved.`, {
          description: saved.researchability_reasons.join(" "),
        });
      }
      onSaved();
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Could not save that audience",
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <div className="space-y-3">
        <AudienceField
          label="Call them"
          hint="The name research, prospect lists and campaigns will know them by."
        >
          <input
            className={FIELD_CLASS}
            value={draft.name}
            maxLength={120}
            disabled={saving || editing}
            placeholder="Shopify warranty desks"
            onChange={set("name")}
          />
        </AudienceField>
        {editing && (
          <p className="text-xs text-muted-foreground">
            The name stays as it is. Research versions, prospects and campaigns all
            point at this audience by name, and renaming it would orphan them.
          </p>
        )}
        <AudienceField
          label="Who they are"
          hint="A situation, not a category. Not “e-commerce”."
        >
          <input
            className={FIELD_CLASS}
            value={draft.organization}
            maxLength={400}
            disabled={saving}
            placeholder="three-person Shopify stores selling refurbished laptops"
            onChange={set("organization")}
          />
        </AudienceField>
        <AudienceField
          label="What they are doing when this matters"
          hint="The work the problem happens inside."
        >
          <input
            className={FIELD_CLASS}
            value={draft.workflow}
            maxLength={400}
            disabled={saving}
            placeholder="answering warranty questions by hand out of a shared inbox"
            onChange={set("workflow")}
          />
        </AudienceField>
        <AudienceField label="What they need to change about it">
          <input
            className={FIELD_CLASS}
            value={draft.need}
            maxLength={400}
            disabled={saving}
            placeholder="cut the time each warranty ticket takes"
            onChange={set("need")}
          />
        </AudienceField>
      </div>

      <div className="space-y-3 rounded-lg border border-dashed p-3">
        <p className="text-xs text-muted-foreground">
          These two are what a research pass spends its search on. Leave them empty
          and this saves anyway — it just cannot be researched or prospected until
          somebody fills them in.
        </p>
        <AudienceField
          label="How you recognise one from the outside"
          hint="One per line. Something you could look at without asking them."
        >
          <textarea
            className={FIELD_CLASS}
            rows={2}
            value={draft.signals}
            disabled={saving}
            placeholder="their storefront has a published warranty page with an email address"
            onChange={set("signals")}
          />
        </AudienceField>
        <AudienceField
          label="Where they are findable in bulk"
          hint={
            "One per line. A named directory, register or exhibitor list — " +
            "“LinkedIn” on its own is refused."
          }
        >
          <textarea
            className={FIELD_CLASS}
            rows={2}
            value={draft.where}
            disabled={saving}
            placeholder="Shopify app store reviews for warranty apps"
            onChange={set("where")}
          />
        </AudienceField>
      </div>

      <details className="rounded-lg border p-3">
        <summary className="cursor-pointer text-sm font-medium">
          More detail (optional)
        </summary>
        <p className="mt-2 text-xs text-muted-foreground">
          None of this is needed to save or to research. It is what makes a campaign
          to this buyer read differently from a campaign to any other, and it can be
          added later.
        </p>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <AudienceField label="How you arrived at them">
            <select
              className={FIELD_CLASS}
              value={draft.kind}
              disabled={saving}
              onChange={set("kind")}
            >
              {KIND_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {KIND_LABELS[option]}
                </option>
              ))}
            </select>
          </AudienceField>
          <AudienceField label="How much they already know">
            <select
              className={FIELD_CLASS}
              value={draft.sophistication}
              disabled={saving}
              onChange={set("sophistication")}
            >
              {SOPHISTICATION_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </AudienceField>
          <AudienceField label="One of them, in a sentence">
            <input
              className={FIELD_CLASS}
              value={draft.who}
              maxLength={600}
              disabled={saving}
              onChange={set("who")}
            />
          </AudienceField>
          <AudienceField label="Why this product matters to them">
            <input
              className={FIELD_CLASS}
              value={draft.why_them}
              maxLength={600}
              disabled={saving}
              onChange={set("why_them")}
            />
          </AudienceField>
          <AudienceField label="What starts them looking">
            <input
              className={FIELD_CLASS}
              value={draft.trigger}
              maxLength={400}
              disabled={saving}
              onChange={set("trigger")}
            />
          </AudienceField>
          <AudienceField label="The line to open on">
            <input
              className={FIELD_CLASS}
              value={draft.angle}
              maxLength={600}
              disabled={saving}
              onChange={set("angle")}
            />
          </AudienceField>
          <AudienceField label="What it costs them today" hint="One per line.">
            <textarea
              className={FIELD_CLASS}
              rows={2}
              value={draft.pains}
              disabled={saving}
              onChange={set("pains")}
            />
          </AudienceField>
          <AudienceField label="Why they would say no">
            <input
              className={FIELD_CLASS}
              value={draft.objection}
              maxLength={600}
              disabled={saving}
              onChange={set("objection")}
            />
          </AudienceField>
          <AudienceField label="Who signs" hint="The decision maker.">
            <input
              className={FIELD_CLASS}
              value={draft.buyer_role}
              maxLength={200}
              disabled={saving}
              onChange={set("buyer_role")}
            />
          </AudienceField>
          <AudienceField label="Who uses it day to day">
            <input
              className={FIELD_CLASS}
              value={draft.user_role}
              maxLength={200}
              disabled={saving}
              onChange={set("user_role")}
            />
          </AudienceField>
          <AudienceField label="What they do instead today">
            <input
              className={FIELD_CLASS}
              value={draft.current_alternative}
              maxLength={400}
              disabled={saving}
              onChange={set("current_alternative")}
            />
          </AudienceField>
          <AudienceField label="How many of them" hint="Vague is fine; invented precision is not.">
            <input
              className={FIELD_CLASS}
              value={draft.population}
              maxLength={200}
              disabled={saving}
              placeholder="roughly 12,000 UK stores"
              onChange={set("population")}
            />
          </AudienceField>
        </div>
      </details>

      <div className="flex items-center gap-2">
        <Button type="submit" size="sm" disabled={!ready || saving}>
          {saving ? "Saving…" : editing ? "Save changes" : "Add audience"}
        </Button>
        <Button type="button" size="sm" variant="ghost" disabled={saving} onClick={onCancel}>
          Cancel
        </Button>
      </div>
    </form>
  );
}

/** The way in for somebody who already knows who they sell to.
 *
 * Open by default when nothing has been mapped, because that is the state
 * where describing the buyer beats buying a search to be told what the user
 * already knew. */
function AudienceAdder({
  brandId,
  defaultOpen,
  onSaved,
}: {
  brandId: string;
  defaultOpen: boolean;
  onSaved: () => void;
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between gap-4">
        <div>
          <CardTitle className="text-base">Add an audience yourself</CardTitle>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
            Four lines, no model call, no search. What you add stays on this map
            through every rescan, and it is researched, prospected and written to
            exactly like an audience the search found.
          </p>
        </div>
        {!open && (
          <Button size="sm" variant="outline" onClick={() => setOpen(true)}>
            Add an audience
          </Button>
        )}
      </CardHeader>
      {open && (
        <CardContent>
          <AudienceForm
            brandId={brandId}
            onSaved={() => {
              setOpen(false);
              onSaved();
            }}
            onCancel={() => setOpen(false)}
          />
        </CardContent>
      )}
    </Card>
  );
}


/** One mapped buyer.
 *
 * `basis` is given as much room as the rate, deliberately. The number on its
 * own is a claim the user can only over-trust or ignore; the number next to
 * the reasoning that produced it is one they can correct in ten seconds — and
 * they are the person in the room who actually knows this market. */
function SegmentCard({
  brandId,
  segment,
  selected,
  prospects,
  research,
  relevance,
  onSelect,
  onProspect,
  onResearch,
  onDossier,
  onChanged,
  busy,
}: {
  brandId: string;
  segment: MappedSegment;
  selected: boolean;
  prospects: number;
  research?: AudienceResearch;
  relevance?: RelevanceDossierStatus;
  onSelect: () => void;
  onProspect: () => void;
  onResearch: () => void;
  onDossier: (rebuild: boolean) => void;
  onChanged: () => void;
  busy: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const [editing, setEditing] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [removing, setRemoving] = useState(false);
  const mine = segment.added_by === "user";

  async function remove() {
    setRemoving(true);
    try {
      await api.deleteAudience(brandId, segment.name);
      toast.success(`${segment.name} removed. Its research is still on file.`);
      onChanged();
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Could not remove that audience",
      );
      setRemoving(false);
      setConfirming(false);
    }
  }

  if (editing) {
    return (
      <Card className="ring-1 ring-primary/50">
        <CardHeader>
          <CardTitle className="text-base">Editing {segment.name}</CardTitle>
        </CardHeader>
        <CardContent>
          <AudienceForm
            brandId={brandId}
            initial={segment}
            onSaved={() => {
              setEditing(false);
              onChanged();
            }}
            onCancel={() => setEditing(false)}
          />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={cn(selected && "ring-1 ring-primary/50")}>
      <CardHeader className="flex flex-row items-start justify-between gap-3">
        <button type="button" onClick={onSelect} className="min-w-0 space-y-1 text-left">
          <CardTitle className="text-base">{segment.name}</CardTitle>
          <p className="text-xs text-muted-foreground">
            {KIND_LABELS[segment.kind] ?? segment.kind}
            {segment.population ? ` · ${segment.population}` : ""}
          </p>
        </button>
        <div className="flex shrink-0 flex-col items-end gap-1">
          {mine && <Badge variant="outline">You added this</Badge>}
          <Badge
            variant={segment.researchable ? "secondary" : "destructive"}
            className="capitalize"
          >
            {researchabilityLabel(segment.researchability)}
          </Badge>
          <Badge variant={segment.assessment.priority === "incompatible" ? "destructive" : "secondary"}>
            {segment.assessment.priority === "explore_first" ? "Explore first" : segment.assessment.priority === "incompatible" ? "Incompatible" : "Hypothesis"}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="space-y-3 text-sm">
        {(segment.who || segment.organization) && (
          <p className="text-foreground/90">{segment.who || segment.organization}</p>
        )}
        <p className="text-xs text-muted-foreground">
          Product compatibility: {segment.assessment.compatibility} · Need evidence: {segment.assessment.evidence_strength}
        </p>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          aria-expanded={expanded}
          onClick={() => setExpanded((current) => !current)}
        >
          {expanded ? "Show less" : "Show more"}
        </Button>
        {expanded && (
          <div className="space-y-3">
            {segment.organization && (
              <p className="text-xs">Who they are: {segment.organization}</p>
            )}
            {segment.workflow && (
              <p className="text-xs">What they are doing: {segment.workflow}</p>
            )}
            {segment.need && <p className="text-xs">What they need: {segment.need}</p>}
            {segment.user_role && <p className="text-xs">User: {segment.user_role}</p>}
            {segment.buyer_role && <p className="text-xs">Decision maker: {segment.buyer_role}</p>}
            {segment.current_alternative && <p className="text-xs">Current workaround: {segment.current_alternative}</p>}
            {segment.why_them && (
              <p className="text-muted-foreground">Why them: {segment.why_them}</p>
            )}
            {segment.trigger && (
              <p className="text-muted-foreground">What starts them looking: {segment.trigger}</p>
            )}
            {segment.angle && (
              <p className="rounded-md bg-muted/40 p-2 text-xs">
                Open on: <span className="text-foreground">{segment.angle}</span>
              </p>
            )}
            {segment.objection && (
              <p className="text-xs text-muted-foreground">
                They say no because: {segment.objection}
              </p>
            )}
            {segment.basis && (
              <p className="text-xs text-muted-foreground">
                Commercial hypothesis: {segment.basis}
              </p>
            )}
            {segment.assessment.reasons.length > 0 && (
              <ul className="space-y-1 text-xs text-muted-foreground">
                {segment.assessment.reasons.map((reason, i) => <li key={i}>{reason}</li>)}
              </ul>
            )}
            {segment.assessment.evidence.length > 0 && (
              <details className="rounded-md border p-3 text-xs">
                <summary className="cursor-pointer font-medium">Verified quotations ({segment.assessment.evidence.length})</summary>
                <p className="mt-2 text-muted-foreground">The quotation is verified. Its interpretation and purchase intent remain hypotheses.</p>
                {segment.assessment.evidence.map((evidence, i) => (
                  <div key={i} className="mt-3 space-y-1 border-t pt-2">
                    <p>{evidence.kind}: {evidence.claim}</p>
                    <blockquote className="border-l-2 pl-2 text-muted-foreground">{evidence.quote}</blockquote>
                    <a className="break-all text-primary underline" href={evidence.url} target="_blank" rel="noopener noreferrer">{evidence.url}</a>
                    {evidence.fetched_at && <p className="text-muted-foreground">Fetched {new Date(evidence.fetched_at).toLocaleDateString()}</p>}
                  </div>
                ))}
              </details>
            )}
            {segment.assessment.unknowns.length > 0 && (
              <div className="rounded-md bg-amber-500/10 p-3 text-xs text-amber-200">
                <p className="font-medium">Still to verify</p>
                <ul className="mt-1 space-y-1">{segment.assessment.unknowns.map((item, i) => <li key={i}>{item}</li>)}</ul>
              </div>
            )}

            <div
              className={cn(
                "rounded-md p-2 text-xs",
                segment.researchable
                  ? "bg-muted/40 text-muted-foreground"
                  : "bg-destructive/10 text-destructive",
              )}
            >
              <p className="font-medium text-foreground">
                {segment.researchable ? "Worth researching" : "Do not spend research here yet"}
              </p>
              <ul className="mt-1 space-y-0.5">
                {segment.researchability_reasons.map((reason) => (
                  <li key={reason}>— {reason}</li>
                ))}
              </ul>
            </div>

            {segment.signals.length > 0 && (
              <div className="space-y-1">
                <p className="text-xs font-medium text-foreground/70">
                  How you recognise one from the outside
                </p>
                <ul className="space-y-0.5 text-xs text-muted-foreground">
                  {segment.signals.slice(0, 4).map((signal) => (
                    <li key={signal}>— {signal}</li>
                  ))}
                </ul>
              </div>
            )}
            {segment.where.length > 0 && (
              <p className="text-xs text-muted-foreground">
                Findable at: {segment.where.slice(0, 3).join(" · ")}
              </p>
            )}

            <DefinitionReceipt definition={segment.definition} />

            {research && <ResearchResult research={research} />}

            {research && relevance && relevance.missing_prerequisites.length > 0 && (
              <div className="rounded-md bg-amber-500/10 p-2 text-xs text-amber-300">
                <p className="font-medium">Relevance dossier unavailable</p>
                <ul className="mt-1 space-y-0.5">
                  {relevance.missing_prerequisites.map((item) => (
                    <li key={item.code}>— {item.message}</li>
                  ))}
                </ul>
              </div>
            )}

            {research && relevance && (
              <DossierResult research={research} relevance={relevance} />
            )}

          </div>
        )}

        <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
          <span className="text-xs text-muted-foreground">
            {prospects > 0
              ? `${prospects} organisation${prospects === 1 ? "" : "s"} found`
              : "nobody named yet"}
          </span>
          <div className="flex flex-wrap gap-2">
            {mine && !confirming && (
              <Button
                size="sm"
                variant="ghost"
                disabled={removing}
                onClick={() => setConfirming(true)}
              >
                Remove
              </Button>
            )}
            {mine && confirming && (
              <>
                <Button
                  size="sm"
                  variant="destructive"
                  disabled={removing}
                  onClick={remove}
                >
                  {removing ? "Removing…" : "Really remove"}
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={removing}
                  onClick={() => setConfirming(false)}
                >
                  Keep
                </Button>
              </>
            )}
            {mine && (
              <Button size="sm" variant="outline" onClick={() => setEditing(true)}>
                Edit
              </Button>
            )}
            {research && (
              <Button
                size="sm"
                variant={relevance?.dossier ? "outline" : "default"}
                disabled={
                  busy || !relevance || relevance.missing_prerequisites.length > 0
                }
                onClick={() => onDossier(Boolean(relevance?.dossier))}
              >
                {busy
                  ? "Working…"
                  : relevance?.dossier
                    ? "Rebuild dossier"
                    : "Generate relevance dossier"}
              </Button>
            )}
            <Button
              size="sm"
              disabled={busy || !segment.researchable}
              title={
                segment.researchable
                  ? undefined
                  : segment.researchability_reasons.join(" ")
              }
              onClick={onResearch}
            >
              {busy ? "Working…" : research ? "Refresh research" : "Research audience"}
            </Button>
            <Button
              size="sm"
              variant="outline"
              disabled={busy || !segment.researchable}
              title={
                segment.researchable
                  ? undefined
                  : "This audience needs a concrete signal, venue, and situation before research"
              }
              onClick={onProspect}
            >
              {busy ? "Working…" : "Find these companies"}
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

/** One named organisation.
 *
 * Every address on this card was found on a page the server fetched and
 * checked back against it — an invented one never gets this far. That is what
 * makes the copy button honest, and it is why `invented_contacts` is shown
 * rather than swallowed: a row that had to discard three is a row whose other
 * claims deserve the same suspicion. */
function ProspectCard({
  brandId,
  prospect,
  onDecided,
}: {
  brandId: string;
  prospect: Prospect;
  onDecided: (updated: Prospect) => void;
}) {
  const [deciding, setDeciding] = useState(false);

  async function decide(status: "kept" | "dismissed") {
    setDeciding(true);
    try {
      onDecided(await api.decideProspect(brandId, prospect.id, status));
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not save that");
    } finally {
      setDeciding(false);
    }
  }

  return (
    <Card className={cn(prospect.status === "dismissed" && "opacity-50")}>
      <CardHeader className="flex flex-row items-start justify-between gap-3">
        <div className="min-w-0 space-y-1">
          <CardTitle className="text-base">
            <a
              href={prospect.url}
              target="_blank"
              rel="noreferrer noopener"
              className="hover:underline"
            >
              {prospect.name}
            </a>
          </CardTitle>
          <p className="text-xs text-muted-foreground">
            {prospect.what_they_do || prospect.segment}
          </p>
        </div>
        {prospect.qualification ? (
          <Badge variant={QUALIFICATION_VARIANT[prospect.qualification.classification]}>
            {prospect.qualification.classification}
          </Badge>
        ) : prospect.fit !== null ? (
          <Badge variant={prospect.fit >= 0.7 ? "secondary" : "outline"}>
            {percent(prospect.fit)} legacy match estimate
          </Badge>
        ) : (
          <Badge variant="outline">UNVERIFIED</Badge>
        )}
      </CardHeader>

      <CardContent className="space-y-3 text-sm">
        {prospect.qualification && (
          <QualificationReceipt qualification={prospect.qualification} />
        )}
        {prospect.why_them && <p>{prospect.why_them}</p>}
        {prospect.verbatim && (
          <blockquote className="border-l-2 border-border pl-3 text-xs text-foreground/80 italic">
            &ldquo;{prospect.verbatim}&rdquo;
          </blockquote>
        )}

        {prospect.contacts.length > 0 ? (
          <ul className="space-y-1">
            {prospect.contacts.map((contact) => (
              <li key={`${contact.kind}-${contact.value}`} className="flex items-center gap-2">
                <span className="text-muted-foreground">{CONTACT_ICONS[contact.kind]}</span>
                <span className="font-mono text-xs">{contact.value}</span>
                {contact.label && (
                  <span className="text-xs text-muted-foreground">({contact.label})</span>
                )}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-xs text-muted-foreground">
            {prospect.verified
              ? "They publish no way to contact them anywhere we could read."
              : prospect.note || "Their site could not be read."}
          </p>
        )}

        {prospect.invented_contacts > 0 && (
          <p className="rounded-md bg-amber-500/10 p-2 text-xs text-amber-300">
            {prospect.invented_contacts} contact detail
            {prospect.invented_contacts === 1 ? " was" : "s were"} reported that could not be
            found anywhere on their site, and discarded. Weigh the rest of this row
            accordingly.
          </p>
        )}
        {prospect.caveat && (
          <p className="text-xs text-muted-foreground">Check first: {prospect.caveat}</p>
        )}

        <div className="flex flex-wrap items-center justify-between gap-2">
          <span className="text-xs text-muted-foreground">
            {prospect.status === "kept"
              ? "on your list"
              : prospect.status === "dismissed"
                ? "dismissed — it will not be offered again"
                : `read ${prospect.pages_read} page${prospect.pages_read === 1 ? "" : "s"}`}
          </span>
          <div className="flex gap-2">
            <Button
              size="sm"
              variant="ghost"
              disabled={deciding || prospect.status === "dismissed"}
              onClick={() => decide("dismissed")}
            >
              Not for us
            </Button>
            <Button
              size="sm"
              disabled={deciding || prospect.status === "kept"}
              onClick={() => decide("kept")}
            >
              Keep
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export function AudiencePanel({
  brandId,
  audience,
  onMap,
  onProspect,
  onResearch,
  onDossier,
  busy,
  runningKind,
}: {
  brandId: string;
  audience: AudienceRead;
  onMap: (options: MapOptions) => void;
  onProspect: (segment: string) => void;
  onResearch: (segment: string) => void;
  onDossier: (segment: string, rebuild: boolean) => void;
  busy: boolean;
  runningKind: string | null;
}) {
  const router = useRouter();
  const [rows, setRows] = useState(audience.prospects);
  const [selected, setSelected] = useState<string | null>(null);
  const [options, setOptions] = useState<MapOptions>(audience.map?.options ?? {
    geography: "", language: "", exclusions: "", objective: "customers", mode: "refresh",
  });
  const scopeControls = (
    <details className="rounded-lg border p-4 text-sm">
      <summary className="cursor-pointer font-medium">Search scope and budget</summary>
      <p className="mt-2 text-xs text-muted-foreground">Two model stages and up to ten source pages. Retries can add calls. Empty filters leave the search open. Changing the scope starts a new map.</p>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        {([['geography', 'Countries or regions', 200], ['language', 'Audience language', 100], ['exclusions', 'Exclude industries or situations', 1000]] as const).map(([key, label, max]) => (
          <label key={key} className="space-y-1">
            <span>{label}</span>
            <input className="w-full rounded-md border bg-background p-2" value={options[key]} maxLength={max} disabled={busy} onChange={(event) => setOptions({ ...options, [key]: event.target.value })} />
          </label>
        ))}
        <label className="space-y-1">
          <span>Looking for</span>
          <select className="w-full rounded-md border bg-background p-2" value={options.objective} disabled={busy} onChange={(event) => setOptions({ ...options, objective: event.target.value as MapOptions['objective'] })}>
            <option value="customers">Direct customers</option><option value="partners">Partners and resellers</option><option value="both">Customers and partners</option>
          </select>
        </label>
      </div>
    </details>
  );

  const demand = audience.map;
  const researchByAudience = useMemo(
    () => new Map(audience.research.map((item) => [item.audience_key, item])),
    [audience.research],
  );
  const relevanceByAudience = useMemo(
    () =>
      new Map(
        audience.relevance.map((item) => [audienceKey(item.audience_name), item]),
      ),
    [audience.relevance],
  );
  const bySegment = useMemo(() => {
    const counts = new Map<string, number>();
    for (const row of rows) {
      if (row.status === "dismissed") continue;
      counts.set(row.segment, (counts.get(row.segment) ?? 0) + 1);
    }
    return counts;
  }, [rows]);

  const visible = selected ? rows.filter((row) => row.segment === selected) : rows;
  // Counted over what is visible, not over everything: the export link is
  // scoped to the selected segment, and a button that says "3 kept" next to a
  // file containing one is a button that gets distrusted the first time
  // somebody opens the file.
  const kept = visible.filter((row) => row.status === "kept").length;

  function replace(updated: Prospect) {
    setRows((current) => current.map((row) => (row.id === updated.id ? updated : row)));
  }

  if (!demand) {
    return (
      <div className="space-y-4">
        {scopeControls}
        <CapabilityProfileCard brandId={brandId} initialProfile={audience.capability_profile} />
        <AudienceAdder
          brandId={brandId}
          defaultOpen
          onSaved={() => router.refresh()}
        />
        <Card>
          <CardHeader className="flex flex-row items-start justify-between gap-4">
            <div>
              <CardTitle className="text-base">Nobody has mapped this yet</CardTitle>
              <p className="mt-1 max-w-2xl text-sm text-muted-foreground">{audience.note}</p>
            </div>
            <Button size="sm" onClick={() => onMap({ ...options, mode: "refresh" })} disabled={busy}>
              {busy ? "Working…" : "Find the audience"}
            </Button>
          </CardHeader>
          <CardContent className="max-w-2xl space-y-2 text-sm text-muted-foreground">
            <p>
              Find audiences whose needs match your product, including your core buyers and
              adjacent markets where public evidence supports the connection.
            </p>
            <p>
              Each candidate is checked against fetched pages and your product capabilities.
              Weak evidence remains an explicit hypothesis; no response rate is predicted.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {scopeControls}
      <CapabilityProfileCard brandId={brandId} initialProfile={audience.capability_profile} />
      <Card>
        <CardHeader className="flex flex-row items-start justify-between gap-4">
          <div className="min-w-0">
            <CardTitle className="text-base">{demand.summary}</CardTitle>
            {demand.reading && (
              <p className="mt-1 max-w-2xl text-sm text-muted-foreground">{demand.reading}</p>
            )}
          </div>
          <div className="flex shrink-0 flex-col gap-2">
            <Button size="sm" variant="outline" onClick={() => onMap({ ...options, mode: "refresh" })} disabled={busy}>
              {busy && runningKind === "audience" ? "Working…" : "Rescan audiences"}
            </Button>
            <Button size="sm" variant="outline" onClick={() => onMap({ ...options, mode: "explore" })} disabled={busy}>Explore other audiences</Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-2 text-xs text-muted-foreground">
          <p>
            Rescan replaces this list with fresh results. Explore adds new audiences to this list.
            {" "}{demand.validation_note}
          </p>
          {demand.searched.length > 0 && (
            <details><summary className="cursor-pointer">Queries reported by the researcher</summary><p>{demand.searched.join(" · ")}</p></details>
          )}
          {demand.note && <p className="text-amber-300/80">{demand.note}</p>}
        </CardContent>
      </Card>

      <AudienceAdder
        brandId={brandId}
        defaultOpen={false}
        onSaved={() => router.refresh()}
      />

      <div className="grid items-start gap-3 lg:grid-cols-2">
        {demand.segments.map((segment) => (
          <SegmentCard
            key={segment.name}
            brandId={brandId}
            segment={segment}
            selected={selected === segment.name}
            prospects={bySegment.get(segment.name) ?? 0}
            research={researchByAudience.get(audienceKey(segment.name))}
            relevance={relevanceByAudience.get(audienceKey(segment.name))}
            onSelect={() =>
              setSelected((current) => (current === segment.name ? null : segment.name))
            }
            onProspect={() => onProspect(segment.name)}
            onResearch={() => onResearch(segment.name)}
            onDossier={(rebuild) => onDossier(segment.name, rebuild)}
            onChanged={() => router.refresh()}
            busy={busy}
          />
        ))}
      </div>

      {rows.length > 0 && (
        <Card>
          <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-3">
            <div>
              <CardTitle className="text-base">
                {selected ? `Organisations for ${selected}` : "Every organisation found"}
              </CardTitle>
              <p className="mt-1 text-xs text-muted-foreground">
                Every address below was read off a page on that company&rsquo;s own site and
                checked against it. Nothing here was guessed from a domain name.
              </p>
            </div>
            <div className="flex items-center gap-2">
              {selected && (
                <Button size="sm" variant="ghost" onClick={() => setSelected(null)}>
                  Show all
                </Button>
              )}
              {/* An href rather than a fetch: the export is a file, and the
                  browser already knows how to save one. */}
              <a
                href={api.prospectsCsvUrl(brandId, selected ?? undefined)}
                className={cn(
                  "rounded-md border border-border px-3 py-1.5 text-xs",
                  kept === 0 && "pointer-events-none opacity-40",
                )}
                title={
                  kept === 0
                    ? "Keep at least one organisation first — the file only carries the rows you reviewed"
                    : "Download the rows you kept"
                }
              >
                Export {kept > 0 ? `${kept} kept` : "kept"}
              </a>
            </div>
          </CardHeader>
        </Card>
      )}

      <div className="space-y-3">
        {visible.map((prospect) => (
          <ProspectCard
            key={prospect.id}
            brandId={brandId}
            prospect={prospect}
            onDecided={replace}
          />
        ))}
      </div>
    </div>
  );
}
