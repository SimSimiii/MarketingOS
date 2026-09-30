"use client";

import { AccountPanel } from "@/app/settings/account-panel";
import { ModelGuide } from "@/app/settings/model-guide";
import { PageHeader } from "@/components/page-header";
import { api } from "@/lib/api-client";
import { AUTH_REQUIRED } from "@/lib/config";
import { PageData, usePageData } from "@/lib/page-data";

export function SettingsView() {
  const state = usePageData(
    // Only where there are accounts. In single-user mode there is nothing to
    // describe: no password, no sessions, no plan.
    () => (AUTH_REQUIRED ? api.getCurrentUser().catch(() => null) : Promise.resolve(null)),
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
                ? "Your account, and how a campaign decides which models write it."
                : "How a campaign decides which models write it. This install runs as a single workspace."
            }
          />
          {account && <AccountPanel account={account} />}
          <ModelGuide />
        </div>
      )}
    </PageData>
  );
}
