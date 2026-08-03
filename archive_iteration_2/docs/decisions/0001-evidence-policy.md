# Decision 0001: Initial statistical evidence policy

**Date:** 2026-07-28  
**Status:** Accepted initial design freeze  
**Registry version:** 1.0.0 (subsequently amended by Decision 0003)

## Decision

The first inferential evidence work will implement two fiscal-capacity analyses and one UPI adoption-trend analysis. Their specifications are frozen in `scripts/config/evidence_specs.py` before live estimation. Any material change made after inspecting results must create a new specification version and a new decision entry.

All three analyses are observational and must publish `causal: false`.

## Fiscal-capacity family

The family identifier is `fiscal_capacity_primary`, with Benjamini–Hochberg adjustment at alpha 0.05 across the two registered primary hypotheses.

The main sample admits `actual` and `revised` observations. Provisional, estimate and budget observations are excluded and counted. Fiscal periods use their explicit 31 March end dates; they are never joined to calendar years by matching year numbers.

The first model relates the change in the central-government interest-to-revenue burden to one-year-lagged general-government debt, one-year-lagged primary balance and a deterministic trend. Its focal term is `lagged_general_government_debt`, with a positive expected direction. The second relates the change in general-government debt to the lagged primary balance, lagged debt change and registered exceptional-period indicators. Its focal term is `lagged_primary_balance`, with a negative expected direction.

Both models require at least 30 complete observations, at least 20 residual degrees of freedom, OLS estimation and HAC covariance with a main maximum lag of two fiscal years.

FY2020-21 and FY2021-22 are the registered COVID exceptional period. The first model retains them in the main sample and excludes them in robustness. The second includes registered exceptional-period indicators and also excludes the period in robustness. Required robustness includes actual-only status, HAC lag one, removal of the most influential observation and a parsimonious bivariate form.

Government coverage must remain explicit: general-government debt is not a direct institutional decomposition of the central-government interest burden.

## Digital-integration family

The family identifier is `digital_integration_primary`, with Benjamini–Hochberg adjustment at alpha 0.05 for the registered focal trend terms.

The main UPI sample starts on 30 April 2017, after the initial launch phase. Zero, null and non-positive observations are excluded before logarithms and counted; no arbitrary constant is added.

The registered break date is 30 April 2020, the first full month under the initial nationwide COVID disruption. The main model distinguishes a level disruption from a post-break slope change:

```text
log(UPI transactions per capita)
    ~ trend
    + calendar-month effects
    + COVID level
    + post-COVID slope
```

The model requires at least 36 observations and at least 20 residual degrees of freedom. It uses HAC covariance with a maximum lag of 12 months.

The focal term is `annualised_underlying_trend`, with a positive expected direction. The post-COVID slope change remains an explicitly reported model term but is not allowed to replace the registered focal hypothesis after results are inspected.

March–June 2020 is the registered pandemic-disruption period. It remains in the main specification with declared break terms and is excluded in robustness. Other required robustness uses an April 2018 start, a level rather than log trend, and HAC maximum lag six.

This is an adoption trend, not an estimate of a policy effect or of UPI's effect on tax capacity or formalisation. The UPI–GST relationship remains `insufficient_data` until substantially more comparable annual GST observations exist.

For all three registered analyses, the main support rule is that every registered focal term has the expected direction and a Benjamini–Hochberg-adjusted p-value below alpha 0.05. Diagnostics and robustness can downgrade that main-model result to `mixed` or `failed_diagnostics`; the exact grading implementation must be deterministic and tested before live estimation.

## Publication policy

Evidence results use a separate `evidence_report` contract. Regression coefficients are not dated economic observations and must not be inserted into `dated_multi_series`.

An ineligible registered analysis publishes a structured `insufficient_data` result instead of disappearing. Every report preserves:

- source artifact path, contract, SHA-256 digest, generation time and coverage;
- specification and registry versions;
- sample coverage and all exclusion counts;
- estimator, covariance, alignment and formula;
- diagnostics and registered robustness;
- multiple-testing family and method;
- practical interpretation and limitation.

Descriptive results do not receive invented p-values. Insufficient results contain no inferential estimates. Non-causal results may use “associated with” but not causal language such as “causes”, “leads to” or “results in”.
