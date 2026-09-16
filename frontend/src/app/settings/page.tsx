import { SettingsForm } from "@/app/settings/settings-form";
import { PageHeader } from "@/components/page-header";
import { AccountPanel } from "@/app/settings/account-panel";
import { api } from "@/lib/api-server";
import { AUTH_REQUIRED } from "@/lib/config";

export default async function SettingsPage() {
  const settings = await api.getSettings();
  // Only where there are accounts. In single-user mode there is nothing to
  // describe: no password, no sessions, no plan.
  const account = AUTH_REQUIRED ? await api.getCurrentUser().catch(() => null) : null;

  return (
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
  );
}
