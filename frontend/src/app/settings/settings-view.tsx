"use client";

import type { ComponentType } from "react";
import Link from "next/link";
import { ArrowUpRight, Files, Gauge, HardDrive, Palette } from "lucide-react";

import { AccountPanel } from "@/app/settings/account-panel";
import { CreditPanel } from "@/app/settings/credit-panel";
import { PageHeader } from "@/components/page-header";
import { api } from "@/lib/api-client";
import { AUTH_REQUIRED } from "@/lib/config";
import { PageData, usePageData } from "@/lib/page-data";

/** Where each decision a campaign depends on is actually made. None of them is
 * an account-wide preference, which is why this page points rather than
 * offering a form: a "default voice" field here would be saved somewhere no
 * part of the pipeline reads. */
const WHERE: { icon: ComponentType<{ className?: string }>; title: string; body: string; href: string; cta: string }[] = [
  {
    icon: Files,
    title: "Voice and facts",
    body: "Come from each brand's own sources. Add its website or documents, and every campaign for it writes from them.",
    href: "/brands",
    cta: "Brands",
  },
  {
    icon: Palette,
    title: "Email look",
    body: "Logo, accent colour and footer are set per brand, under Identity, and used by the branded layout.",
    href: "/brands",
    cta: "Brand identity",
  },
  {
    icon: Gauge,
    title: "Review depth",
    body: "Each campaign has its own execution preset - fast, balanced or maximum - beside its brief.",
    href: "/campaigns",
    cta: "Campaigns",
  },
];

export function SettingsView() {
  const state = usePageData(
    // Only where there are accounts. In single-user mode there is nothing to
    // describe: no password, no sessions, no plan.
    () => (AUTH_REQUIRED ? api.getCurrentUser() : Promise.resolve(null)),
    [],
  );

  return (
    <PageData state={state}>
      {(account) => (
        <div className="space-y-8">
          <PageHeader
            eyebrow="Workspace"
            title="Settings"
            description={
              account
                ? "Your account and where you are signed in."
                : "How this install runs, and where each decision a campaign depends on is made."
            }
          />
          {account && <AccountPanel account={account} />}
          {account && <CreditPanel />}
          {!account && (
            <section className="studio-hero rise flex flex-wrap items-center gap-5 overflow-hidden rounded-3xl p-6 sm:p-8">
              <span className="icon-tile flex size-12 shrink-0 items-center justify-center rounded-2xl">
                <HardDrive className="size-5" aria-hidden="true" />
              </span>
              <div className="min-w-0 flex-1 basis-72">
                <h2 className="font-display text-[1.75rem] leading-tight">Single workspace</h2>
                <p className="mt-1.5 max-w-2xl text-sm leading-relaxed text-muted-foreground">
                  No sign-in and no account to manage: every brand, campaign and run on this
                  install is visible here. Your account and where you are signed in appear on this page when
                  the console is deployed with sign-in turned on.
                </p>
              </div>
            </section>
          )}
          <section aria-labelledby="where-title" className="space-y-4">
            <h2 id="where-title" className="font-display text-[1.75rem] leading-tight">
              Where things are set
            </h2>
            <ul className="rise-stagger grid gap-4 md:grid-cols-3">
              {WHERE.map(({ icon: Icon, title, body, href, cta }) => (
                <li key={title}>
                  <Link
                    href={href}
                    className="group surface surface-interactive flex h-full flex-col rounded-2xl p-5"
                  >
                    <span className="icon-tile flex size-9 items-center justify-center rounded-xl">
                      <Icon className="size-4" aria-hidden="true" />
                    </span>
                    <span className="mt-4 text-[0.9375rem] font-semibold">{title}</span>
                    <span className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{body}</span>
                    <span className="mt-auto inline-flex items-center gap-1 pt-4 text-xs font-medium text-muted-foreground transition-colors group-hover:text-violet-200">
                      {cta}
                      <ArrowUpRight className="size-3.5 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" aria-hidden="true" />
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        </div>
      )}
    </PageData>
  );
}
