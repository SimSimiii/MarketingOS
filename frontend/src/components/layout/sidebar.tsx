"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, ArrowUpRight, AudioLines, BookOpen, Building2, LayoutDashboard, Mail, Settings2, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import { AccountMenu } from "@/components/layout/account-menu";

// Knowledge and market remain inside each brand's workspace.
const NAV_ITEMS = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/campaigns", label: "Campaigns", icon: Mail },
  { href: "/live", label: "Runs", icon: AudioLines },
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
        <span className="flex size-9 items-center justify-center rounded-xl border border-violet-400/30 bg-violet-500/15 text-violet-300 shadow-[0_0_20px_-6px_oklch(0.62_0.22_292/0.6)]"><Sparkles className="size-5" aria-hidden="true" /></span>
        <span className="text-lg font-semibold tracking-tight">Marketing<span className="text-violet-300">OS</span></span>
      </Link>
      <p className="hidden px-6 pb-3 text-[10px] font-medium tracking-[0.2em] text-muted-foreground lg:block">WORKSPACE</p>
      {/*
        On a phone this nav is a horizontal strip that scrolls past the edge of
        the screen, and nothing said so: the last two items were simply gone.
        The mask fades the row out where it is cut off, which is the only
        affordance a touch device gets - there is no scrollbar to see.
      */}
      <nav
        aria-label="Main navigation"
        className="flex gap-1 overflow-x-auto px-3 pb-3 [mask-image:linear-gradient(to_right,transparent,black_1rem,black_calc(100%-2rem),transparent)] [scrollbar-width:none] lg:mt-0 lg:flex-1 lg:flex-col lg:overflow-y-auto lg:[mask-image:none] lg:[scrollbar-width:thin] [&::-webkit-scrollbar]:hidden"
      >
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active = href === activeHref;
          return (
            <Link
              key={href}
              href={href}
              aria-current={active ? "page" : undefined}
              className={cn(
                "relative flex shrink-0 items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                active
                  ? "bg-violet-500/12 text-violet-100"
                  : "text-muted-foreground hover:bg-sidebar-accent/60 hover:text-foreground",
              )}
            >
              {/* A filled bar down the left edge rather than a dot on the
                  right: the eye finds the start of a row before its end, and
                  on the phone strip there is no room for a trailing marker. */}
              {active && (
                <span
                  className="absolute inset-y-1.5 left-0 w-0.5 rounded-full bg-violet-400 lg:-left-1"
                  aria-hidden="true"
                />
              )}
              <Icon className={cn("size-4 shrink-0", active && "text-violet-300")} aria-hidden="true" />
              {label}
            </Link>
          );
        })}
      </nav>
      <div className="hidden p-4 lg:block">
        <Link href="/brands" className="group block rounded-xl border border-border bg-background/40 p-4 transition-colors hover:border-violet-400/30 hover:bg-background/70">
          <div className="flex items-center justify-between text-xs font-medium">Built on your business<ArrowUpRight className="size-3.5 text-violet-300 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" aria-hidden="true" /></div>
          <p className="mt-2 text-xs leading-relaxed text-muted-foreground">Better sources. Stronger proof. Copy that sounds like you.</p>
        </Link>
        <p className="px-2 pt-4 text-[10px] tracking-widest text-muted-foreground">YOUR EMAIL STUDIO</p>
      </div>
      <AccountMenu />
    </aside>
  );
}
