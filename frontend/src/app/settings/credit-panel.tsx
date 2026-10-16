"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { Coins, RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api-client";
import type { CreditBalance } from "@/lib/types";

const PACKAGES = [
  { id: "starter", credits: 1000, price: "$10" },
  { id: "standard", credits: 3000, price: "$30" },
  { id: "growth", credits: 6000, price: "$60" },
];

export function CreditPanel() {
  const [account, setAccount] = useState<CreditBalance | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [paymentReturn, setPaymentReturn] = useState(false);
  const [updatedAt, setUpdatedAt] = useState<string | null>(null);
  const generation = useRef(0);

  const refresh = useCallback(async () => {
    const current = ++generation.current;
    api.invalidate();
    try {
      const value = await api.getCredits();
      if (generation.current !== current) return;
      setAccount(value);
      setError(null);
      setUpdatedAt(new Date().toLocaleTimeString());
      setPaymentReturn(new URLSearchParams(window.location.search).get("credits") === "return");
    } catch (failure) {
      if (generation.current === current) {
        setError(failure instanceof Error ? failure.message : "Credits are temporarily unavailable.");
      }
    }
  }, []);

  useEffect(() => {
    const returned = new URLSearchParams(window.location.search).get("credits") === "return";
    let checks = 0;
    let active = true;
    const requests = generation;
    void Promise.resolve().then(() => { if (active) void refresh(); });
    // The browser can return before Stripe delivers its signed webhook.
    const timer = returned ? window.setInterval(() => {
      checks += 1;
      void refresh();
      if (checks >= 12) window.clearInterval(timer);
    }, 5000) : undefined;
    return () => { active = false; ++requests.current; if (timer) window.clearInterval(timer); };
  }, [refresh]);

  if (!account || error) return <Card>
    <CardHeader><CardTitle className="flex items-center gap-3"><span className="icon-tile flex size-8 items-center justify-center rounded-lg"><Coins className="size-4" aria-hidden="true" /></span>Credits</CardTitle></CardHeader>
    <CardContent className="space-y-3">
      <p role={error ? "alert" : "status"} className="text-sm text-muted-foreground">{error ?? "Loading your credit balance…"}</p>
      {error && <Button type="button" variant="outline" onClick={() => void refresh()}>Retry</Button>}
    </CardContent>
  </Card>;
  if (!account.billing_active) return null;

  async function recharge(packageId: string) {
    setBusy(packageId);
    try {
      const checkout = await api.createCreditCheckout(packageId);
      window.location.assign(checkout.url);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not open checkout.");
      setBusy(null);
    }
  }

  return <Card>
    <CardHeader>
      <CardTitle className="flex items-center gap-3">
        <span className="icon-tile flex size-8 items-center justify-center rounded-lg"><Coins className="size-4" aria-hidden="true" /></span>
        Credits
      </CardTitle>
    </CardHeader>
    <CardContent className="space-y-5">
      {paymentReturn && <p role="status" className="rounded-xl border border-violet-400/20 bg-violet-500/[0.07] p-3.5 text-sm leading-relaxed">
        You returned from checkout. Credits are added only after payment confirmation.
        If the purchase is not listed yet, wait and refresh; do not pay again to resolve a delay.
      </p>}
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs text-muted-foreground">{updatedAt ? `Balance checked at ${updatedAt}` : ""}</p>
        <Button type="button" variant="outline" size="sm" onClick={() => void refresh()}><RefreshCw aria-hidden="true" />Refresh balance</Button>
      </div>
      <div>
        <p className="text-gradient text-5xl leading-none font-semibold tracking-tight tabular-nums">{account.balance.toLocaleString()}</p>
        <p className="mt-2 text-sm text-muted-foreground">Available credits · 1 credit = $0.01</p>
        <p className="mt-1 text-xs text-muted-foreground">Generation uses credits based on twice the measured processing cost. A reserve is taken before each step. Unused credits return after confirmed usage; an uncertain provider failure may keep a reserve pending review.</p>
        <p className="mt-1 text-xs text-muted-foreground">Credits do not increase your monthly job quota. Check your account limits before purchasing.</p>
      </div>
      <div className="grid gap-3 sm:grid-cols-3">
        {PACKAGES.map((item) => <button
          key={item.id} type="button" disabled={busy !== null}
          onClick={() => recharge(item.id)}
          className="group surface surface-interactive flex cursor-pointer flex-col items-start rounded-2xl p-4 text-left disabled:cursor-not-allowed disabled:opacity-50"
        >
          <span className="text-[0.6875rem] font-medium uppercase tracking-[0.16em] text-muted-foreground">{item.id}</span>
          <span className="mt-2 text-2xl font-semibold tracking-tight tabular-nums">{item.credits.toLocaleString()}</span>
          <span className="text-xs text-muted-foreground">credits</span>
          <span className="mt-3 rounded-full bg-violet-500/15 px-2.5 py-1 text-sm font-semibold text-violet-100 ring-1 ring-violet-400/25 transition-colors group-hover:bg-violet-500/25">
            {busy === item.id ? "Opening…" : item.price}
          </span>
        </button>)}
      </div>
      {account.movements.length > 0 && <div className="space-y-2 border-t border-hairline pt-4">
        <p className="text-sm font-semibold">Recent activity</p>
        <ul className="space-y-1.5 text-sm text-muted-foreground">
          {account.movements.map((movement, index) => <li
            key={`${movement.created_at}-${index}`} className="flex justify-between gap-4"
          >
            <span>
              {movement.kind === "purchase" ? "Recharge" : movement.kind === "release" ? "Unused credits returned" : movement.kind === "hold" ? "Generation reserve" : movement.kind}
              <span className="block text-xs">{new Date(movement.created_at).toLocaleString()} · balance {movement.balance_after.toLocaleString()}</span>
            </span>
            <span className={movement.amount > 0 ? "font-medium text-emerald-300 tabular-nums" : "tabular-nums"}>{movement.amount > 0 ? "+" : ""}{movement.amount}</span>
          </li>)}
        </ul>
      </div>}
    </CardContent>
  </Card>;
}
