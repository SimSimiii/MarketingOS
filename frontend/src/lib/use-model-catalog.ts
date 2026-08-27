"use client";

import { useEffect, useState } from "react";

import { api } from "@/lib/api-client";
import type { ModelCatalog } from "@/lib/types";

/** One in-flight request for the whole app.
 *
 * The catalog is static for the lifetime of a backend build, and two screens
 * offer the picker. Without this, opening the new-campaign dialog on a page
 * that already shows the campaign's own picker fetches the same unchanging
 * list twice. Kept as the promise rather than the result so concurrent callers
 * share the first request instead of racing a second one. */
let cached: Promise<ModelCatalog> | null = null;

function load(): Promise<ModelCatalog> {
  if (cached === null) {
    cached = api.getModelCatalog().catch((error: unknown) => {
      // A failed fetch must not poison the cache, or the picker stays broken
      // until a full reload even after the backend comes back.
      cached = null;
      throw error;
    });
  }
  return cached;
}

/** The model catalog, or `null` until it arrives.
 *
 * Null rather than a thrown error on failure: the picker is an enhancement
 * over the preset, and a backend that cannot serve the catalog should cost the
 * user the picker, not the screen it sits on.
 */
export function useModelCatalog(): ModelCatalog | null {
  const [catalog, setCatalog] = useState<ModelCatalog | null>(null);

  useEffect(() => {
    let live = true;
    load()
      .then((result) => {
        if (live) setCatalog(result);
      })
      .catch(() => undefined);
    return () => {
      live = false;
    };
  }, []);

  return catalog;
}
