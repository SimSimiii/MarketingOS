"use client";

import { useState } from "react";
import { Plus, X } from "lucide-react";
import { toast } from "sonner";

import { BrandDisclosure } from "@/app/brands/brand-ui";
import { Notice } from "@/components/notice";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api-client";
import type {
  Campaign,
  CampaignSteering,
  SteeringCheck,
  SteeringInstruction,
  SteeringOption,
} from "@/lib/types";
import { cn } from "@/lib/utils";

type Choice = "include" | "exclude";

const GROUPS: { id: SteeringOption["group"]; label: string }[] = [
  { id: "facts", label: "Facts" },
  { id: "proof", label: "Proof" },
  { id: "offer", label: "Offer" },
  { id: "price", label: "Price" },
  { id: "audience", label: "Audience" },
  { id: "competition", label: "Competition" },
];

const STATUS: Record<SteeringOption["status"], { label: string; className: string }> = {
  usable: { label: "Usable in the copy", className: "border-emerald-400/25 bg-emerald-500/10 text-emerald-200" },
  strategic: { label: "Strategic context", className: "border-sky-400/25 bg-sky-500/10 text-sky-200" },
  to_confirm: { label: "To confirm", className: "border-amber-400/25 bg-amber-500/10 text-amber-200" },
};

//: Long ledgers are the norm for a crawled site. A group shows this many
//: until asked for the rest, so the section stays a glance rather than a form.
const SHOWN = 6;
const MAX_INSTRUCTIONS = 8;
const MAX_CHARS = 500;

/**
 * Optional content choices before a run - "Orienter le contenu".
 *
 * Closed by default and never required: a campaign nobody steers runs exactly
 * as it did before this existed. The options are what the existing analyses
 * already found, each with an honest status, and selecting one never changes
 * that status - "include" on something unverified makes it context for the
 * plan, not a claim in the copy. Choices are saved on the campaign and apply
 * to the next run; each run keeps the choices it was planned with.
 */
