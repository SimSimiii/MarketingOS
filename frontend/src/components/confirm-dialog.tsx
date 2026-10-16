"use client";

import { useState, type ReactNode } from "react";
import { CircleHelp, TriangleAlert } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

/** Destructive-action confirmation.
 *
 * Replaces `window.confirm`, which blocks the main thread, cannot be styled,
 * and can be permanently suppressed by the browser after a few uses - which
 * would silently turn "Delete" into a one-click irreversible action.
 */
export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel = "Delete",
  tone = "destructive",
  pending = false,
  onConfirm,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: ReactNode;
  confirmLabel?: string;
  /** `default` for a confirmation that is a decision rather than a loss -
   * spending quota against a recommendation, say. Red there reads as danger
   * the reader is not in. */
  tone?: "destructive" | "default";
  pending?: boolean;
  onConfirm: () => void;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <span
            className={
              tone === "destructive"
                ? "mb-2 flex size-11 items-center justify-center rounded-2xl bg-red-500/10 text-red-300 ring-1 ring-red-400/25"
                : "icon-tile mb-2 flex size-11 items-center justify-center rounded-2xl"
            }
            aria-hidden="true"
          >
            {tone === "destructive" ? <TriangleAlert className="size-5" /> : <CircleHelp className="size-5" />}
          </span>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription render={<div />}>{description}</DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={pending}>
            Cancel
          </Button>
          <Button
            variant={tone === "destructive" ? "destructive" : "default"}
            onClick={onConfirm}
            disabled={pending}
            className={tone === "destructive" ? "border-red-400/40 bg-red-500/85 text-white hover:bg-red-500 hover:text-white" : undefined}
          >
            {pending ? "Working…" : confirmLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/** Small helper for the common "button opens a confirm" pairing. */
export function useConfirm() {
  const [open, setOpen] = useState(false);
  return { open, setOpen, ask: () => setOpen(true) };
}
