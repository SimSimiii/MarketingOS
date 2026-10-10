"use client";

import { useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { API_URL } from "@/lib/config";

type Mode = "login" | "register";

/**
 * Sign in and sign up, in one component.
 *
 * They differ by two fields and a verb, and keeping them apart meant two
 * copies of the same error handling, the same redirect logic and the same
 * layout - which is how one of them ends up with a bug the other does not.
 *
 * It posts to the API's own `/auth/*`, on this origin (CloudFront routes
 * /api/* to it). The API answers with the session as two cookies: the access
 * token, readable by script so the client can send it as a bearer header, and
 * the refresh token, httpOnly and scoped to /api/auth.
 */
export function AuthForm({ mode, allowSignup }: { mode: Mode; allowSignup: boolean }) {
  const params = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [company, setCompany] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const signingUp = mode === "register";

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (signingUp && !allowSignup) return;
    setBusy(true);
    setError("");
    try {
      const response = await fetch(`${API_URL}/auth/${mode}`, {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(
          signingUp
            ? {
                email,
                password,
                full_name: fullName || undefined,
                company_name: company || undefined,
              }
            : { email, password },
        ),
      });
      if (!response.ok) {
        const body = (await response.json().catch(() => null)) as { detail?: unknown } | null;
        // A string from the API's own checks, or a list from request
        // validation (a malformed address, say) - rendering the list itself
        // would crash the form instead of explaining.
        const detail = body?.detail;
        const first = Array.isArray(detail) ? (detail[0] as { msg?: unknown } | undefined)?.msg : detail;
        setError(typeof first === "string" && first ? first : "That did not work. Try again.");
        return;
      }
      // Only a path from this origin: `next` is resolved against the current
      // origin and anything that lands elsewhere is dropped, so a crafted
      // ?next= cannot bounce somebody off the site after they sign in.
      const requested = params.get("next");
      const destination =
        requested && new URL(requested, window.location.origin).origin === window.location.origin
          ? requested
          : "/";
      // A full load rather than a client navigation: the whole app starts
      // again with the cookies that were just set.
      window.location.replace(destination);
    } catch {
      setError("Could not reach the server. Is the API running?");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto flex min-h-[80vh] w-full max-w-md flex-col justify-center">
      <div className="mb-8 flex items-center justify-center gap-3">
        <span className="flex size-10 items-center justify-center rounded-xl border border-violet-400/30 bg-violet-500/15 text-violet-300 shadow-[0_0_24px_-6px_oklch(0.62_0.22_292/0.7)]">
          <Sparkles className="size-5" aria-hidden="true" />
        </span>
        <span className="text-xl font-semibold tracking-tight">
          Marketing<span className="text-violet-300">OS</span>
        </span>
      </div>

      {/* The one page a signed-out visitor can reach, so it gets the same
          surface the workspace uses rather than bare fields on the ground. */}
      <div className="studio-hero rounded-2xl border border-violet-400/15 p-6 sm:p-8">
      <h1 className="text-2xl font-semibold tracking-tight">
        {signingUp ? "Create your account" : "Sign in"}
      </h1>
      <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
        {signingUp
          ? "One account holds your businesses, their compiled knowledge, and every campaign written from it."
          : "Your businesses, their knowledge and their campaigns are behind this."}
      </p>

      {signingUp && !allowSignup && (
        <p className="mt-4 rounded-lg border border-border bg-muted/40 px-3 py-2 text-sm text-muted-foreground">
          Access is currently by invitation. Ask the person who invited you to create your
          account, then return to Sign in.
        </p>
      )}

      <form onSubmit={submit} className="mt-6 space-y-4">
        <div className="space-y-1.5">
          <Label htmlFor="email">Email</Label>
          <Input
            id="email"
            type="email"
            className="h-10"
            autoComplete="username"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        </div>

        {signingUp && (
          <>
            <div className="space-y-1.5">
              <Label htmlFor="full-name">Your name</Label>
              <Input
                id="full-name"
                className="h-10"
                autoComplete="name"
                value={fullName}
                onChange={(event) => setFullName(event.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="company">Company</Label>
              <Input
                id="company"
                className="h-10"
                autoComplete="organization"
                value={company}
                onChange={(event) => setCompany(event.target.value)}
              />
            </div>
          </>
        )}

        <div className="space-y-1.5">
          <Label htmlFor="password">Password</Label>
          <Input
            id="password"
            type="password"
            className="h-10"
            autoComplete={signingUp ? "new-password" : "current-password"}
            required
            minLength={signingUp ? 10 : undefined}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
          {signingUp && (
            <p className="text-xs text-muted-foreground">
              At least 10 characters. Length is the only rule - a passphrase beats
              punctuation.
            </p>
          )}
        </div>

        {error && (
          <p
            role="alert"
            className="rounded-lg border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive"
          >
            {error}
          </p>
        )}

        <Button type="submit" size="lg" disabled={busy || (signingUp && !allowSignup)} className="w-full">
          {busy
            ? signingUp
              ? "Creating…"
              : "Signing in…"
            : signingUp
              ? "Create account"
              : "Sign in"}
        </Button>
      </form>
      </div>

      <p className="mt-6 text-center text-sm text-muted-foreground">
        {signingUp ? (
          <>
            Already have an account?{" "}
            <Link href="/login" className="text-violet-300 hover:underline">
              Sign in
            </Link>
          </>
        ) : allowSignup ? (
          <>
            No account yet?{" "}
            <Link href="/register" className="text-violet-300 hover:underline">
              Create one
            </Link>
          </>
        ) : (
          "Accounts are created by invitation while the product is in testing."
        )}
      </p>
    </div>
  );
}
