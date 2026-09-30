"use client";

import Link from "next/link";
import { Building2, Cpu } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/skeleton";
import { useModelCatalog } from "@/lib/use-model-catalog";
import type { ModelTier } from "@/lib/types";

const TIER_LABEL: Record<ModelTier, string> = {
  fast: "Fast work",
  balanced: "Balanced work",
  deep: "Deep work",
};

/**
 * Where a campaign's models and voice actually come from.
 *
 * This page used to hold a "Workspace defaults" form - company name, brand
 * voice, default model - that saved to a settings row nothing in the pipeline
 * ever reads. The model a role runs on comes from its tier and the campaign's
 * own overrides; the voice and the company come from each brand's material.
 * A form that accepts a value and does nothing with it is worse than no form:
 * the reader believes they have steered the copy. This says what does.
 */
export function ModelGuide() {
  const catalog = useModelCatalog();

  return (
    <div className="grid max-w-5xl gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Cpu className="size-4 text-violet-300" aria-hidden="true" />
            How models are chosen
          </CardTitle>
          <CardDescription>
            Every agent asks for a kind of work, not a model. A campaign&apos;s preset decides how
            much of it is bought; the model behind each agent can be pinned on the campaign
            itself, under Custom models.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          {catalog === null ? (
            <div className="space-y-2" aria-hidden="true">
              <Skeleton className="h-10" />
              <Skeleton className="h-10" />
              <Skeleton className="h-10" />
            </div>
          ) : (
            <>
              <dl className="grid gap-3 sm:grid-cols-3">
                {(Object.keys(TIER_LABEL) as ModelTier[]).map((tier) => {
                  const model = catalog.models.find((option) => option.id === catalog.tier_defaults[tier]);
                  return (
                    <div key={tier} className="rounded-lg border border-hairline bg-background/40 p-3">
                      <dt className="text-xs text-muted-foreground">{TIER_LABEL[tier]}</dt>
                      <dd className="mt-1 text-sm font-medium">{model?.label ?? catalog.tier_defaults[tier]}</dd>
                    </div>
                  );
                })}
              </dl>
              <ul className="divide-y divide-hairline">
                {catalog.models.map((model) => (
                  <li key={model.id} className="flex flex-wrap items-start gap-x-3 gap-y-1 py-3 first:pt-0 last:pb-0">
                    <div className="min-w-0 flex-1">
                      <p className="flex flex-wrap items-center gap-2 text-sm font-medium">
                        {model.label}
                        <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-[11px] text-muted-foreground">
                          {model.id}
                        </code>
                      </p>
                      <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground">{model.blurb}</p>
                      {model.requires && (
                        <p className="mt-0.5 text-xs text-amber-300/80">Needs: {model.requires}</p>
                      )}
                    </div>
                    <Badge variant="secondary" className="capitalize">
                      {model.vendor === "anthropic" ? "Claude" : "GPT"}
                    </Badge>
                  </li>
                ))}
              </ul>
            </>
          )}
        </CardContent>
      </Card>

      <Card size="sm" className="self-start">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm">
            <Building2 className="size-4 text-violet-300" aria-hidden="true" />
            Voice and company
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm leading-relaxed text-muted-foreground">
          <p>
            How the emails sound, and what they may say about the company, are learned from each
            brand&apos;s own material - its site, its documents, the copy it already sends.
          </p>
          <p>To change them, change what the brand reads.</p>
          <Link href="/brands" className="inline-flex text-sm font-medium text-violet-300 hover:underline">
            Open brand workspaces →
          </Link>
        </CardContent>
      </Card>
    </div>
  );
}
