"use client"

import { Toaster as Sonner, type ToasterProps } from "sonner"
import { CircleCheckIcon, InfoIcon, TriangleAlertIcon, OctagonXIcon, Loader2Icon } from "lucide-react"

/**
 * Toasts in the console's own dark.
 *
 * This used to ask next-themes for the theme, but nothing provides one, so
 * the answer was always "system" - and on a machine set to light mode every
 * toast arrived as a white card on a black page. The console has one theme.
 */
const Toaster = ({ ...props }: ToasterProps) => {
  return (
    <Sonner
      theme="dark"
      className="toaster group"
      icons={{
        success: <CircleCheckIcon className="size-4 text-emerald-300" />,
        info: <InfoIcon className="size-4 text-violet-300" />,
        warning: <TriangleAlertIcon className="size-4 text-amber-300" />,
        error: <OctagonXIcon className="size-4 text-destructive" />,
        loading: <Loader2Icon className="size-4 animate-spin text-violet-300" />,
      }}
      style={
        {
          "--normal-bg": "oklch(0.2 0.022 285 / 92%)",
          "--normal-text": "var(--popover-foreground)",
          "--normal-border": "oklch(1 0 0 / 10%)",
          "--border-radius": "0.9rem",
        } as React.CSSProperties
      }
      toastOptions={{
        classNames: {
          toast:
            "cn-toast !gap-3 !px-4 !py-3.5 !shadow-[inset_0_1px_0_0_oklch(1_0_0/7%),0_24px_48px_-12px_oklch(0_0_0/70%)] backdrop-blur-xl",
          title: "!font-medium",
          description: "!text-muted-foreground",
        },
      }}
      {...props}
    />
  )
}

export { Toaster }
