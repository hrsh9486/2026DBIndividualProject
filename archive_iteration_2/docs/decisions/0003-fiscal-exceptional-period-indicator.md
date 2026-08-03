# Decision 0003: Combine the fiscal exceptional-period indicator

**Date:** 2026-07-28  
**Status:** Accepted corrective specification change  
**Registry version:** 1.1.0  
**Analysis version changed:** `primary-balance-debt-change` 1.0.0 → 1.1.0

## Trigger

The first live estimation attempt stopped before producing or publishing a
report. The version 1.0.0 debt-change design used separate indicators for the
fiscal years ending March 2021 and March 2022. Each indicator isolated exactly
one observation, giving both observations leverage of one and making Cook’s
distance undefined.

This is a structural diagnostic failure rather than an empirical coefficient
finding. The failed candidate was not written to either processed or frontend
data.

## Change

Replace the two singleton indicators with one `covid_fy2020_22` indicator equal
to one for both registered COVID fiscal years and zero otherwise. The main
design becomes:

```text
debt_change
    ~ intercept
    + lagged_primary_balance
    + lagged_debt_change
    + covid_fy2020_22
```

The fitted parameter count changes from five to four. The exceptional-period
dates, focal term, expected direction, HAC rule, minimum sample, diagnostics,
robustness checks and multiple-testing family are unchanged.

## Rationale

The combined indicator represents the pre-registered two-year disruption while
avoiding saturated one-observation cells. A version increment is required
because the design matrix changed after a live estimation attempt, even though
no coefficient was reviewed and no result was published.
