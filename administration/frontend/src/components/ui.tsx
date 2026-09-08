"use client";

/**
 * The console's whole component vocabulary, in one file.
 *
 * Deliberately not a component library. This is six primitives used by five
 * pages; a dependency for it would be more code to audit on a surface that can
 * suspend a paying customer, and none of it would be shared with the product's
 * own design system anyway.
 */

import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode } from "react";

export function cn(...parts: (string | false | null | undefined)[]): string {
  return parts.filter(Boolean).join(" ");
}

export function Card({
  title,
  action,
  children,
  className,
}: {
  title?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section
      className={cn("rounded-xl border border-line bg-surface", className)}
    >
      {(title || action) && (
        <header className="flex items-center justify-between gap-4 border-b border-line px-5 py-4">
          <h2 className="text-sm font-semibold tracking-tight">{title}</h2>
          {action}
        </header>
      )}
      <div className="p-5">{children}</div>
    </section>
  );
}

export function Stat({
  label,
  value,
  hint,
}: {
  label: string;
  value: ReactNode;
  hint?: string;
}) {
  return (
    <div className="rounded-xl border border-line bg-surface px-5 py-4">
      <p className="text-[11px] font-medium uppercase tracking-widest text-muted">{label}</p>
      <p className="mt-2 text-2xl font-semibold tabular-nums tracking-tight">{value}</p>
      {hint && <p className="mt-1 text-xs text-muted">{hint}</p>}
    </div>
  );
}

type Tone = "neutral" | "violet" | "ok" | "warn" | "danger";

const TONES: Record<Tone, string> = {
  neutral: "border-line bg-white/5 text-muted",
  violet: "border-violet/35 bg-violet/15 text-violet-soft",
  ok: "border-ok/30 bg-ok/10 text-ok",
  warn: "border-warn/30 bg-warn/10 text-warn",
  danger: "border-danger/35 bg-danger/12 text-danger",
};

export function Badge({ tone = "neutral", children }: { tone?: Tone; children: ReactNode }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium",
        TONES[tone],
      )}
    >
      {children}
    </span>
  );
}

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "ghost" | "danger";
};

export function Button({ variant = "ghost", className, ...props }: ButtonProps) {
  const styles = {
    primary: "bg-violet text-white hover:bg-violet/85 border-transparent",
    ghost: "border-line bg-white/5 hover:border-violet/45",
    danger: "border-danger/40 bg-danger/10 text-danger hover:bg-danger/20",
  }[variant];
  return (
    <button
      {...props}
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-lg border px-3 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50",
        styles,
        className,
      )}
    />
  );
}

export function Field({
  label,
  hint,
  className,
  ...props
}: InputHTMLAttributes<HTMLInputElement> & { label: string; hint?: string }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-medium text-muted">{label}</span>
      <input
        {...props}
        className={cn(
          "w-full rounded-lg border border-line bg-bg px-3 py-2 text-sm placeholder:text-muted/60",
          className,
        )}
      />
      {hint && <span className="mt-1 block text-xs text-muted">{hint}</span>}
    </label>
  );
}

export function Select({
  label,
  children,
  value,
  onChange,
}: {
  label: string;
  children: ReactNode;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-medium text-muted">{label}</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded-lg border border-line bg-bg px-3 py-2 text-sm"
      >
        {children}
      </select>
    </label>
  );
}

/** A message worth reading. `tone="danger"` for anything that failed - a
 *  silent failure on a console that changes accounts is the worst outcome. */
export function Notice({ tone = "danger", children }: { tone?: Tone; children: ReactNode }) {
  if (!children) return null;
  return (
    <p className={cn("rounded-lg border px-3 py-2 text-sm", TONES[tone])} role="status">
      {children}
    </p>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <p className="py-8 text-center text-sm text-muted">{children}</p>;
}
