# MarketingOS Frontend

Next.js 16 (App Router) + TypeScript + Tailwind + shadcn/ui dashboard for the MarketingOS API.

## Setup

```bash
npm install
cp .env.local.example .env.local
npm run dev
```

Runs on http://localhost:3000. Browser requests use `/api` on that origin; the development
server proxies them to `API_PROXY_TARGET` (default `http://localhost:8000`). Keep
`NEXT_PUBLIC_API_URL=/api` for cookie authentication. If accounts are enabled, set
`NEXT_PUBLIC_AUTH_REQUIRED=true` to match the backend. The static production export needs
an HTTPS reverse proxy routing `/api/*` to the backend on the console's domain.

## Structure

- `src/app/*` — one route per page (Dashboard, Campaigns, Campaign Details, Live, Brands,
  Campaign sources, Settings, Activity). The production site is a static export. Client
  loaders use `usePageData` and `PageData` for loading, errors and navigation;
  `refreshPage()` reloads mounted loaders after mutations.
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

The brand layout loads the brand and renders the header, the brand switcher and the section
nav around all of them. `/market` and `/knowledge/base?brand=` redirect here rather than 404,
because bookmarks to the old account-wide pages exist. What is left at `/knowledge` is the one
thing that has no brand to move into: sources attached to a one-off campaign, read once and
kept to it.

## Watching a run

The execution page uses persisted snapshots and a manual Refresh action. Its three pieces are:

- `hooks/use-execution-stream.ts` — loads the persisted timeline over HTTP and exposes
  refresh, error and last-updated state. It opens no SSE connection and does not poll.
- `lib/run-timeline.ts` — a pure fold of the persisted event list into steps.
- `components/run-timeline.tsx` — one row per director step, each opening onto that agent's own
  log lines. A specialist that gets reworked appears as several steps rather than one collapsed
  card, because the rework loop is the product, not an implementation detail.

Theme is dark-only with a violet accent (see `globals.css`); there is no light/dark toggle.

After an API schema change, run `backend/scripts/export_api_types.py`, then lint, typecheck,
tests and build. The backend generator's `--check` also runs in CI.
