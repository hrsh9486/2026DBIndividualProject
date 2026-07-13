# 2026DBIndividualProject
Analysis of India's position as a emerging global financial leader




# Frontend

React + Vite + Tailwind v4 + Recharts frontend for the India economic
research project. Scaffolded for all 7 analytical buckets; **Currency**
is wired up end-to-end as the working example.

## Run it

```bash
npm install
npm run dev
```

Open http://localhost:5173.

## How data flows in

Each script writes JSON into `public/data/<section>/<file>.json`. The
frontend fetches those as static files client-side — no backend.

```
public/data/
  currency/
    rebased_performance.json
    volatility_summary.json
    correlation_summary.json
    cross_decomposition.json
    event_windows.json
```

`raw_fx_data.json` isn't consumed by any component yet (too granular for
a chart) — copy it in too if you want to build something against it later.

The sample JSON in this repo matches the shape your
`inr_currency_analysis.py` script produces, so you can just point the
script's output path at `public/data/currency/` and the charts will pick
up real numbers instead of the samples.

`src/lib/dataLoader.js` has two hooks:
- `useJson(section, file)` — fetch one file, get `{ data, loading, error }`
- `useJsonBundle(section, [files])` — fetch several in parallel

Both handle loading/error states so every panel shows a skeleton or a
clear error instead of crashing on missing/malformed JSON.

## Adding a new bucket

1. Add real data under `public/data/<section-id>/`.
2. Build components in `src/sections/<section-id>/` (copy the `currency/`
   folder as a starting point — same panel/chart/table patterns).
3. In `src/App.jsx`, extend the `status === "live"` check to route your
   new section's dashboard component instead of `PendingSection`.
4. Flip `status: "pending"` → `"live"` in `src/lib/sections.js` — this
   also updates the sidebar's status dot automatically.

All 7 buckets, their IDs, and blurbs live in one place:
`src/lib/sections.js`. That's the single source of truth for the sidebar
nav and routing.

## Design notes

- Dark, data-dense "terminal" aesthetic — IBM Plex Sans for UI text,
  IBM Plex Mono for anything numeric (tickers, tables, axes).
- Palette: deep ink background, marigold as the primary accent (used
  sparingly — headline series, active nav state), teal for
  secondary/positive, muted brick for negative/alerts.
- The top ticker strip is real for USD/INR (computed from the rebased
  series) and explicitly labeled "pending" for buckets without data yet,
  rather than faking numbers.
- Sidebar bucket numbering (01–07) is a real fixed taxonomy, not
  decoration — it mirrors the 7-bucket framework from the project scope.

## Stack

- Vite + React 19
- Tailwind CSS v4 (CSS-first config via `@theme` in `src/index.css` —
  no `tailwind.config.js` needed)
- Recharts for line/bar charts
- React Router for section navigation