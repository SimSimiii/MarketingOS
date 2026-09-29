"use client";

import { SettingsForm } from "@/app/settings/settings-form";
import { PageHeader } from "@/components/page-header";
import { AccountPanel } from "@/app/settings/account-panel";
import { api } from "@/lib/api-client";
import { AUTH_REQUIRED } from "@/lib/config";
import { PageData, usePageData } from "@/lib/page-data";

export function SettingsView() {
  const state = usePageData(
    () =>
      Promise.all([
        api.getSettings(),
        // Only where there are accounts. In single-user mode there is nothing
        // to describe: no password, no sessions, no plan.
        AUTH_REQUIRED ? api.getCurrentUser().catch(() => null) : Promise.resolve(null),
      ]),
    [],
  );

  return (
    <PageData state={state}>
      {([settings, account]) => (
        <div className="space-y-6">
          <PageHeader
            eyebrow="Workspace"
            title="Settings"
            description={
              account
                ? "Your account, and the defaults every campaign starts from."
                : "Defaults used across campaigns. This install runs as a single workspace."
            }
          />
          <SettingsForm settings={settings} />
          {account && <AccountPanel account={account} />}
        </div>
      )}
    </PageData>
  );
}
