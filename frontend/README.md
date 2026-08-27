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

- `src/app/*` — one route per page (Dashboard, Campaigns, Campaign Details, Live, Brands,
  Campaign sources, Settings, Activity). Pages are server components that call the API
  directly; forms that mutate data are small colocated client components (`"use client"`).
- `src/lib/api-client.ts` — typed fetch wrapper over the backend REST API.
- `src/lib/types.ts` — TypeScript types mirroring the backend's Pydantic schemas.
- `src/components/ui/*` — shadcn/ui primitives.
- `src/components/layout/*` — sidebar + app shell.

## One workspace per brand

Knowledge and market are not top-level pages, and that is a product decision rather than a
routing one. Both belong to a *business*: two brands have different competitors, different
proof and different claims that are theirs alone, so an account-wide Market has to pick a brand
on the reader's behalf, and the one it picks is never the one they meant.

Everything scoped to a business therefore lives under `src/app/brands/[brandId]/`:

- `page.tsx` — what this brand can prove, who it is up against, what it has shipped.
- `knowledge/` — its sources, and `knowledge/base/` the compiled knowledge base built from them.
- `market/` — its competitors, positioning map, proof queue and radar.

`layout.tsx` fetches the brand once and renders the header, the brand switcher and the section
nav around all of them. `/market` and `/knowledge/base?brand=` redirect here rather than 404,
because bookmarks to the old account-wide pages exist. What is left at `/knowledge` is the one
thing that has no brand to move into: sources attached to a one-off campaign, read once and
kept to it.

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
