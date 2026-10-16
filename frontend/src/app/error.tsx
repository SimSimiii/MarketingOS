"use client";

import { useTransition } from "react";
import Link from "next/link";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { Button, buttonVariants } from "@/components/ui/button";
import { refreshPage } from "@/lib/page-data";

export default function ErrorPage({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  const [pending, startTransition] = useTransition();
  return (
    <div
      role="alert"
      className="studio-hero rise mx-auto mt-6 max-w-xl overflow-hidden rounded-3xl px-8 py-12 text-center sm:mt-12 sm:px-12"
    >
      <span className="mx-auto mb-6 flex size-14 items-center justify-center rounded-2xl bg-amber-400/10 text-amber-300 ring-1 ring-amber-400/25">
        <AlertTriangle className="size-6" aria-hidden="true" />
      </span>
      <h1 className="font-display text-[2.25rem] leading-tight">We couldn&rsquo;t load this page</h1>
      <p className="mx-auto mt-3 max-w-sm text-sm leading-relaxed text-muted-foreground">
        Your workspace may be temporarily unavailable. Try loading this page again, then check
        whether your latest changes were saved before repeating an action.
      </p>
      <div className="mt-8 flex flex-wrap justify-center gap-2">
        <Button
          size="lg"
          disabled={pending}
          onClick={() => startTransition(() => {
            refreshPage();
            reset();
          })}
        >
          <RefreshCw className={pending ? "motion-safe:animate-spin" : undefined} aria-hidden="true" />
          {pending ? "Retrying…" : "Try again"}
        </Button>
        <Link href="/" className={buttonVariants({ variant: "outline", size: "lg" })}>
          Back to overview
        </Link>
      </div>
    </div>
  );
}
