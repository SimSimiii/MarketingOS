"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, ArrowUpRight, AudioLines, BookOpen, Building2, LayoutDashboard, Mail, Settings2, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

// Knowledge and market remain inside each brand's workspace.
const NAV_ITEMS = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/campaigns", label: "Campaigns", icon: Mail },
  { href: "/live", label: "Live runs", icon: AudioLines },
  { href: "/brands", label: "Brands", icon: Building2 },
  { href: "/knowledge", label: "Campaign sources", icon: BookOpen },
  { href: "/logs", label: "Activity", icon: Activity },
  { href: "/settings", label: "Settings", icon: Settings2 },
];

export function Sidebar() {
  const pathname = usePathname();
  const activeHref = NAV_ITEMS.find((item) => item.href === "/" ? pathname === "/" : pathname === item.href || pathname.startsWith(`${item.href}/`))?.href;

  return (
    <aside className="border-b border-sidebar-border bg-sidebar text-sidebar-foreground lg:sticky lg:top-0 lg:flex lg:h-dvh lg:w-60 lg:shrink-0 lg:flex-col lg:border-r lg:border-b-0">
      <Link href="/" className="flex items-center gap-3 px-5 py-5 lg:px-6 lg:py-8" aria-label="MarketingOS home">
        <span className="flex size-9 items-center justify-center rounded-xl border border-violet-400/30 bg-violet-500/15 text-violet-300"><Sparkles className="size-5" aria-hidden="true" /></span>
        <span className="text-lg font-semibold tracking-tight">Marketing<span className="text-violet-300">OS</span></span>
      </Link>
      <p className="hidden px-6 pb-3 text-[10px] font-medium tracking-[0.2em] text-muted-foreground lg:block">WORKSPACE</p>
      <nav aria-label="Main navigation" className="flex gap-1 overflow-x-auto px-3 pb-3 lg:flex-1 lg:flex-col lg:overflow-y-auto">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active = href === activeHref;
          return (
            <Link key={href} href={href} aria-current={active ? "page" : undefined} className={cn("flex shrink-0 items-center gap-3 rounded-lg border px-3 py-3 text-sm font-medium transition-colors", active ? "border-violet-400/15 bg-violet-500/12 text-violet-200" : "border-transparent text-muted-foreground hover:bg-sidebar-accent/60 hover:text-foreground")}>
              <Icon className="size-4 shrink-0" aria-hidden="true" />{label}
              {active && <span className="ml-auto hidden size-1.5 rounded-full bg-violet-400 lg:block" aria-hidden="true" />}
            </Link>
          );
        })}
      </nav>
      <div className="hidden p-4 lg:block">
        <Link href="/brands" className="block rounded-xl border border-border bg-background/40 p-4 transition-colors hover:border-violet-400/30">
          <div className="flex items-center justify-between text-xs font-medium">Built on your business<ArrowUpRight className="size-3.5 text-violet-300" aria-hidden="true" /></div>
          <p className="mt-2 text-xs leading-relaxed text-muted-foreground">Better sources. Stronger proof. Copy that sounds like you.</p>
        </Link>
        <p className="px-2 pt-4 text-[10px] tracking-widest text-muted-foreground">YOUR EMAIL STUDIO</p>
      </div>
    </aside>
  );
}
