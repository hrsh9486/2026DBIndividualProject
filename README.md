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
build_capex_pipeline.py                         orchestration only
  -> extractors/capex_sources.py               network acquisition or raw replay
       -> data/raw/                            immutable source landings
  -> transforms/capex_metrics.py               typed calculated metrics
       -> GovernmentMetrics / PrivateMetrics / FiscalMetrics
  -> builders/capex_artifacts.py               final artifact assembly
  -> validators/                               complete-set and schema gates
  -> exporters/json_export.py                  per-file atomic JSON publication
       -> data/processed/                      13 final CapEx JSON files
       -> frontend/public/data/                13 identical public copies
```

The full run extracts every source before transformation, builds thirteen final
payloads in memory and validates the complete set before writing the first processed or
public output. Raw source files are immutable evidence and are retained even if
a later transform fails. Publication then replaces each JSON file atomically;
there is no run-level transaction, backup tree or rollback mechanism.

The orchestration call graph is explicit. `run_pipeline()` accepts only data and
configuration values and directly calls the named extraction, build, validation,
publication and verification functions. Production behavior is not supplied as
function-valued parameters, and the Python pipeline contains no lambda-based
dispatch or callback configuration.

Three typed metric sets exist only in memory as explicit transform results:

- `scripts/transforms/capex_metrics.py::calculate_government_metrics` reconstructs Union Budget vintages
  and execution ratios;
- `scripts/transforms/capex_metrics.py::calculate_private_metrics` combines national-accounts private GFCF
  with RBI OBICUS capacity utilisation;
- `scripts/transforms/capex_metrics.py::calculate_fiscal_metrics` produces the debt, interest-burden and
  primary-balance inputs.

Each contains immutable `CanonicalRecord` values plus source provenance—never
JSON-shaped `metadata` or `series` dictionaries. They are dependencies of final
artifacts and are never read from or written to JSON. Allocation, physical-delivery and
IIP observations follow the same boundary: `sources/capex_delivery_reference.json`
is parsed by `scripts/extractors/delivery_reference.py` into typed source models,
then passed to pure builders.

CapEx-specific payload construction is handled by:

- `scripts/builders/fiscal_outputs.py` for execution and fiscal sustainability;
- `scripts/builders/market_outputs.py` for sector performance and correlations;
- `scripts/builders/real_economy_outputs.py` for allocation, delivery,
  production, private response and corporate fundamentals;
- `scripts/builders/evaluation_outputs.py` for investment quality, state
  evaluation, crowding-in evidence and the summary.

`scripts/builders/capex_artifacts.py` directly calls all thirteen named output
builders and then constructs the thirteen-key `CapexArtifacts.outputs` map. No
bulk `build_core_*` or `build_depth_*` function hides output creation.

Run the complete ETL pipeline with one command:

```bash
PYTHONPATH=scripts venv/bin/python scripts/build_capex_pipeline.py
```

The orchestrator owns extraction, transformation, complete-set validation,
processed publication and public publication. It is the only analytical
executable; there are no separate `build_*.py` or promotion entry points.

Target one registered artifact through the same ETL call graph:

```bash
PYTHONPATH=scripts venv/bin/python scripts/build_capex_pipeline.py --target output:execution
PYTHONPATH=scripts venv/bin/python scripts/build_capex_pipeline.py --offline --target output:quality
```

The only target namespace is `output:<key>`. A targeted run still extracts, transforms and
validates the complete dependency graph; `--target` limits only which validated
artifact is written and verified. The default is `--target all`.

Replay the latest immutable source landing without network access with:

```bash
PYTHONPATH=scripts venv/bin/python scripts/build_capex_pipeline.py --offline
```

Offline mode reads immutable files in `data/raw/` in place, reruns the production
parsers and follows the same transform, validation and publication path. It does
not use existing processed JSON as source input.

Schema and catalogue synchronisation remain separate because they change
frontend metadata rather than analytical payloads:

```bash
PYTHONPATH=scripts venv/bin/python scripts/sync_public_schemas.py
PYTHONPATH=scripts venv/bin/python scripts/sync_focused_catalogue.py
```

The central validation gate checks every registered artifact before replacing
any processed or public JSON. Only paths registered in
`scripts/config/capex_analysis.py` receive public copies, so unrelated legacy
outputs cannot enter the live frontend accidentally.

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

The generated documents are written to `docs/`.

## Archives

- `archive_iteration_1/` contains the original exploratory/dashboard material.
- `archive_iteration_2/` contains the superseded seven-lens research programme,
  evidence-report engine, broad frontend catalogue, old schemas, notebooks and
  their tests.

Archive files are retained for provenance and recovery but are outside the
active import, validation and deployment boundary.
