"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { LogOut } from "lucide-react";

import { api } from "@/lib/api-client";
import { AUTH_REQUIRED } from "@/lib/config";
import type { Account } from "@/lib/types";

/**
 * Who is signed in, and the way out.
 *
 * Renders nothing at all in single-user mode - there is no account to name and
 * no session to end, so a "signed in as" panel would be describing something
 * that does not exist.
 */
export function AccountMenu() {
  const router = useRouter();
  const [account, setAccount] = useState<Account | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!AUTH_REQUIRED) return;
    let cancelled = false;
    api
      .getCurrentUser()
      .then((me) => {
        if (!cancelled) setAccount(me);
      })
      // A 401 here means the proxy is about to redirect anyway; nothing to say
      // in a sidebar that is on its way out.
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  if (!AUTH_REQUIRED || account === null) return null;

  async function signOut() {
    setBusy(true);
    await fetch("/api/auth/logout", { method: "POST" }).catch(() => undefined);
    // `refresh` as well: every page is server-rendered from the cookie that
    // was just deleted, and the router cache still holds the signed-in render.
    router.replace("/login");
    router.refresh();
  }

  return (
    <div className="border-t border-sidebar-border px-4 py-4">
      <Link href="/settings" className="block truncate text-sm font-medium hover:text-violet-200">
        {account.full_name ?? account.email}
      </Link>
      <p className="mt-0.5 truncate text-xs text-muted-foreground">{account.email}</p>
      <p className="mt-1 text-[10px] uppercase tracking-widest text-muted-foreground">
        {account.plan} plan
        {account.monthly_run_quota > 0 &&
          ` · ${account.runs_used}/${account.monthly_run_quota} runs`}
      </p>
      <button
        onClick={signOut}
        disabled={busy}
        className="mt-3 flex w-full items-center gap-2 rounded-lg border border-border px-3 py-2 text-sm text-muted-foreground transition-colors hover:border-destructive/40 hover:text-destructive disabled:opacity-50"
      >
        <LogOut className="size-4" aria-hidden="true" />
        {busy ? "Signing out…" : "Sign out"}
      </button>
    </div>
  );
}
