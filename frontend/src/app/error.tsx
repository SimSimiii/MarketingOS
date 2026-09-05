"use client";

import { useRouter } from "next/navigation";
import { useTransition } from "react";
import { AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function ErrorPage({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  return (
    <div role="alert" className="mx-auto max-w-lg rounded-2xl border border-border bg-card p-8 text-center">
      <AlertCircle className="mx-auto mb-4 size-8 text-amber-300" aria-hidden="true" />
      <h1 className="text-xl font-semibold">We couldn’t load this page</h1>
      <p className="mt-3 text-sm leading-relaxed text-muted-foreground">Your workspace may be temporarily unavailable. Try loading it again.</p>
      <Button className="mt-6" disabled={pending} onClick={() => startTransition(() => { router.refresh(); reset(); })}>{pending ? "Retrying…" : "Try again"}</Button>
    </div>
  );
}
