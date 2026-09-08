"use client";

import { usePathname } from "next/navigation";

import { Sidebar } from "@/components/layout/sidebar";

/** Routes that are the whole page: no sidebar, no workspace chrome. */
const BARE_ROUTES = new Set(["/login", "/register"]);

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  // Signing in is not part of the workspace, and a sidebar full of links to
  // pages that will redirect straight back here is worse than no sidebar.
  if (BARE_ROUTES.has(pathname)) {
    return (
      <main id="main-content" className="px-5 py-10 sm:px-8">
        {children}
      </main>
    );
  }

  return (
    <div className="flex min-h-screen w-full flex-col lg:flex-row">
      <a href="#main-content" className="sr-only fixed left-4 top-4 z-50 rounded-lg bg-primary px-4 py-3 text-primary-foreground focus:not-sr-only">Skip to content</a>
      <Sidebar />
      <main id="main-content" tabIndex={-1} className="min-w-0 flex-1 px-5 py-8 outline-none sm:px-8 lg:px-10 lg:py-10">
        <div className="mx-auto w-full max-w-7xl">{children}</div>
      </main>
    </div>
  );
}
