export default function Loading() {
  return (
    <div role="status" aria-label="Loading page" className="space-y-8">
      <span className="sr-only">Loading your workspace…</span>
      <div aria-hidden="true" className="space-y-4 motion-safe:animate-pulse">
        <div className="h-3 w-24 rounded bg-muted" />
        <div className="h-9 w-2/3 max-w-md rounded bg-muted" />
        <div className="h-4 w-4/5 max-w-lg rounded bg-muted" />
        <div className="mt-8 h-48 rounded-2xl border border-border bg-card" />
        <div className="grid gap-4 sm:grid-cols-3">{[0, 1, 2].map((item) => <div key={item} className="h-32 rounded-xl border border-border bg-card" />)}</div>
        <div className="h-64 rounded-xl border border-border bg-card" />
      </div>
    </div>
  );
}
