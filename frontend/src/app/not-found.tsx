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
    <div className="studio-hero rise mx-auto mt-6 max-w-xl overflow-hidden rounded-3xl px-8 py-12 text-center sm:mt-12 sm:px-12">
      <div aria-hidden="true" className="bg-grid pointer-events-none absolute inset-0 -z-10" />
      <span className="icon-tile mx-auto mb-6 flex size-14 items-center justify-center rounded-2xl">
        <Compass className="size-6" aria-hidden="true" />
      </span>
      <p className="font-display text-7xl leading-none text-gradient-accent">404</p>
      <h1 className="mt-4 text-xl font-semibold tracking-tight">This page is not here</h1>
      <p className="mx-auto mt-3 max-w-sm text-sm leading-relaxed text-muted-foreground">
        The address may be mistyped, or what it pointed to has moved. Everything you made is still
        in your workspace.
      </p>
      <div className="mt-8 flex flex-wrap justify-center gap-2">
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
