"use client";

import { useMemo } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectSeparator,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { AgentOption, ModelCatalog, ModelOption, RolePhase } from "@/lib/types";
import { cn } from "@/lib/utils";

/** The value a Select carries for "no pin - use whatever the preset chose".
 *
 * Not the empty string: the underlying Select treats "" as "nothing selected"
 * and shows its placeholder instead of the row, which reads as a bug. The
 * sentinel is translated back to an absent key on the way out. */
const INHERIT = "__inherit__";

const PHASE_LABELS: Record<RolePhase, string> = {
  campaign: "Campaign",
  knowledge: "Knowledge",
  market: "Market intelligence",
};

const PHASE_BLURBS: Record<RolePhase, string> = {
  campaign: "Runs many times per campaign. Where nearly all the spend goes.",
  knowledge: "Runs once per business, then reused by every campaign attached to it.",
  market: "Only runs when market intelligence is refreshed. Reads the open web.",
};

const PHASE_ORDER: RolePhase[] = ["campaign", "knowledge", "market"];

const VENDOR_LABELS: Record<string, string> = {
  anthropic: "Claude - your Claude subscription",
  openai: "GPT - your ChatGPT plan",
};

/** Can this model do everything the agent's calls ask for?
 *
 * Today this is the market-intelligence roles: they pass `web_fetch` and no
 * GPT model has it. Checked here so the option is visibly greyed out with a
 * reason, rather than accepted and refused by the API a click later. */
function canRun(model: ModelOption, agent: AgentOption): boolean {
  return agent.tools.every((tool) => model.tools.includes(tool));
}

function missingFor(model: ModelOption, agent: AgentOption): string {
  return agent.tools.filter((tool) => !model.tools.includes(tool)).join(", ");
}

export interface ModelOverridePanelProps {
  catalog: ModelCatalog;
  /** `{role_id: model}`. An absent key means the agent follows the preset. */
  value: Record<string, string>;
  onChange: (next: Record<string, string>) => void;
  disabled?: boolean;
}

/** Pick the model behind each agent, across both vendors.
 *
 * Deliberately not a fourth execution preset. A preset decides the *shape* of a
 * run - how many drafts get written, whether the critic runs, what the budget
 * is - and models are only part of that. Folding "custom models" into the same
 * dropdown would mean choosing a model silently also changed how many drafts
 * get written, which is not what anyone picking a model means to do.
 */
