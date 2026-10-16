"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { useRouteIds } from "@/lib/page-data";

/**
 * LinkedIn left the brand workspace; old links to it land on the brand.
 *
 * In the browser rather than with `redirect()`: the console is a static
 * export, so a server redirect is decided once at build time, for the
 * placeholder id "_" - every brand's old LinkedIn link was sent to
 * `/brands/_`, a page with no brand behind it. Only the address bar knows
 * the real id.
 */
export function LinkedInRedirect() {
  const { brandId } = useRouteIds();
  const router = useRouter();
  useEffect(() => {
    router.replace(brandId ? `/brands/${brandId}` : "/brands");
  }, [brandId, router]);
  return null;
}
