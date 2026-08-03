# Decision 0002: Evidence estimation, diagnostics and grading

**Date:** 2026-07-28  
**Status:** Accepted implementation freeze before live estimation  
**Applies to registry:** 1.0.0, except where superseded by Decision 0003

## Estimation and uncertainty

The version 1.0.0 models are estimated with `statsmodels` ordinary least
squares. Main-model covariance uses the registered Newey–West HAC maximum lag,
the Bartlett kernel, the finite-sample covariance correction, and Student-t
inference with residual degrees of freedom. Reported intervals are two-sided
95% confidence intervals.

The two fiscal models use these exact design matrices:

- interest-burden change: intercept, lagged general-government debt, lagged
  primary balance and a zero-based linear trend;
- debt change: intercept, lagged primary balance, lagged debt change and
  separate indicators for the fiscal years ending March 2021 and March 2022.

The UPI model uses log transactions per capita as its dependent variable and:
an intercept, a zero-based calendar-month trend, February–December indicators
with January as the reference month, a level indicator beginning April 2020,
and a post-April-2020 calendar-month slope. The focal monthly log-trend
coefficient is converted to an annual percentage rate as
`100 × (exp(12 × beta) − 1)`. Its confidence interval is transformed through
the same monotonic formula; its standard error uses the delta method.

Benjamini–Hochberg adjustment is applied only to registered focal terms within
the declared family. Control-term p-values are reported without an adjusted
p-value.

## Diagnostics

Diagnostics are evaluated on the main OLS fit before robust covariance changes
its coefficient uncertainty.

- `residual_degrees_of_freedom`: pass at the registered minimum.
- `condition_number`: standardise every non-constant design column and pass at
  a matrix condition number no greater than 30.
- `residual_autocorrelation`: Breusch–Godfrey LM test at the registered HAC lag;
  pass when its p-value is at least 0.01. HAC remains the uncertainty estimator
  even when this diagnostic passes.
- `stationarity`: augmented Dickey–Fuller test of residuals with no deterministic
  term and AIC lag selection; pass when its p-value is below 0.10.
- `influential_observation`: pass when maximum Cook’s distance is no greater
  than 1.0. The lower `4/n` screening value is reported in the interpretation
  but is not a hard failure threshold.
- `stability` for UPI: refit the registered model after separately dropping the
  first and last 12 observations; pass when both focal coefficients retain the
  registered positive direction.

Any failed registered main diagnostic produces `failed_diagnostics`, regardless
of the focal p-value. Diagnostic exceptions are represented as failed checks,
not silently omitted.

## Registered robustness

Fiscal robustness uses, in registry order:

1. omit fiscal years ending March 2021 and March 2022;
2. retain only rows for which every input has `actual` status;
3. use HAC maximum lag one;
4. omit the observation with the largest main-model Cook’s distance;
5. fit an intercept plus the registered focal regressor only.

UPI robustness uses, in registry order:

1. begin the sample in April 2018;
2. omit March–June 2020;
3. fit the same design to the unlogged transactions-per-capita level, reporting
   twelve times the monthly focal coefficient;
4. use HAC maximum lag six.

A robustness fit is `supported` when its unadjusted focal p-value is below 0.05
and its coefficient has the registered direction; otherwise it is
`not_supported`. An unestimable robustness fit is `insufficient_data`.

## Main status and grade

The main support rule remains the registry rule: every adjusted focal p-value
is below 0.05 and has the expected direction.

- A failed main diagnostic yields `failed_diagnostics`, grade `limited`.
- If the main rule passes, every estimable robustness estimate has the expected
  direction, and at least half of the registered robustness fits are supported,
  status is `supported`.
- If the main rule passes but that robustness rule does not, status is `mixed`.
- If the main rule fails but any robustness fit is supported, status is `mixed`.
- Otherwise status is `not_supported`.
- `supported` receives grade `strong` only when every registered robustness fit
  is supported; otherwise it receives `moderate`.
- `mixed`, `not_supported`, and `failed_diagnostics` receive grade `limited`.
- A failed eligibility gate remains `insufficient_data`, grade `not_assessed`,
  and is never estimated.

These grades describe robustness under the registered observational design.
They do not upgrade an associational model to causal evidence.
