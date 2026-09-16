"use client";

import { useId, useState } from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

/** Keep the complete source text available without letting it dominate a card. */
export function ExpandableText({ text, className, limit = 240 }: { text: string; className?: string; limit?: number }) {
  const [expanded, setExpanded] = useState(false);
  const id = useId();
  const long = text.length > limit;
  const excerpt = text.slice(0, limit).replace(/\s+\S*$/, "");
  return (
    <div className={cn("min-w-0 text-sm leading-relaxed", className)}>
      <p id={id} className="whitespace-pre-line [overflow-wrap:anywhere]">{long && !expanded ? `${excerpt}…` : text}</p>
      {long && <button type="button" aria-expanded={expanded} aria-controls={id} onClick={() => setExpanded(!expanded)} className="mt-2 inline-flex min-h-9 items-center gap-1.5 rounded-md px-1 text-xs font-medium text-violet-300 hover:text-violet-200 focus-visible:outline-2 focus-visible:outline-ring">
        {expanded ? "Show less" : "Read full text"}<ChevronDown className={cn("size-3.5 transition-transform", expanded && "rotate-180")} />
      </button>}
    </div>
  );
}
