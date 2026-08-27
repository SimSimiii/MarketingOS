"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

/** The sections of one brand's workspace.
 *
 * Rendered as links rather than as tab panels because each section is its own
 * route: the market of a brand is a place you can send somebody, bookmark, and
 * come back to - which is the whole point of scoping it to a brand instead of
 * hanging it off a global page that quietly picks the first one. */
export function BrandNav({
  brandId,
  counts,
}: {
  brandId: string;
  counts: { sources: number; facts: number | null; rivals: number; alerts: number };
}) {
  const pathname = usePathname();
  const base = `/brands/${brandId}`;

  const items = [
    { href: base, label: "Overview", badge: null as number | null, exact: true },
    { href: `${base}/knowledge`, label: "Sources", badge: counts.sources || null },
    { href: `${base}/knowledge/base`, label: "Knowledge base", badge: counts.facts },
    { href: `${base}/market`, label: "Market", badge: counts.rivals || null },
  ];

  // Longest prefix wins, so "/knowledge/base" does not also light up
  // "/knowledge" and leave the reader unsure which page they are on.
  const active = items
    .filter((item) => (item.exact ? pathname === item.href : pathname.startsWith(item.href)))
    .sort((a, b) => b.href.length - a.href.length)[0]?.href;

  return (
    <nav className="flex flex-wrap gap-1 border-b border-border">
      {items.map((item) => (
        <Link
          key={item.href}
          href={item.href}
          className={cn(
            "-mb-px flex items-center gap-1.5 border-b-2 px-3 py-2 text-sm font-medium transition-colors",
            item.href === active
              ? "border-primary text-foreground"
              : "border-transparent text-muted-foreground hover:text-foreground",
          )}
        >
          {item.label}
          {item.badge !== null && item.badge > 0 && (
            <Badge variant="ghost" className="font-normal">
              {item.badge}
            </Badge>
          )}
          {item.href === `${base}/market` && counts.alerts > 0 && (
            <Badge variant="default" className="font-normal">
              {counts.alerts} new
            </Badge>
          )}
        </Link>
      ))}
    </nav>
  );
}
