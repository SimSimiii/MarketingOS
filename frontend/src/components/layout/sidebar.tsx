"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

//: Knowledge and market are not listed here, and that is the point: both
//: belong to a business, so both live inside one, under /brands/[id]. A
//: top-level "Market" would have to pick a brand for the reader, and the one
//: it picks is never the one they meant.
const NAV_ITEMS = [
  { href: "/", label: "Dashboard" },
  { href: "/campaigns", label: "Campaigns" },
  { href: "/live", label: "Live" },
  { href: "/brands", label: "Brands" },
  { href: "/knowledge", label: "Campaign sources" },
  { href: "/settings", label: "Settings" },
  { href: "/logs", label: "Activity" },
];

export function Sidebar() {
  const pathname = usePathname();

  // Longest prefix wins, so a nested item would not light up its parent as
  // well and leave the sidebar unable to say where you are.
  const activeHref = NAV_ITEMS.filter((item) =>
    item.href === "/" ? pathname === "/" : pathname.startsWith(item.href),
  ).sort((a, b) => b.href.length - a.href.length)[0]?.href;

  return (
    <aside className="flex w-60 shrink-0 flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground">
      <div className="px-5 py-6">
        <span className="text-lg font-semibold tracking-tight text-primary">MarketingOS</span>
        <p className="mt-1 text-xs text-sidebar-foreground/60">Your marketing team, on demand</p>
      </div>
      <nav className="flex-1 space-y-1 px-3">
        {NAV_ITEMS.map((item) => {
          const active = item.href === activeHref;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "block rounded-md px-3 py-2 text-sm font-medium transition-colors",
                active
                  ? "bg-sidebar-accent text-sidebar-accent-foreground"
                  : "text-sidebar-foreground/70 hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground",
              )}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
