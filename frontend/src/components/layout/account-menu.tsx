"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { LogOut } from "lucide-react";
import { toast } from "sonner";

import { api } from "@/lib/api-client";
import { AUTH_REQUIRED } from "@/lib/config";
import type { Account } from "@/lib/types";
import { API_URL } from "@/lib/config";
import { refreshPage } from "@/lib/page-data";
import { cn } from "@/lib/utils";

/** "Ada Lovelace" -> "AL"; "ada@example.com" -> "A". */
function initials(account: Account): string {
  const source = account.full_name?.trim() || account.email;
  const words = source.split(/[\s@._-]+/).filter(Boolean);
  if (account.full_name && words.length > 1) return `${words[0][0]}${words[words.length - 1][0]}`.toUpperCase();
  return (words[0]?.[0] ?? "?").toUpperCase();
}

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
    try {
      const response = await fetch(`${API_URL}/auth/logout`, { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" }, body: "{}" });
      if (!response.ok) throw new Error("Could not sign out. Please retry.");
      api.invalidate();
      router.replace("/login/");
      refreshPage();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not sign out. Please retry.");
    } finally {
      setBusy(false);
    }
  }

  const quota = account.monthly_run_quota;
  const used = Math.min(account.runs_used, quota || account.runs_used);
  const share = quota > 0 ? Math.min(1, account.runs_used / quota) : 0;

  return (
    <div className="mx-3 mb-4 rounded-2xl border border-white/[0.07] bg-white/[0.025] p-3 shadow-[inset_0_1px_0_0_oklch(1_0_0/4%)]">
      <div className="flex items-center gap-3">
        <span
          className="brand-mark flex size-9 shrink-0 items-center justify-center rounded-full text-xs font-semibold text-white"
          aria-hidden="true"
        >
          {initials(account)}
        </span>
        <Link href="/settings" className="min-w-0 flex-1 rounded-md">
          <span className="block truncate text-sm font-medium hover:text-violet-200">
            {account.full_name ?? account.email}
          </span>
          <span className="mt-0.5 block truncate text-[0.6875rem] text-muted-foreground">{account.email}</span>
        </Link>
        <button
          type="button"
          onClick={signOut}
          disabled={busy}
          aria-label={busy ? "Signing out" : "Sign out"}
          title="Sign out"
          className="flex size-8 shrink-0 cursor-pointer items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-red-500/10 hover:text-red-300 disabled:opacity-50"
        >
          <LogOut className="size-4" aria-hidden="true" />
        </button>
      </div>
      <div className="mt-3 border-t border-white/[0.06] pt-2.5">
        <div className="flex items-center justify-between text-[0.625rem] font-medium uppercase tracking-[0.16em] text-muted-foreground">
          <span>{account.plan} plan</span>
          {quota > 0 && (
            <span className="tabular-nums tracking-normal">
              {used}/{quota} runs
            </span>
          )}
        </div>
        {quota > 0 && (
          <div
            className="mt-2 h-1 overflow-hidden rounded-full bg-white/[0.06]"
            role="meter"
            aria-label="Runs used this period"
            aria-valuemin={0}
            aria-valuemax={quota}
            aria-valuenow={account.runs_used}
          >
            <div
              className={cn(
                "h-full rounded-full",
                share >= 0.9
                  ? "bg-gradient-to-r from-amber-400 to-red-400"
                  : "bg-gradient-to-r from-violet-500 to-fuchsia-400",
              )}
              style={{ width: `${Math.max(4, share * 100)}%` }}
            />
          </div>
        )}
      </div>
    </div>
  );
}
