# Iteration 2 archive

Archived on 3 August 2026 when the repository was narrowed from the broad
India-indicators programme to the public-CapEx transmission product.

The archive is stored at `archive_iteration_2/`, following the repository's
`archive_iteration_<n>` naming convention. At archival time it contained 250
files (about 28 MB).

## Scope

This archive preserves the superseded iteration-2 material:

- digital integration, external competitiveness, human capital and domestic
  capital-resilience lens builders;
- the generic World Bank, broad-market and formal evidence-report pipeline;
- non-CapEx frontend catalogue assets, dashboard/evidence UI and schemas;
- broad-programme planning, architecture and weekly-update documents;
- superseded Python/frontend dependency declarations;
- exploratory notebooks and early frontend contract drafts;
- tests that only exercised the archived programme.

Paths below this directory mirror their former repository locations wherever
practical. Files were moved rather than deleted, so they can be restored by
moving them back to the recorded path.

## Inventory by subtree

| Subtree | Files | Contents |
| --- | ---: | --- |
| `data/` | 116 | Raw and processed non-CapEx evidence, including obsolete RBI table snapshots |
| `frontend/` | 40 | Old public assets/contracts and dashboard/evidence UI |
| `scripts/` | 48 | Superseded builders, evidence engine, extractors, transforms and original shared registrations |
| `docs/` | 14 | Architecture, planning, decisions, review and weekly updates |
| `tests/` | 11 | Tests specific to the archived programme |
| `notebooks/` and checkpoints | 10 | Exploration notebooks and generated notebook artifacts |
| `schemas/` | 4 | Annual-country, event-study, evidence-report and old series contracts |
| `requirements/` | 2 | Dependency lists before the CapEx-only reduction |
| root contract drafts | 3 | Early manifest/type drafts |

## Deliberately retained in the active repository

The CapEx product still depends on three structural upstream pipelines, so the
following remain active:

- `scripts/build_government_investment.py` and its Union Budget/RBI transform;
- `scripts/build_private_investment.py` and its national-accounts/OBICUS
  transform;
- `scripts/build_fiscal_capacity.py` and its RBI fiscal transform;
- shared canonical records, dated-series builders, validators and atomic JSON
  exporters;
- CapEx-specific extraction, transformation, promotion, catalogue, frontend,
  tests and documentation.

## Active product after archival

The deployable frontend now contains only the `capex-transmission` section and
the assets under `frontend/public/data/capex-analysis/`. The root route opens
that research lens directly. Processed upstream inputs remain under `data/`
because they are part of the current CapEx rebuild chain, not legacy outputs.

## Restore procedure

1. Review the desired archived subtree and the current destination first.
2. Move only the required files back to their original paths.
3. Restore the corresponding catalogue/schema/type registrations.
4. Run the Python tests and `npm run build` before publishing.

Do not copy the entire archive over the active tree: several active files were
intentionally simplified after the move and would otherwise be overwritten.
