"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BookOpen, Compass, Files, LayoutDashboard, ContactRound, Palette } from "lucide-react";
import { cn } from "@/lib/utils";

export function BrandNav({ brandId, counts }: { brandId: string; counts: { sources: number; facts: number | null; rivals: number; alerts: number } }) {
  const pathname = usePathname();
  const base = `/brands/${brandId}`;
  const items = [
    { href: base, label: "Overview", hint: "At a glance", icon: LayoutDashboard, badge: null, exact: true },
    { href: `${base}/knowledge`, label: "Sources", hint: "Your material", icon: Files, badge: counts.sources },
    { href: `${base}/knowledge/base`, label: "Knowledge", hint: "Facts & evidence", icon: BookOpen, badge: counts.facts },
    { href: `${base}/market`, label: "Market", hint: "Buyers & competitors", icon: Compass, badge: counts.alerts || counts.rivals },
    { href: `${base}/linkedin`, label: "LinkedIn", hint: "Find people", icon: ContactRound, badge: null },
    { href: `${base}/identity`, label: "Identity", hint: "Email appearance", icon: Palette, badge: null },
  ];
  const active = items.filter((item) => item.exact ? pathname === item.href : pathname === item.href || pathname.startsWith(`${item.href}/`)).sort((a, b) => b.href.length - a.href.length)[0]?.href;
  return <nav aria-label="Brand workspace" className="grid grid-cols-2 gap-2 rounded-2xl border border-border bg-card/50 p-2 sm:grid-cols-3 xl:grid-cols-6">
    {items.map(({ icon: Icon, ...item }) => <Link key={item.href} href={item.href} aria-current={item.href === active ? "page" : undefined} className={cn("min-w-0 rounded-xl border p-2.5 transition-colors", item.href === active ? "border-violet-400/40 bg-violet-500/15 text-foreground shadow-sm" : "border-transparent text-muted-foreground hover:border-border hover:bg-accent/30 hover:text-foreground")}>
      <span className="flex items-center gap-2"><Icon className={cn("size-4 shrink-0", item.href === active && "text-violet-300")} /><span className="whitespace-nowrap text-[13px] font-semibold">{item.label}</span>{item.badge !== null && item.badge > 0 && <span className="ml-auto shrink-0 whitespace-nowrap rounded-md bg-background/60 px-1.5 py-0.5 text-[10px] tabular-nums">{item.badge}{item.label === "Market" && counts.alerts > 0 ? " new" : ""}</span>}</span>
      <span className="mt-1.5 hidden text-[11px] text-muted-foreground sm:block">{item.hint}</span>
    </Link>)}
  </nav>;
}
