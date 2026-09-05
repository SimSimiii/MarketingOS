import { Sidebar } from "@/components/layout/sidebar";

export function AppShell({ children }: { children: React.ReactNode }) {
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
