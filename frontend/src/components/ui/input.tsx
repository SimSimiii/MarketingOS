import * as React from "react"
import { Input as InputPrimitive } from "@base-ui/react/input"

import { cn } from "@/lib/utils"

/** Fields are set into the surface rather than raised from it: a shade darker
 * than the card, with a shadow on the inside of the top edge. Focus lights
 * the border in the accent. */
export const FIELD_STYLES =
  "w-full min-w-0 rounded-lg border border-white/10 bg-black/25 text-base shadow-[inset_0_1px_2px_0_oklch(0_0_0/30%)] transition-[border-color,box-shadow,background-color] duration-150 outline-none placeholder:text-muted-foreground/70 hover:border-white/[0.16] focus-visible:border-violet-400/60 focus-visible:bg-black/30 focus-visible:ring-3 focus-visible:ring-violet-500/20 disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50 aria-invalid:border-destructive/60 aria-invalid:ring-3 aria-invalid:ring-destructive/20 md:text-sm"

function Input({ className, type, ...props }: React.ComponentProps<"input">) {
  return (
    <InputPrimitive
      type={type}
      data-slot="input"
      className={cn(
        FIELD_STYLES,
        "h-9 px-3 py-1 file:inline-flex file:h-6 file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground [&::-webkit-search-cancel-button]:cursor-pointer",
        className
      )}
      {...props}
    />
  )
}

export { Input }
