"use client";

import { useEffect, useState } from "react";
import { Loader2, RefreshCw } from "lucide-react";

import { AuthWordmark } from "@/components/auth-form";
import { Button } from "@/components/ui/button";
import { renewSession } from "@/lib/renew-session";

/**
 * The moment between an expired access token and the page the reader was on.
 *
 * It used to be a bare paragraph in French in an English console, unstyled,
 * with an unstyled button under it. It is on screen for a fraction of a
 * second when it works, and it is the whole page when the API is down, so it
 * is worth the same care as the sign-in page beside it.
 */
export default function RenewSessionPage() {
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    const requested = new URLSearchParams(window.location.search).get("next") || "/";
    const next = requested.startsWith("/") && !requested.startsWith("//") && !requested.includes("\\")
      && !requested.startsWith("/session/renew") ? requested : "/";
    void renewSession().then(ok => {
      if (active) window.location.replace(ok ? next : `/login/?next=${encodeURIComponent(next)}`);
    }).catch(() => { if (active) setError("The sign-in service is unavailable right now."); });
    return () => { active = false; };
  }, []);

  return (
    <div className="flex min-h-dvh items-center justify-center px-5">
      <div className="w-full max-w-sm text-center">
        <div className="mb-10 flex justify-center">
          <AuthWordmark />
        </div>
        <div role={error ? "alert" : "status"} className="studio-hero rounded-3xl px-8 py-10">
          {error ? (
            <>
              <p className="font-display text-3xl">Connection lost</p>
              <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
                {error} Your work is saved - try again in a moment.
              </p>
              <Button className="mt-7" onClick={() => window.location.reload()}>
                <RefreshCw aria-hidden="true" />
                Try again
              </Button>
            </>
          ) : (
            <>
              <Loader2 className="mx-auto size-6 animate-spin text-violet-300" aria-hidden="true" />
              <p className="mt-5 text-sm text-muted-foreground">Renewing your session…</p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
