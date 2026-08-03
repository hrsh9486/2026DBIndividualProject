# Decision 0004: Drop the zero exceptional-period column in exclusion robustness

**Date:** 2026-07-28  
**Status:** Accepted corrective robustness clarification  
**Registry version:** 1.2.0  
**Analysis version changed:** `primary-balance-debt-change` 1.1.0 → 1.2.0

## Trigger

After Decision 0003, the main model and report validation completed in memory.
The registered `exclude_covid_fiscal_years` robustness correctly removed both
rows for which `covid_fy2020_22` equals one, but it retained the now-all-zero
indicator column. The safety layer rejected that robustness design as exactly
rank deficient.

No report had yet been written or promoted.

## Change

For `exclude_covid_fiscal_years` only, remove both registered COVID rows and
omit the `covid_fy2020_22` column. Retain the intercept, lagged primary balance,
lagged debt change, HAC maximum lag two and every other registered rule.

## Rationale

An indicator for a period absent from a subsample contains no information and
is not an estimable parameter. Omitting its identically zero column implements
the intended exclusion robustness; treating the predictable zero column as
insufficient data would misdescribe a design-construction issue as a coverage
problem.

Main-model coefficients, focal direction, diagnostics, grading thresholds and
all other robustness specifications remain unchanged.
