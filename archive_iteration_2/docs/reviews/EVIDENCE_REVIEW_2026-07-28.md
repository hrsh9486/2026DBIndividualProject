# Evidence implementation and analytical consistency review

**Review date:** 2026-07-28  
**Specification registry:** 1.2.0  
**Reports reviewed:** fiscal capacity and digital integration  
**Disposition:** Technically reproducible and suitable for qualified display

## Review scope

This review used `scripts/review_evidence_reports.py`, a numerical code path
separate from the production estimator module. It reconstructed each main
design from the registered aligned sample and independently checked:

- OLS coefficients and Newey–West HAC inference;
- transformed focal estimates and 95% intervals;
- Benjamini–Hochberg-adjusted focal p-values;
- registered diagnostic values and pass/fail flags;
- robustness status rules;
- final evidence status and grade.

All comparisons passed at a numerical tolerance of `1e-9`. The promoted
frontend reports are byte-identical to the validated processed reports.

This is an internal reproducibility and interpretation review, not external
human peer review.

## Findings

### Debt and subsequent interest-burden change

The focal estimate is −0.193 percentage points for a one-percentage-point
increase in lagged general-government debt, with a 95% interval from −0.347 to
−0.039 and an adjusted p-value of 0.0306.

The estimate is statistically distinguishable from zero under the registered
model but has the opposite sign from the predeclared positive direction.
Accordingly, `not_supported / limited` is the correct status. It must not be
relabelled as support, nor interpreted as evidence that additional debt reduces
interest burden. General-government debt and central-government interest
payments also have different institutional coverage.

All five robustness fits retain the opposite direction and are correctly
classified as not supporting the registered positive hypothesis.

### Primary balance and subsequent debt change

The focal estimate is 0.294 percentage points for a one-percentage-point
stronger lagged primary balance, with a 95% interval from −0.749 to 1.338 and an
adjusted p-value of 0.5702.

The estimate neither has the registered negative direction nor meets the
adjusted significance threshold. Maximum Cook’s distance is 6.546, above the
hard threshold of 1.0, so `failed_diagnostics / limited` is correct. Removing
the most influential observation changes the focal estimate to approximately
−0.036 but remains highly uncertain; none of the five robustness fits supports
the registered hypothesis.

The result cannot isolate nominal growth, valuation effects or stock-flow
adjustments in debt dynamics.

### Persistent UPI adoption trend

The log-linear segmented model reports an annualised underlying trend of
410.826%, with a 95% interval from 206.650% to 750.949% and an adjusted p-value
of approximately `8.62e-9`.

All four registered robustness fits retain a positive trend. However, the
Breusch–Godfrey residual-autocorrelation p-value is approximately `5.57e-14`,
well below the registered 0.01 threshold. `failed_diagnostics / limited` is
therefore correct even though HAC uncertainty is used and robustness fits are
positive.

The large annualised value describes the early exponential adoption phase
within a segmented log trend. It is not a forecast of current annual growth and
does not identify an effect of UPI on tax capacity, formalisation or policy
outcomes.

## Versioned corrective decisions

The first live fiscal attempt stopped before publication because two singleton
COVID indicators created leverage-one observations. Decision 0003 combined
them into one two-year indicator. Decision 0004 then removed that all-zero
indicator from the robustness subsample that excludes both COVID years.

Both changes were versioned before publication. Main results, expected
directions and diagnostic thresholds were not changed to improve findings.

## Frontend review

The evidence interface:

- presents evidence at lens level, separately from descriptive time-series
  metrics;
- spells out the full status rather than using a generic significance badge;
- surfaces failed diagnostics before collapsed technical details;
- displays focal estimates, intervals, adjusted p-values, sample coverage,
  robustness counts and limitations;
- retains the registered claim, null, formula and causal flag;
- does not recompute or reinterpret statistics in the browser.

The current evidence may be displayed with these qualifications. Prominent
policy conclusions should still wait for external analytical review and, for
UPI, a better-specified serial-dependence model registered as a future version
rather than retrofitted to version 1.0.0.
