import { SettingsForm } from "@/app/settings/settings-form";
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
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
        <p className="text-sm text-muted-foreground">
          {account
            ? "Your account, and the defaults every campaign starts from."
            : "Defaults used across campaigns. This install runs as a single workspace."}
        </p>
      </div>
      <SettingsForm settings={settings} />
      {account && <AccountPanel account={account} />}
    </div>
  );
}
