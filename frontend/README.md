# MarketingOS Frontend

Next.js 15 (App Router) + TypeScript + Tailwind + shadcn/ui dashboard for the MarketingOS API.

## Setup

```bash
npm install
cp .env.local.example .env.local   # point NEXT_PUBLIC_API_URL at the backend
npm run dev
```

Runs on http://localhost:3000, expects the backend at http://localhost:8000/api by default.

## Structure

- `src/app/*` — one route per page (Dashboard, Campaigns, Campaign Details, Live, Knowledge,
  Settings, Activity). Pages are server components that call the API directly; forms that
  mutate data are small colocated client components (`"use client"`).
- `src/lib/api-client.ts` — typed fetch wrapper over the backend REST API.
- `src/lib/types.ts` — TypeScript types mirroring the backend's Pydantic schemas.
- `src/components/ui/*` — shadcn/ui primitives.
- `src/components/layout/*` — sidebar + app shell.

## Watching a run

The execution page is the one genuinely live surface, and it is built out of three pieces that
stay deliberately separate:

- `hooks/use-execution-stream.ts` — loads the run's history over HTTP first, then opens the SSE
  stream from the position it ended at. A page opened late, or simply reloaded mid-run, shows
  the whole story rather than starting blank; the browser's own reconnection carries
  `Last-Event-ID`, so a dropped connection costs nothing either.
- `lib/run-timeline.ts` — a pure fold of the event list into steps. Replayed history and live
  events go through the same function, which is what makes the handover seamless.
- `components/run-timeline.tsx` — one row per director step, each opening onto that agent's own
  log lines. A specialist that gets reworked appears as several steps rather than one collapsed
  card, because the rework loop is the product, not an implementation detail.

Theme is dark-only with a violet accent (see `globals.css`); there is no light/dark toggle.
