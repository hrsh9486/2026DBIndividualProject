# India public CapEx transmission

This repository now contains one deployable research product: an evidence-led
analysis of whether India's public capital-expenditure push translated into
executed projects, market and corporate response, private investment and real
productive capacity strongly enough to justify its fiscal cost.

The former broad India-indicators programme is preserved under
`archive_iteration_2/`. It is not imported, published or exercised by the
active build.

## Research stages

The frontend follows a single transmission chain:

1. public CapEx intensity, execution, sector allocation and physical delivery;
2. project timing and cost quality;
3. CapEx-sensitive market performance, lag correlations and a corporate case
   study;
4. private GFCF, capacity utilisation, capital-goods production, a distributed
   lag evidence ladder and a state fixed-effects evaluation;
5. debt and interest burden, followed by a five-year conditional scenario lab.

The analysis is descriptive or associational unless explicitly labelled
otherwise. The scenario lab is a parameterised stress test, not an estimated
forecast or causal multiplier.

## Active pipeline

```text
official sources / frozen raw inputs
  -> provider-specific extractors
  -> canonical records
  -> deterministic CapEx and upstream transforms
  -> schema-valid processed JSON
  -> validated atomic promotion
  -> static React frontend
```

The three retained structural upstream builders are required by the CapEx
story:

- `scripts/build_government_investment.py` reconstructs Union Budget vintages
  and execution ratios;
- `scripts/build_private_investment.py` combines national-accounts private GFCF
  with RBI OBICUS capacity utilisation;
- `scripts/build_fiscal_capacity.py` produces the debt, interest-burden and
  primary-balance inputs.

CapEx-specific construction is handled by:

- `scripts/build_capex_analysis.py` for execution, markets, correlations,
  private response, fiscal bridge, summary and corporate fundamentals;
- `scripts/build_capex_delivery.py` for sector allocation, physical delivery
  and capital-goods production;
- `scripts/build_capex_depth.py` for investment quality, the state evaluation
  and the registered crowding-in lag grid.

Refresh the upstream inputs first when their sources change, then build and
publish the CapEx product:

```bash
python3 scripts/build_government_investment.py
python3 scripts/build_private_investment.py
python3 scripts/build_fiscal_capacity.py
python3 scripts/build_capex_analysis.py
python3 scripts/build_capex_delivery.py
python3 scripts/build_capex_depth.py
python3 scripts/promote_processed_data.py
python3 scripts/sync_public_schemas.py
python3 scripts/sync_focused_catalogue.py
```

Each builder validates before replacing a processed artifact. Promotion accepts
only paths registered in `scripts/config/capex_analysis.py`; unrelated legacy
outputs cannot be copied into the live frontend accidentally.

## Data contracts and publication

Active browser data lives only under `frontend/public/data/capex-analysis/`.
The catalogue contains one `capex-transmission` section and uses two chart-data
contracts:

```text
catalogue.json
  -> dated_multi_series -> time-series and CapEx-specific analytical views
  -> market_performance -> sector performance views
```

`capex_analysis_summary.schema.json` separately validates the verdict summary
loaded by the CapEx page. JSON Schema validation runs both during Python
publication and in the frontend build. Runtime guards repeat the schema
discriminator check before React renders an asset.

The browser has no application API. It loads static JSON through TanStack Query
and renders it with React, TypeScript, React Router and Recharts.

## Verification

Backend:

```bash
PYTHONPATH=scripts venv/bin/python -m unittest discover -s tests -v
```

Frontend:

```bash
cd frontend
npm run validate:data
npx tsc --noEmit
npm run lint
npm run build
```

Generate the two maintained CapEx guides with:

```bash
PYTHONPATH=scripts venv/bin/python scripts/generate_capex_documentation.py
```

The generated documents are written to `docs/capex/`.

## Archives

- `archive_iteration_1/` contains the original exploratory/dashboard material.
- `archive_iteration_2/` contains the superseded seven-lens research programme,
  evidence-report engine, broad frontend catalogue, old schemas, notebooks and
  their tests.

Archive files are retained for provenance and recovery but are outside the
active import, validation and deployment boundary.
