import * as React from "react"

import { FIELD_STYLES } from "@/components/ui/input"
import { cn } from "@/lib/utils"

function Textarea({ className, ...props }: React.ComponentProps<"textarea">) {
  return (
    <textarea
      data-slot="textarea"
      className={cn(
        FIELD_STYLES,
        "flex field-sizing-content min-h-20 px-3 py-2.5 leading-relaxed",
        className
      )}
      {...props}
    />
  )
}

export { Textarea }
