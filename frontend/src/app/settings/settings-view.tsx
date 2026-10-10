"use client";

import { AccountPanel } from "@/app/settings/account-panel";
import { CreditPanel } from "@/app/settings/credit-panel";
import { PageHeader } from "@/components/page-header";
import { api } from "@/lib/api-client";
import { AUTH_REQUIRED } from "@/lib/config";
import { PageData, usePageData } from "@/lib/page-data";

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
        <div className="space-y-6">
          <PageHeader
            eyebrow="Workspace"
            title="Settings"
            description={
              account
                ? "Manage your account and campaign preferences."
                : "This install runs as a single workspace."
            }
          />
          {account && <AccountPanel account={account} />}
          {account && <CreditPanel />}
        </div>
      )}
    </PageData>
  );
}
