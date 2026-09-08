"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Building2 } from "lucide-react";

import { useSession } from "@/lib/session";
import { Button, Field, Notice } from "@/components/ui";

export default function LoginPage() {
  const { admin, loading, signIn } = useSession();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  // Somebody who already has a session should not be looking at a sign-in
  // form - most often they got here from a bookmark.
  useEffect(() => {
    if (!loading && admin !== null) router.replace("/");
  }, [loading, admin, router]);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await signIn(email, password);
      router.replace("/");
    } catch (exception) {
      setError(exception instanceof Error ? exception.message : "Sign-in failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid min-h-dvh place-items-center px-5 py-10">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex items-center gap-3">
          <span className="grid size-9 place-items-center rounded-lg border border-violet/35 bg-violet/15">
            <Building2 className="size-4 text-violet-soft" aria-hidden="true" />
          </span>
          <div>
            <p className="text-sm font-semibold tracking-tight">MarketingOS</p>
            <p className="text-[11px] tracking-widest text-muted">BACK-OFFICE</p>
          </div>
        </div>

        <form
          onSubmit={submit}
          className="space-y-4 rounded-xl border border-line bg-surface p-6"
        >
          <div>
            <h1 className="text-lg font-semibold tracking-tight">Sign in</h1>
            <p className="mt-1 text-sm text-muted">
              Operator accounts are created by a superadmin. There is no signup here.
            </p>
          </div>

          <Field
            label="Email"
            type="email"
            autoComplete="username"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
          <Field
            label="Password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />

          <Notice>{error}</Notice>

          <Button type="submit" variant="primary" className="w-full" disabled={busy}>
            {busy ? "Signing in…" : "Sign in"}
          </Button>
        </form>

        <p className="mt-4 text-center text-xs text-muted">
          Your session lasts as long as this tab. Closing it signs you out.
        </p>
      </div>
    </div>
  );
}
