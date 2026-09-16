"use client";

import { useRouter } from "next/navigation";
import { useTransition } from "react";
import Link from "next/link";
import { AlertTriangle } from "lucide-react";
import { Button, buttonVariants } from "@/components/ui/button";

export default function ErrorPage({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  return (
    <div
      role="alert"
      className="studio-hero mx-auto mt-10 max-w-lg overflow-hidden rounded-2xl border border-amber-400/20 p-8 text-center sm:p-10"
    >
      <span className="mx-auto mb-5 flex size-12 items-center justify-center rounded-2xl border border-amber-400/25 bg-amber-400/10 text-amber-300">
        <AlertTriangle className="size-6" aria-hidden="true" />
      </span>
      <h1 className="text-xl font-semibold tracking-tight">We couldn&rsquo;t load this page</h1>
      <p className="mx-auto mt-3 max-w-sm text-sm leading-relaxed text-muted-foreground">
        Your workspace may be temporarily unavailable. Nothing has been lost &mdash; try loading it
        again.
      </p>
      <div className="mt-7 flex flex-wrap justify-center gap-2">
        <Button
          size="lg"
          disabled={pending}
          onClick={() => startTransition(() => {
            router.refresh();
            reset();
          })}
        >
          {pending ? "Retrying…" : "Try again"}
        </Button>
        <Link href="/" className={buttonVariants({ variant: "outline", size: "lg" })}>
          Back to overview
        </Link>
      </div>
    </div>
  );
}
