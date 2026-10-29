"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BookOpen, Compass, Files, LayoutDashboard, Palette, MailCheck } from "lucide-react";
import { cn } from "@/lib/utils";
import { normalizePath } from "@/lib/paths";

export function BrandNav({ brandId, counts }: { brandId: string; counts: { sources: number; facts: number | null; rivals: number; alerts: number } }) {
  const pathname = normalizePath(usePathname());
  const base = `/brands/${brandId}`;
  const items = [
    { href: base, label: "Overview", hint: "At a glance", icon: LayoutDashboard, badge: null, exact: true },
    { href: `${base}/knowledge`, label: "Sources", hint: "Your material", icon: Files, badge: counts.sources },
    { href: `${base}/knowledge/base`, label: "Knowledge", hint: "Facts & evidence", icon: BookOpen, badge: counts.facts },
    { href: `${base}/market`, label: "Market", hint: "Buyers & competitors", icon: Compass, badge: counts.alerts || counts.rivals },
    { href: `${base}/email-analysis`, label: "Email review", hint: "Analyse your draft", icon: MailCheck, badge: null },
    { href: `${base}/identity`, label: "Identity", hint: "Email appearance", icon: Palette, badge: null },
  ];
  const active = items.filter((item) => item.exact ? pathname === item.href : pathname === item.href || pathname.startsWith(`${item.href}/`)).sort((a, b) => b.href.length - a.href.length)[0]?.href;
  return (
    <nav
      aria-label="Brand workspace"
      className="grid grid-cols-2 gap-1.5 rounded-2xl bg-black/25 p-1.5 shadow-[inset_0_1px_2px_0_oklch(0_0_0/30%)] ring-1 ring-white/[0.06] sm:grid-cols-3 xl:grid-cols-6"
    >
      {items.map(({ icon: Icon, ...item }) => {
        const current = item.href === active;
        const alert = item.label === "Market" && counts.alerts > 0;
        return (
          <Link
            key={item.href}
            href={item.href}
            aria-current={current ? "page" : undefined}
            className={cn(
              "group/tab min-w-0 rounded-xl px-3 py-2.5 transition-all duration-200",
              current
                ? "bg-[linear-gradient(180deg,oklch(0.55_0.2_293/26%),oklch(0.55_0.2_293/10%))] text-foreground shadow-[inset_0_1px_0_0_oklch(1_0_0/8%),0_0_0_1px_oklch(0.7_0.16_293/28%),0_8px_20px_-10px_oklch(0.55_0.22_293/60%)]"
                : "text-muted-foreground hover:bg-white/[0.04] hover:text-foreground",
            )}
          >
            <span className="flex items-center gap-2.5">
              <span
                className={cn(
                  "flex size-7 shrink-0 items-center justify-center rounded-lg transition-colors",
                  current ? "bg-violet-500/25 text-violet-100" : "bg-white/[0.04] group-hover/tab:text-foreground",
                )}
              >
                <Icon className="size-3.5" aria-hidden="true" />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-[0.8125rem] font-semibold">{item.label}</span>
                <span className="hidden truncate text-[0.6875rem] text-muted-foreground sm:block">{item.hint}</span>
              </span>
              {item.badge !== null && item.badge > 0 && (
                <span
                  className={cn(
                    "shrink-0 rounded-full px-1.5 py-0.5 text-[0.625rem] font-semibold whitespace-nowrap tabular-nums",
                    alert
                      ? "bg-amber-400/15 text-amber-200 ring-1 ring-amber-400/25"
                      : current
                        ? "bg-white/[0.1] text-foreground"
                        : "bg-white/[0.05] text-muted-foreground",
                  )}
                >
                  {item.badge}
                  {alert ? " new" : ""}
                </span>
              )}
            </span>
          </Link>
        );
      })}
    </nav>
  );
}
