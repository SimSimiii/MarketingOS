"use client";

import { usePathname } from "next/navigation";

import { CommandPalette } from "@/components/command-palette";
import { MobileHeader, Sidebar } from "@/components/layout/sidebar";
import { normalizePath } from "@/lib/paths";

/** Routes that are the whole page: no sidebar, no workspace chrome. The
 * session-renewal screen is one of them - it is a moment between two pages,
 * and a sidebar full of links behind it would ask for data with a session
 * that is being replaced. */
const BARE_ROUTES = new Set(["/login", "/register", "/session/renew"]);

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = normalizePath(usePathname());

  // Signing in is not part of the workspace, and a sidebar full of links to
  // pages that will redirect straight back here is worse than no sidebar.
  if (BARE_ROUTES.has(pathname)) {
    return (
      <main id="main-content" className="min-h-dvh">
        {children}
      </main>
    );
  }

  return (
    <div className="flex min-h-dvh w-full flex-col lg:flex-row">
      <a
        href="#main-content"
        className="sr-only fixed top-4 left-4 z-50 rounded-lg bg-primary px-4 py-3 text-primary-foreground focus:not-sr-only"
      >
        Skip to content
      </a>
      <Sidebar />
      <MobileHeader />
      <main
        id="main-content"
        tabIndex={-1}
        className="min-w-0 flex-1 px-4 pt-7 pb-16 outline-none sm:px-8 sm:pt-10 lg:px-12 lg:pt-12"
      >
        <div className="mx-auto w-full max-w-[78rem]">{children}</div>
      </main>
      <CommandPalette />
    </div>
  );
}
