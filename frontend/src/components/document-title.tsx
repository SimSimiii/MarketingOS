"use client";

import { useEffect } from "react";

const PRODUCT = "MarketingOS";

/**
 * The browser tab's title.
 *
 * The console is a static export, so every page ships the same `<title>` and
 * five open tabs all read "MarketingOS" - the one place a person looks to find
 * the campaign they left open. The page knows its own name only once its data
 * has loaded, so this sets it from the page rather than from metadata.
 */
export function DocumentTitle({ title }: { title: string | null | undefined }) {
  useEffect(() => {
    if (!title) return;
    const previous = document.title;
    document.title = `${title} · ${PRODUCT}`;
    return () => {
      document.title = previous;
    };
  }, [title]);
  return null;
}
