# 2026DBIndividualProject
Analysis of India's position as a emerging global financial leader

## Data pipeline

The pipeline follows the source-boundary architecture documented in
`docs/planning/`:

```text
config/indicators.py      indicator definitions and output contracts
extractors/               provider-specific network and raw landing logic
models/                   canonical provider-neutral records
transforms/               deterministic reusable calculations
builders/                 contract-specific payload assembly
validators/               quality gates and Draft 2020-12 JSON Schema checks
exporters/                validated atomic publication
data/raw/<source>/        immutable retrieved payloads
data/processed/<bucket>/  schema-valid frontend artifacts
```

Run a subset of the World Bank registry with:

```bash
python3 scripts/build_world_bank_series.py labour_force_participation working_age_share_pct
```

Build, quality-check and promote all seven focused India research lenses with:

```bash
python3 scripts/build_focused_pipeline.py --frontend-build
```

Individual lens keys can be supplied for targeted refreshes. For example:

```bash
python3 scripts/build_focused_pipeline.py human_capital capital_resilience
```

The focused jobs retain immutable dated source snapshots, map provider data to
canonical records, validate semantic quality constraints, publish processed JSON
atomically, promote only schema-valid artifacts, and regenerate the frontend
catalogue. Government investment runs before private investment because the
private lens uses the validated public-CapEx series as a lagged comparator.

Some official sources expose only partial histories. The catalogue reports these
honestly: GST is not yet included in the digital bundle, RBI OBICUS is not yet
included in the private-investment bundle, and NSE's current-day FII/DII endpoint
is accumulated prospectively before rolling 12-month measures are enabled.

Build the market-performance bundle with:

```bash
python3 scripts/build_yfinance_markets.py
```

Build the focused India public-CapEx transmission project with:

```bash
python3 scripts/build_capex_analysis.py
python3 scripts/promote_processed_data.py \
  capex-analysis/capex-execution.json \
  capex-analysis/sector-performance.json \
  capex-analysis/capex-sector-correlations.json \
  capex-analysis/private-investment-response.json \
  capex-analysis/fiscal-sustainability.json \
  capex-analysis/analysis-summary.json \
  capex-analysis/corporate-fundamentals.json
python3 scripts/sync_focused_catalogue.py
```

This job uses official Nifty total-return-index histories, the validated Union
Budget/MoSPI CapEx artifact, RBI OBICUS capacity utilisation, national-accounts
private GFCF, and RBI fiscal tables. It publishes the five chart contracts and
a rule-generated hypothesis summary and frozen ten-company corporate case study
under `data/processed/capex-analysis/`. The market bundle includes Nifty FMCG
as a control and publishes target-sector performance relative to both Nifty 50
and Nifty FMCG.
The 0-, 6- and 12-month market tests include a pandemic-year exclusion
sensitivity. The project labels nominal CapEx growth explicitly; real growth is
withheld until a consistent investment deflator is registered.

Promote validated processed artifacts into the frontend without deleting any
existing files:

```bash
python3 scripts/promote_processed_data.py
# or promote one artifact
python3 scripts/promote_processed_data.py currency/real_effective_exchange_rate.json
```

Each job validates before replacing a processed artifact. A failed source,
quality gate, or schema check leaves the last valid JSON untouched.




# Frontend

The current frontend is a TypeScript React application in `frontend/`.
`frontend_legacy/` is retained for reference but is not used by the build.

The browser has no application API. It loads `public/data/catalogue.json`,
resolves an indicator view to a static artifact, runtime-checks its schema
discriminator, and sends it through one of three schema-specific adapters.

```text
catalogue.json
  -> annual_country_series -> country comparison
  -> dated_multi_series    -> multi-series chart
  -> market_performance    -> market chart and summaries
```

Run locally:

```bash
cd frontend
npm install
npm run dev
```

Verify a production build:

```bash
npm run validate:data
npx tsc --noEmit
npm run lint
npm run build
```

`npm run build` validates the catalogue against its manifest schema, checks
every view-to-asset reference and adapter pairing, validates all published
artifacts against their declared Draft 2020-12 schemas, checks duplicate
periods and metadata coverage, and only then runs Vite.

To publish newly processed artifacts to their stable frontend paths:

```bash
python3 scripts/promote_processed_data.py
```

The frontend stack is React 19, TypeScript, Vite, TanStack Query, React Router,
Recharts and AJV. Presentation and percentage scaling are controlled by the
catalogue rather than inferred in React components.
