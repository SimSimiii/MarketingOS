"use client";

import { useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { ArrowRight, Eye, Layers, ShieldCheck, Sparkles } from "lucide-react";

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
    <div className="grid min-h-dvh lg:grid-cols-[minmax(0,1.05fr)_minmax(0,1fr)]">
      <AuthShowcase />

      <section className="relative flex items-center justify-center px-5 py-12 sm:px-8">
        <div className="w-full max-w-[26rem]">
          <Link href="/" className="mb-10 flex justify-center lg:hidden" aria-label="MarketingOS home">
            <AuthWordmark />
          </Link>

          {/* The one page a signed-out visitor can reach, so it gets the same
              surface the workspace uses rather than bare fields on the ground. */}
          <div className="studio-hero rise rounded-3xl p-7 sm:p-9">
            <p className="mb-3 flex items-center gap-2.5 text-[0.6875rem] font-medium uppercase tracking-[0.2em] text-violet-300/90">
              <span className="h-px w-6 bg-gradient-to-r from-violet-400/80 to-transparent" aria-hidden="true" />
              {signingUp ? "Join the studio" : "Welcome back"}
            </p>
            <h1 className="font-display text-[2.5rem] leading-[1.05] text-gradient">
              {signingUp ? "Create your account" : "Sign in"}
            </h1>
            <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
              {signingUp
                ? "One account holds your businesses, their compiled knowledge, and every campaign written from it."
                : "Your businesses, their knowledge and their campaigns are behind this."}
            </p>

            {signingUp && !allowSignup && (
              <p className="mt-5 rounded-xl border border-white/[0.08] bg-white/[0.03] px-4 py-3 text-sm leading-relaxed text-muted-foreground">
                Access is currently by invitation. Ask the person who invited you to create your
                account, then return to Sign in.
              </p>
            )}

            <form onSubmit={submit} className="mt-7 space-y-5">
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  className="h-11"
                  autoComplete="username"
                  placeholder="you@company.com"
                  required
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                />
              </div>

              {signingUp && (
                <div className="grid gap-5 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="full-name">Your name</Label>
                    <Input
                      id="full-name"
                      className="h-11"
                      autoComplete="name"
                      value={fullName}
                      onChange={(event) => setFullName(event.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="company">Company</Label>
                    <Input
                      id="company"
                      className="h-11"
                      autoComplete="organization"
                      value={company}
                      onChange={(event) => setCompany(event.target.value)}
                    />
                  </div>
                </div>
              )}

              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <Input
                  id="password"
                  type="password"
                  className="h-11"
                  autoComplete={signingUp ? "new-password" : "current-password"}
                  required
                  minLength={signingUp ? 10 : undefined}
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                />
                {signingUp && (
                  <p className="text-xs leading-relaxed text-muted-foreground">
                    At least 10 characters. Length is the only rule - a passphrase beats
                    punctuation.
                  </p>
                )}
              </div>

              {error && (
                <p
                  role="alert"
                  className="rounded-xl border border-red-400/25 bg-red-500/[0.07] px-4 py-3 text-sm text-red-200"
                >
                  {error}
                </p>
              )}

              <Button
                type="submit"
                size="lg"
                disabled={busy || (signingUp && !allowSignup)}
                className="h-11 w-full text-[0.9375rem]"
              >
                {busy
                  ? signingUp
                    ? "Creating…"
                    : "Signing in…"
                  : signingUp
                    ? "Create account"
                    : "Sign in"}
                {!busy && <ArrowRight aria-hidden="true" />}
              </Button>
            </form>
          </div>

          <p className="mt-7 text-center text-sm text-muted-foreground">
            {signingUp ? (
              <>
                Already have an account?{" "}
                <Link href="/login" className="font-medium text-violet-300 hover:text-violet-200 hover:underline">
                  Sign in
                </Link>
              </>
            ) : allowSignup ? (
              <>
                No account yet?{" "}
                <Link href="/register" className="font-medium text-violet-300 hover:text-violet-200 hover:underline">
                  Create one
                </Link>
              </>
            ) : (
              "Accounts are created by invitation while the product is in testing."
            )}
          </p>
        </div>
      </section>
    </div>
  );
}

export function AuthWordmark() {
  return (
    <span className="flex items-center gap-3">
      <span className="brand-mark flex size-10 items-center justify-center rounded-xl text-white">
        <Sparkles className="size-5" aria-hidden="true" />
      </span>
      <span className="text-xl font-semibold tracking-tight">
        Marketing<span className="text-gradient-accent">OS</span>
      </span>
    </span>
  );
}

const PROMISES = [
  {
    icon: ShieldCheck,
    title: "Only what you can prove",
    body: "Every number, price and quotation is checked against your own material before a draft can ship.",
  },
  {
    icon: Eye,
    title: "Read cold, first",
    body: "Each email is read by someone who has never seen the brief. What they could not follow is rewritten.",
  },
  {
    icon: Layers,
    title: "One home per business",
    body: "Sources, compiled knowledge and market context stay with the brand, and every campaign reuses them.",
  },
];

/** The half of the sign-in page that says what is behind it. Hidden on a
 * phone, where the form is the whole job. */
function AuthShowcase() {
  return (
    <aside className="relative isolate hidden overflow-hidden border-r border-white/[0.06] lg:flex lg:flex-col lg:justify-between lg:p-12 xl:p-16">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(ellipse_70%_55%_at_20%_0%,oklch(0.5_0.22_293/30%),transparent_70%),radial-gradient(ellipse_60%_50%_at_100%_100%,oklch(0.5_0.16_262/18%),transparent_70%)]"
      />
      <div aria-hidden="true" className="bg-grid pointer-events-none absolute inset-0 -z-10 opacity-70" />

      <Link href="/" aria-label="MarketingOS home" className="w-fit rounded-xl">
        <AuthWordmark />
      </Link>

      <div className="max-w-xl">
        <h2 className="font-display text-[3.25rem] leading-[1.02] xl:text-[3.75rem]">
          Email copy written from{" "}
          <span className="text-gradient-accent italic">your own material</span>, read cold before
          you ever see it.
        </h2>
        <ul className="rise-stagger mt-12 space-y-6">
          {PROMISES.map(({ icon: Icon, title, body }) => (
            <li key={title} className="flex gap-4">
              <span className="icon-tile flex size-10 shrink-0 items-center justify-center rounded-xl">
                <Icon className="size-[1.125rem]" aria-hidden="true" />
              </span>
              <span>
                <span className="block text-[0.9375rem] font-semibold">{title}</span>
                <span className="mt-1 block text-sm leading-relaxed text-muted-foreground">{body}</span>
              </span>
            </li>
          ))}
        </ul>
      </div>

      <p className="text-xs text-muted-foreground/70">MarketingOS · Grounded email studio</p>
    </aside>
  );
}
