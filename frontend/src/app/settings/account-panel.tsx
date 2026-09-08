"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { api } from "@/lib/api-client";
import type { Account, AuthSession } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

/** The account half of Settings: the password, and where it is signed in. */
export function AccountPanel({ account }: { account: Account }) {
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <PasswordCard />
      <SessionsCard account={account} />
    </div>
  );
}

function PasswordCard() {
  const router = useRouter();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      await api.changePassword({ current_password: current, password: next });
      // The API revokes every session on a password change, this one included -
      // so the honest next step is the sign-in page, not a success toast on a
      // page whose next request will 401.
      toast.success("Password changed. Sign in again with the new one.");
      await fetch("/api/auth/logout", { method: "POST" }).catch(() => undefined);
      router.replace("/login");
      router.refresh();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not change the password.");
      setBusy(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Password</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={submit} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="current-password">Current password</Label>
            <Input
              id="current-password"
              type="password"
              autoComplete="current-password"
              required
              value={current}
              onChange={(event) => setCurrent(event.target.value)}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="new-password">New password</Label>
            <Input
              id="new-password"
              type="password"
              autoComplete="new-password"
              required
              minLength={10}
              value={next}
              onChange={(event) => setNext(event.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              At least 10 characters. Changing it signs out every device, including this
              one.
            </p>
          </div>
          <Button type="submit" disabled={busy}>
            {busy ? "Changing…" : "Change password"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

function SessionsCard({ account }: { account: Account }) {
  const router = useRouter();
  const [sessions, setSessions] = useState<AuthSession[] | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api
      .listAuthSessions()
      .then((rows) => {
        if (!cancelled) setSessions(rows);
      })
      .catch(() => {
        if (!cancelled) setSessions([]);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function signOutEverywhere() {
    setBusy(true);
    try {
      await api.signOutEverywhere();
      await fetch("/api/auth/logout", { method: "POST" }).catch(() => undefined);
      router.replace("/login");
      router.refresh();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not sign out.");
      setBusy(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Account</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <dl className="grid grid-cols-2 gap-y-2 text-sm">
          <dt className="text-muted-foreground">Email</dt>
          <dd className="truncate">{account.email}</dd>
          <dt className="text-muted-foreground">Plan</dt>
          <dd className="capitalize">{account.plan}</dd>
          <dt className="text-muted-foreground">Runs this period</dt>
          <dd>
            {account.monthly_run_quota > 0
              ? `${account.runs_used} of ${account.monthly_run_quota}`
              : `${account.runs_used} (no limit set)`}
          </dd>
        </dl>

        <div className="border-t border-border pt-4">
          <p className="text-sm font-medium">Where you are signed in</p>
          {sessions === null ? (
            <p className="mt-1 text-sm text-muted-foreground">Loading…</p>
          ) : sessions.length === 0 ? (
            <p className="mt-1 text-sm text-muted-foreground">No other devices.</p>
          ) : (
            <ul className="mt-2 space-y-1.5 text-xs text-muted-foreground">
              {sessions.map((session) => (
                <li key={session.id} className="flex justify-between gap-3">
                  <span className="truncate">{session.user_agent ?? "Unknown device"}</span>
                  <span className="shrink-0">{session.ip_address ?? "—"}</span>
                </li>
              ))}
            </ul>
          )}
          <Button
            variant="outline"
            className="mt-3"
            disabled={busy || sessions === null || sessions.length === 0}
            onClick={signOutEverywhere}
          >
            {busy ? "Signing out…" : "Sign out everywhere"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
