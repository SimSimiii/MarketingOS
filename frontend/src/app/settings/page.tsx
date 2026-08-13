import { SettingsForm } from "@/app/settings/settings-form";
import { api } from "@/lib/api-client";

export default async function SettingsPage() {
  const settings = await api.getSettings();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
        <p className="text-sm text-muted-foreground">
          Defaults used across campaigns. Single-user MVP, no auth yet.
        </p>
      </div>
      <SettingsForm settings={settings} />
    </div>
  );
}
