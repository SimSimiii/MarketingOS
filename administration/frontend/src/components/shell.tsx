"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Building2,
  ClipboardList,
  LayoutDashboard,
  LogOut,
  ShieldCheck,
  Users,
} from "lucide-react";

import { useRequireSession } from "@/lib/session";
import { Badge, cn } from "@/components/ui";

const NAV = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/users/", label: "Accounts", icon: Users },
  { href: "/admins/", label: "Operators", icon: ShieldCheck },
  { href: "/audit/", label: "Audit trail", icon: ClipboardList },
];

/**
 * The frame every signed-in page renders inside.
 *
 * It also holds the session gate, so a page cannot be added later that forgets
 * to check - if it is inside the shell it is behind the gate, and if it is not,
 * it is the sign-in page.
 */
export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { admin, loading, signOut } = useRequireSession();

  if (loading || admin === null) {
    return (
      <div className="grid min-h-dvh place-items-center text-sm text-muted">
        {loading ? "Checking your session…" : "Redirecting to sign in…"}
      </div>
    );
  }

  const active = NAV.find((item) =>
    item.href === "/" ? pathname === "/" : pathname.startsWith(item.href),
  )?.href;

  return (
    <div className="flex min-h-dvh flex-col lg:flex-row">
      <aside className="border-b border-line bg-surface-2 lg:sticky lg:top-0 lg:flex lg:h-dvh lg:w-60 lg:shrink-0 lg:flex-col lg:border-r lg:border-b-0">
        <div className="flex items-center gap-3 px-5 py-5">
          <span className="grid size-8 place-items-center rounded-lg border border-violet/35 bg-violet/15">
            <Building2 className="size-4 text-violet-soft" aria-hidden="true" />
          </span>
          <span className="text-sm font-semibold tracking-tight">
            MarketingOS
            <span className="block text-[11px] font-normal tracking-widest text-muted">
              BACK-OFFICE
            </span>
          </span>
        </div>

        <nav aria-label="Console" className="flex gap-1 overflow-x-auto px-3 pb-3 lg:flex-1 lg:flex-col">
          {NAV.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              aria-current={href === active ? "page" : undefined}
              className={cn(
                "flex shrink-0 items-center gap-3 rounded-lg border px-3 py-2.5 text-sm font-medium transition-colors",
                href === active
                  ? "border-violet/20 bg-violet/12 text-violet-soft"
                  : "border-transparent text-muted hover:bg-white/5 hover:text-fg",
              )}
            >
              <Icon className="size-4 shrink-0" aria-hidden="true" />
              {label}
            </Link>
          ))}
        </nav>

        <div className="hidden border-t border-line p-4 lg:block">
          <p className="truncate text-sm font-medium">{admin.full_name ?? admin.email}</p>
          <p className="mt-0.5 truncate text-xs text-muted">{admin.email}</p>
          <div className="mt-2">
            <Badge tone="violet">{admin.role}</Badge>
          </div>
          <button
            onClick={signOut}
            className="mt-3 flex w-full items-center gap-2 rounded-lg border border-line px-3 py-2 text-sm text-muted transition-colors hover:border-danger/40 hover:text-danger"
          >
            <LogOut className="size-4" aria-hidden="true" />
            Sign out
          </button>
        </div>
      </aside>

      <main className="min-w-0 flex-1 px-5 py-8 sm:px-8 lg:px-10">
        <div className="mx-auto w-full max-w-6xl">{children}</div>
      </main>
    </div>
  );
}

export function PageHeader({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        {description && <p className="mt-1 max-w-2xl text-sm text-muted">{description}</p>}
      </div>
      {action}
    </header>
  );
}
