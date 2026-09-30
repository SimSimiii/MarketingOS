import Link from "next/link";
import { Compass } from "lucide-react";

import { buttonVariants } from "@/components/ui/button";

/**
 * An address that matches no route at all - a mistyped URL, an old bookmark.
 *
 * Without this file Next draws its own bare "404 | This page could not be
 * found" in the middle of the workspace chrome, in a type and a colour that
 * belong to no page of this product.
 */
export default function NotFound() {
  return (
    <div className="studio-hero mx-auto mt-10 max-w-lg overflow-hidden rounded-2xl border border-border p-8 text-center sm:p-10">
      <span className="mx-auto mb-5 flex size-12 items-center justify-center rounded-2xl border border-violet-400/25 bg-violet-500/10 text-violet-300">
        <Compass className="size-6" aria-hidden="true" />
      </span>
      <p className="text-[10px] font-medium uppercase tracking-[0.2em] text-violet-300">404</p>
      <h1 className="mt-2 text-xl font-semibold tracking-tight">This page is not here</h1>
      <p className="mx-auto mt-3 max-w-sm text-sm leading-relaxed text-muted-foreground">
        The address may be mistyped, or what it pointed to has moved. Everything you made is still
        in your workspace.
      </p>
      <div className="mt-7 flex flex-wrap justify-center gap-2">
        <Link href="/" className={buttonVariants({ size: "lg" })}>
          Back to overview
        </Link>
        <Link href="/campaigns" className={buttonVariants({ variant: "outline", size: "lg" })}>
          Campaigns
        </Link>
      </div>
    </div>
  );
}