export function SteeringPanel({ campaign, locked }: { campaign: Campaign; locked: boolean }) {
  const saved = campaign.steering ?? null;
  const [check, setCheck] = useState<SteeringCheck | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [choices, setChoices] = useState<Record<string, Choice>>(() =>
    Object.fromEntries((saved?.items ?? []).map((item) => [item.id, item.choice])),
  );
  const [instructions, setInstructions] = useState<SteeringInstruction[]>(saved?.instructions ?? []);
  const [draft, setDraft] = useState("");
  const [draftPosition, setDraftPosition] = useState<string>("");
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  const chosen = Object.keys(choices).length;
  const summary = chosen + instructions.length === 0
    ? "Nothing set - the system decides. Open to include or exclude facts, or add directions."
    : `${chosen} choice(s) and ${instructions.length} direction(s) apply to the next run.`;

  function load() {
    if (check || loading) return;
    setLoading(true);
    api.getCampaignSteering(campaign.id)
      .then(setCheck)
      .catch(() => toast.error("Could not load what this campaign can be steered with."))
      .finally(() => setLoading(false));
  }

  function setChoice(id: string, choice: Choice | null) {
    setChoices((current) => {
      const next = { ...current };
      if (choice === null) delete next[id];
      else next[id] = choice;
      return next;
    });
  }

  function addInstruction() {
    const text = draft.trim();
    if (!text) return;
    const position = Number.parseInt(draftPosition, 10);
    setInstructions((current) => [
      ...current,
      Number.isFinite(position) && position > 0
        ? { text, scope: "email", position }
        : { text, scope: "sequence", position: null },
    ]);
    setDraft("");
    setDraftPosition("");
  }

  async function save(next?: CampaignSteering) {
    const body: CampaignSteering = next ?? {
      items: Object.entries(choices).map(([id, choice]) => ({ id, choice })),
      instructions,
    };
    setSaving(true);
    try {
      const result = await api.updateCampaignSteering(campaign.id, body);
      setCheck(result);
      const conflicts = result.conflicts?.filter((item) => item.severity === "conflict").length ?? 0;
      toast.success(conflicts ? `Saved - ${conflicts} point(s) to review below.` : "Saved for the next run.");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not save your choices.");
    } finally {
      setSaving(false);
    }
  }

  function clear() {
    setChoices({});
    setInstructions([]);
    void save({ items: [], instructions: [] });
  }

  const options = check?.options ?? [];
  const conflicts = check?.conflicts ?? [];

  return (
    <BrandDisclosure title="Steer the content (optional)" description={summary} onOpen={load}>
        <div className="space-y-6">
          <p className="max-w-3xl text-xs leading-relaxed text-muted-foreground">
            Every choice is optional and applies from the plan onward, through every rewrite.
            <strong className="font-medium text-foreground/90"> Selecting an item does not verify it:</strong>{" "}
            only items marked “Usable in the copy” can be stated; strategic context shapes the plan and
            items to confirm are used as context only. Exclusions and the factual checks always win
            over directions.
          </p>

          {loading && <p className="text-sm text-muted-foreground">Reading the analyses…</p>}
          {check && !check.knowledge_ready && (
            <Notice tone="info" title="Nothing to choose from yet">
              Facts, proof and prices appear here once this campaign&apos;s material has been analysed,
              after its first run. Directions below can be saved now.
            </Notice>
          )}

          {conflicts.length > 0 && (
            <Notice tone={conflicts.some((item) => item.severity === "conflict") ? "warning" : "info"} title="Worth checking">
              <ul className="space-y-1">
                {conflicts.map((item) => <li key={item.message}>— {item.message}</li>)}
              </ul>
            </Notice>
          )}

          {GROUPS.map((group) => {
            const items = options.filter((option) => option.group === group.id);
            if (items.length === 0) return null;
            const visible = expanded[group.id] ? items : items.slice(0, SHOWN);
            return (
              <section key={group.id} aria-labelledby={`steer-${group.id}`} className="space-y-2">
                <h3 id={`steer-${group.id}`} className="text-[0.6875rem] font-medium uppercase tracking-[0.16em] text-muted-foreground">
                  {group.label} <span className="tabular-nums">({items.length})</span>
                </h3>
                <ul className="divide-y divide-white/[0.05] rounded-xl ring-1 ring-white/[0.07]">
                  {visible.map((option) => (
                    <li key={option.id} className="flex flex-wrap items-start justify-between gap-3 p-3">
                      <div className="min-w-0 flex-1 basis-64 space-y-1">
                        <p className="text-sm leading-snug">{option.label}</p>
                        <div className="flex flex-wrap items-center gap-2">
                          <Badge className={STATUS[option.status].className} title={option.status_reason}>
                            {STATUS[option.status].label}
                          </Badge>
                          {option.detail && <span className="line-clamp-1 text-xs text-muted-foreground">{option.detail}</span>}
                        </div>
                      </div>
                      <TriState
                        label={option.label}
                        value={choices[option.id] ?? null}
                        disabled={locked}
                        onChange={(value) => setChoice(option.id, value)}
                      />
                    </li>
                  ))}
                </ul>
                {items.length > SHOWN && (
                  <Button variant="link" size="sm" className="px-0" onClick={() => setExpanded((current) => ({ ...current, [group.id]: !current[group.id] }))}>
                    {expanded[group.id] ? "Show fewer" : `Show all ${items.length}`}
                  </Button>
                )}
              </section>
            );
          })}

          <section aria-labelledby="steer-directions" className="space-y-3">
            <h3 id="steer-directions" className="text-[0.6875rem] font-medium uppercase tracking-[0.16em] text-muted-foreground">
              Directions
            </h3>
            {instructions.length > 0 && (
              <ul className="space-y-1.5">
                {instructions.map((instruction, index) => (
                  <li key={`${instruction.text}-${index}`} className="flex items-start gap-2 rounded-lg bg-white/[0.03] px-3 py-2 text-sm ring-1 ring-white/[0.06]">
                    <Badge variant="secondary" className="shrink-0">
                      {instruction.scope === "email" ? `Email ${instruction.position}` : "Whole sequence"}
                    </Badge>
                    <span className="min-w-0 flex-1">{instruction.text}</span>
                    <Button
                      variant="ghost" size="icon-xs" disabled={locked}
                      aria-label={`Remove the direction “${instruction.text}”`}
                      onClick={() => setInstructions((current) => current.filter((_, i) => i !== index))}
                    >
                      <X aria-hidden="true" />
                    </Button>
                  </li>
                ))}
              </ul>
            )}
            {instructions.length < MAX_INSTRUCTIONS && (
              <div className="flex flex-wrap items-end gap-2">
                <label className="min-w-0 flex-1 basis-72 space-y-1">
                  <span className="text-xs text-muted-foreground">A direction, in your words</span>
                  <Textarea
                    value={draft}
                    maxLength={MAX_CHARS}
                    disabled={locked}
                    onChange={(event) => setDraft(event.target.value)}
                    placeholder="e.g. state the price at the start"
                    className="min-h-11"
                  />
                </label>
                <label className="w-36 space-y-1">
                  <span className="text-xs text-muted-foreground">Only email # (optional)</span>
                  <Input
                    type="number" min={1} max={12} inputMode="numeric" value={draftPosition}
                    disabled={locked}
                    onChange={(event) => setDraftPosition(event.target.value)}
                    placeholder="All"
                  />
                </label>
                <Button variant="outline" onClick={addInstruction} disabled={locked || !draft.trim()}>
                  <Plus aria-hidden="true" /> Add
                </Button>
              </div>
            )}
          </section>

          <div className="flex flex-wrap items-center gap-2 border-t border-hairline pt-4">
            <Button onClick={() => void save()} disabled={locked || saving}>
              {saving ? "Saving…" : "Save for the next run"}
            </Button>
            {(chosen > 0 || instructions.length > 0) && (
              <Button variant="ghost" onClick={clear} disabled={locked || saving}>Clear all</Button>
            )}
            {locked && <span className="text-xs text-muted-foreground">A run is in progress - change these once it finishes.</span>}
          </div>
        </div>
    </BrandDisclosure>
  );
}

/** Include · System decides · Exclude, as one labelled group of buttons. */
function TriState({
  label, value, disabled, onChange,
}: {
  label: string;
  value: Choice | null;
  disabled: boolean;
  onChange: (value: Choice | null) => void;
}) {
  const options: { value: Choice | null; text: string; active: string }[] = [
    { value: "include", text: "Include", active: "bg-emerald-500/20 text-emerald-100" },
    { value: null, text: "Auto", active: "bg-white/[0.1] text-foreground" },
    { value: "exclude", text: "Exclude", active: "bg-rose-500/20 text-rose-100" },
  ];
  return (
    <div role="group" aria-label={`Choice for ${label}`} className="flex h-8 shrink-0 items-center rounded-[0.6rem] bg-black/25 p-0.5 ring-1 ring-white/[0.07]">
      {options.map((option) => (
        <button
          key={option.text}
          type="button"
          disabled={disabled}
          aria-pressed={value === option.value}
          onClick={() => onChange(option.value)}
          className={cn(
            "h-full cursor-pointer rounded-[0.45rem] px-2.5 text-xs font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-ring disabled:cursor-not-allowed disabled:opacity-50",
            value === option.value ? option.active : "text-muted-foreground hover:text-foreground",
          )}
        >
          {option.text}
        </button>
      ))}
    </div>
  );
}