export function ModelOverridePanel({
  catalog,
  value,
  onChange,
  disabled = false,
}: ModelOverridePanelProps) {
  const byPhase = useMemo(
    () =>
      PHASE_ORDER.map((phase) => ({
        phase,
        agents: catalog.agents.filter((agent) => agent.phase === phase),
      })).filter((group) => group.agents.length > 0),
    [catalog.agents],
  );

  const wildcard = value[catalog.wildcard] ?? "";
  const pinned = Object.keys(value).filter((key) => key !== catalog.wildcard).length;

  function set(roleId: string, model: string) {
    const next = { ...value };
    if (model === INHERIT) delete next[roleId];
    else next[roleId] = model;
    onChange(next);
  }

  /** What this agent will actually run on, given everything set above it -
   * the same three layers the backend router resolves in. */
  function effective(agent: AgentOption): { model: string; source: string } {
    if (value[agent.id]) return { model: value[agent.id], source: "pinned" };
    if (wildcard) return { model: wildcard, source: "every agent" };
    return { model: catalog.tier_defaults[agent.tier], source: `${agent.tier} tier` };
  }

  function labelFor(modelId: string): string {
    return catalog.models.find((model) => model.id === modelId)?.label ?? modelId;
  }

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-border bg-muted/30 p-3 space-y-2">
        <div className="flex items-center justify-between gap-3">
          <div className="min-w-0">
            <p className="text-sm font-medium">Every agent</p>
            <p className="text-xs text-muted-foreground">
              One model for the whole run. Anything pinned below still wins.
            </p>
          </div>
          <Select
            value={wildcard || INHERIT}
            onValueChange={(next) => next && set(catalog.wildcard, next as string)}
            disabled={disabled}
          >
            <SelectTrigger className="w-56 shrink-0">
              {/* Base UI renders the raw value unless it is told how to read
                  one, which would put "__inherit__" on the trigger. */}
              <SelectValue>
                {(selected: string) =>
                  selected === INHERIT ? "Follow the preset" : labelFor(selected)
                }
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={INHERIT}>Follow the preset</SelectItem>
              <SelectSeparator />
              <ModelOptions models={catalog.models} />
            </SelectContent>
          </Select>
        </div>
        {pinned > 0 && (
          <div className="flex items-center justify-between gap-3 pt-1">
            <p className="text-xs text-muted-foreground">
              {pinned} agent{pinned === 1 ? "" : "s"} pinned individually.
            </p>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              disabled={disabled}
              onClick={() => onChange(wildcard ? { [catalog.wildcard]: wildcard } : {})}
            >
              Clear pins
            </Button>
          </div>
        )}
      </div>

      {byPhase.map(({ phase, agents }) => (
        <div key={phase} className="space-y-2">
          <div>
            <p className="text-sm font-medium">{PHASE_LABELS[phase]}</p>
            <p className="text-xs text-muted-foreground">{PHASE_BLURBS[phase]}</p>
          </div>
          <div className="divide-y divide-border rounded-lg border border-border">
            {agents.map((agent) => {
              const current = value[agent.id] ?? "";
              const resolved = effective(agent);
              return (
                <div
                  key={agent.id}
                  className="flex items-start justify-between gap-3 p-3"
                >
                  <div className="min-w-0 space-y-1">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-medium">{agent.label}</p>
                      {agent.tools.length > 0 && (
                        <Badge variant="outline" className="text-[10px]">
                          reads the web
                        </Badge>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground">{agent.blurb}</p>
                    <p
                      className={cn(
                        "text-xs",
                        current ? "text-foreground" : "text-muted-foreground",
                      )}
                    >
                      Runs on <span className="font-medium">{labelFor(resolved.model)}</span>
                      <span className="text-muted-foreground"> ({resolved.source})</span>
                    </p>
                  </div>
                  <Select
                    value={current || INHERIT}
                    onValueChange={(next) => next && set(agent.id, next as string)}
                    disabled={disabled}
                  >
                    <SelectTrigger className="w-56 shrink-0">
                      <SelectValue>
                        {/* The row underneath already says what it will run
                            on and why, so the trigger says what the *choice*
                            is - not a second copy of the answer. */}
                        {(selected: string) =>
                          selected === INHERIT ? "Not pinned" : labelFor(selected)
                        }
                      </SelectValue>
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value={INHERIT}>
                        {wildcard ? "Follow “every agent”" : "Follow the preset"}
                      </SelectItem>
                      <SelectSeparator />
                      <ModelOptions models={catalog.models} agent={agent} />
                    </SelectContent>
                  </Select>
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}

/** The model list, grouped by who bills for it.
 *
 * Vendor is the grouping rather than capability or price because it is the
 * distinction with consequences the operator already understands: one group
 * spends their Claude subscription, the other their ChatGPT plan.
 */
function ModelOptions({ models, agent }: { models: ModelOption[]; agent?: AgentOption }) {
  const vendors = Array.from(new Set(models.map((model) => model.vendor)));
  return (
    <>
      {vendors.map((vendor) => (
        <SelectGroup key={vendor}>
          <SelectLabel>{VENDOR_LABELS[vendor] ?? vendor}</SelectLabel>
          {models
            .filter((model) => model.vendor === vendor)
            .map((model) => {
              const blocked = agent ? !canRun(model, agent) : false;
              return (
                <SelectItem key={model.id} value={model.id} disabled={blocked}>
                  <span className="flex flex-col items-start gap-0.5">
                    <span>{model.label}</span>
                    <span className="text-xs text-muted-foreground">
                      {blocked
                        ? `No ${missingFor(model, agent!)} - cannot run this agent`
                        : (model.requires ?? model.blurb)}
                    </span>
                  </span>
                </SelectItem>
              );
            })}
        </SelectGroup>
      ))}
    </>
  );
}
