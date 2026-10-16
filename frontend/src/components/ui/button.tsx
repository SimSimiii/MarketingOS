import { Button as ButtonPrimitive } from "@base-ui/react/button"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "group/button relative inline-flex shrink-0 cursor-pointer items-center justify-center rounded-lg border border-transparent bg-clip-padding text-sm font-medium whitespace-nowrap transition-[background-color,border-color,color,box-shadow,transform,opacity] duration-200 outline-none select-none focus-visible:ring-3 focus-visible:ring-ring/45 active:not-aria-[haspopup]:translate-y-px disabled:pointer-events-none disabled:opacity-45 aria-invalid:border-destructive aria-invalid:ring-3 aria-invalid:ring-destructive/20 dark:aria-invalid:border-destructive/50 dark:aria-invalid:ring-destructive/40 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
  {
    variants: {
      variant: {
        // Lit from above: a gradient, a highlight on the top edge and a glow
        // the colour of the accent. The one control on a page that should be
        // found without looking for it.
        default:
          "bg-[linear-gradient(180deg,oklch(0.68_0.21_293),oklch(0.56_0.23_289))] text-primary-foreground shadow-[inset_0_1px_0_0_oklch(1_0_0/28%),inset_0_-1px_0_0_oklch(0_0_0/18%),0_0_0_1px_oklch(0.5_0.2_290/85%),0_6px_20px_-6px_oklch(0.6_0.24_293/70%)] hover:bg-[linear-gradient(180deg,oklch(0.72_0.2_293),oklch(0.6_0.23_289))] hover:shadow-[inset_0_1px_0_0_oklch(1_0_0/32%),inset_0_-1px_0_0_oklch(0_0_0/18%),0_0_0_1px_oklch(0.55_0.2_290/90%),0_10px_28px_-6px_oklch(0.62_0.24_293/80%)]",
        outline:
          "border-white/10 bg-white/[0.035] text-foreground shadow-[inset_0_1px_0_0_oklch(1_0_0/4%)] hover:border-white/[0.16] hover:bg-white/[0.07] aria-expanded:border-white/[0.16] aria-expanded:bg-white/[0.07]",
        secondary:
          "border-white/[0.06] bg-white/[0.08] text-secondary-foreground shadow-[inset_0_1px_0_0_oklch(1_0_0/6%)] hover:bg-white/[0.12] aria-expanded:bg-white/[0.12]",
        ghost:
          "text-muted-foreground hover:bg-white/[0.06] hover:text-foreground aria-expanded:bg-white/[0.06] aria-expanded:text-foreground",
        destructive:
          "border-destructive/25 bg-destructive/10 text-destructive hover:border-destructive/40 hover:bg-destructive/20 focus-visible:ring-destructive/30",
        link: "text-violet-300 underline-offset-4 hover:text-violet-200 hover:underline",
      },
      size: {
        default:
          "h-9 gap-2 px-3.5 has-data-[icon=inline-end]:pr-3 has-data-[icon=inline-start]:pl-3",
        xs: "h-6 gap-1 rounded-md px-2 text-xs in-data-[slot=button-group]:rounded-lg has-data-[icon=inline-end]:pr-1.5 has-data-[icon=inline-start]:pl-1.5 [&_svg:not([class*='size-'])]:size-3",
        sm: "h-8 gap-1.5 rounded-[0.6rem] px-3 text-[0.8125rem] in-data-[slot=button-group]:rounded-lg has-data-[icon=inline-end]:pr-2.5 has-data-[icon=inline-start]:pl-2.5 [&_svg:not([class*='size-'])]:size-3.5",
        lg: "h-10 gap-2 px-4 has-data-[icon=inline-end]:pr-3.5 has-data-[icon=inline-start]:pl-3.5",
        icon: "size-9",
        "icon-xs":
          "size-6 rounded-md in-data-[slot=button-group]:rounded-lg [&_svg:not([class*='size-'])]:size-3",
        "icon-sm":
          "size-8 rounded-[0.6rem] in-data-[slot=button-group]:rounded-lg",
        "icon-lg": "size-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

function Button({
  className,
  variant = "default",
  size = "default",
  ...props
}: ButtonPrimitive.Props & VariantProps<typeof buttonVariants>) {
  return (
    <ButtonPrimitive
      data-slot="button"
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}

export { Button, buttonVariants }
