# Statistical Evidence Layer Implementation Plan

**Project:** India Structural Growth and Resilience Analysis  
**Status:** Proposed implementation roadmap  
**Prepared:** 27 July 2026  
**Scope:** Add reproducible descriptive and inferential evidence to the seven focused research lenses without weakening the existing ETL, provenance, validation, or static-publication architecture.

---

## 1. Purpose

The current project reliably answers:

> What do the selected official statistics report, how were they transformed, and what limitations attach to them?

The proposed evidence layer adds a second question:

> Given the available history and a pre-declared analytical design, how strong is the evidence for each research claim?

This is not a request to attach a p-value to every chart. The implementation must distinguish:

1. **Measurement evidence:** whether a statistic is correctly sourced, transformed, and published.
2. **Descriptive evidence:** whether a change is large enough to be economically or practically notable.
3. **Associational evidence:** whether two measures move together after accounting for trend, timing, and time-series dependence.
4. **Causal evidence:** whether a design identifies the effect of one variable on another.
5. **Insufficient evidence:** whether the available observations cannot support the proposed calculation or model.

The system must be able to publish an explicit `insufficient_data` conclusion. A statistically invalid result must never be presented merely because a model can technically be fitted.

---

## 2. Relationship to existing project documentation

This plan extends, rather than replaces, the current research and architecture documents.

### 2.1 Research scope

The existing research scope is defined in:

- [`focused_india_analysis_plan.docx`](focused_india_analysis_plan.docx)
- [`scripts/config/focused_indicators.py`](../../scripts/config/focused_indicators.py)

Those sources establish:

- the central research question;
- the seven connected analytical lenses;
- primary and supporting indicators;
- formulas and units;
- intended interpretations; and
- explicit limitations on causal claims.

The evidence layer must retain that scope discipline. New models are permitted only when they test an existing lens mechanism or a clearly identified subclaim. They must not become unrelated headline indicators.

### 2.2 Implemented architecture

The implemented architecture is documented in:

- [`FOCUSED_PIPELINE_ARCHITECTURE.docx`](../architecture/FOCUSED_PIPELINE_ARCHITECTURE.docx)
- [`README.md`](../../README.md)

The current processing path is:

```text
research registry
    → provider extractor
    → immutable raw snapshot
    → CanonicalRecord
    → deterministic transform
    → dated_multi_series payload
    → quality and JSON Schema validation
    → atomic processed publication
    → promotion
    → catalogue
    → frontend runtime guard and adapter
    → chart and interpretation panels
```

The evidence layer will extend this path:

```text
validated processed measurement artifacts
    → analytical alignment and eligibility checks
    → pre-declared estimator
    → diagnostics and robustness checks
    → evidence_report payload
    → quality and JSON Schema validation
    → atomic processed publication
    → promotion
    → catalogue evidence reference
    → frontend EvidencePanel
```

The input to statistical analysis must be the validated processed artifacts, or the same validated canonical records used to build them. It must not re-download data independently or scrape values from frontend JSON without contract validation.

### 2.3 Existing contracts and boundaries

The current contract registry is in [`scripts/config/indicators.py`](../../scripts/config/indicators.py). It defines:

- `annual_country_series`;
- `dated_multi_series`;
- `market_performance`; and
- `event_study`.

Relevant JSON Schemas are:

- [`schemas/annual_country_series.schema.json`](../../schemas/annual_country_series.schema.json)
- [`schemas/dated_multi_series.schema.json`](../../schemas/dated_multi_series.schema.json)
- [`schemas/market_performance.schema.json`](../../schemas/market_performance.schema.json)
- [`schemas/event_study.schema.json`](../../schemas/event_study.schema.json)

The statistical outputs should use a new `evidence_report` contract. They should **not** be inserted into `dated_multi_series` observations because:

- a regression coefficient is not a dated economic observation;
- model diagnostics require different validation rules;
- evidence may be unavailable even when the measurement artifact is active;
- the evidence model can change without changing the underlying observed series;
- multiple model specifications may refer to one measurement bundle; and
- a separate contract preserves the existing provider-neutral measurement boundary.

The existing `event_study` contract should remain available for named shock episodes. Evidence reports may reference an event-study asset, but should not duplicate its event-level results.

---

## 3. Current analytical readiness

The following coverage audit is based on the currently promoted focused artifacts in `frontend/public/data/`. Counts must be recomputed during each evidence build rather than hard-coded.

| Lens | Current useful coverage | Initial evidence status | Reason |
|---|---:|---|---|
| Digital integration | 123 monthly UPI observations; 4 annual GST-growth-gap observations | Partial | UPI adoption trend is testable; UPI–GST association is not |
| Government investment | 7–9 annual observations | Descriptive | Effects and execution gaps are reportable; inferential power is weak |
| Private investment | 3 annual GFCF observations; 5 quarterly capacity observations | Insufficient | The crowding-in relationship cannot be estimated credibly |
| Fiscal capacity | 41–43 annual observations | Model eligible | Longest internally consistent focused history |
| External competitiveness | 67 monthly REER; 16 quarterly current-account observations | Exploratory | Frequency alignment is possible, but the quarterly sample is small |
| Human capital | 4–5 annual observations | Insufficient | Too few overlapping employment observations |
| Capital resilience | 1 provisional flow observation | Insufficient | No time-series or event inference is possible |
| Market performance | Daily observations | Model eligible | Existing daily returns and event-study infrastructure support analysis |

These readiness labels describe analytical capability, not pipeline availability. The existing catalogue meanings of `active`, `partial`, and `planned` must remain unchanged.

---

## 4. Design principles

### 4.1 Pre-declare every claim

Every analysis must be registered before it is executed. The registry must define:

- stable analysis key;
- lens key;
- human-readable claim;
- null hypothesis;
- evidence class;
- dependent and explanatory series;
- required frequencies;
- alignment rule;
- transformation rule;
- estimator;
- lag structure;
- covariance or uncertainty method;
- minimum observation count;
- required diagnostics;
- robustness specifications;
- multiple-testing family;
- interpretation template;
- causal status; and
- known limitations.

Changing a model after seeing its result must create a new specification version, not silently mutate the old definition.

### 4.2 Lead with effect size

The frontend must display, in order:

1. practical interpretation;
2. estimate and unit;
3. 95% confidence interval;
4. sample size and coverage;
5. evidence grade;
6. method and robustness summary; and
7. p-value or adjusted p-value, where applicable.

A p-value must never be the headline.

### 4.3 Preserve non-causal language

Unless a future design supplies credible identification, the evidence classification must be `descriptive` or `associational`, with `causal: false`.

Words such as “caused,” “impact,” “effect of,” and “led to” must be disallowed from auto-generated interpretations for non-causal analyses. Prefer:

- “changed by” for descriptive comparisons;
- “is associated with” for regression or correlation;
- “predicts” only for explicitly lagged predictive specifications; and
- “evidence is insufficient” when eligibility gates fail.

### 4.4 Treat time-series structure explicitly

The focused indicators are primarily time series. Ordinary independent-observation tests are not the default. Depending on the model, the implementation must consider:

- deterministic trends;
- seasonality;
- autocorrelation;
- heteroskedasticity;
- non-stationary levels;
- structural breaks;
- lag choice;
- mixed frequencies;
- incomplete rolling windows;
- COVID-period sensitivity; and
- revisions and provisional observations.

HAC/Newey–West uncertainty should be the default for eligible time-series regressions unless another covariance estimator is justified in the specification.

### 4.5 Separate data absence from null evidence

The output must distinguish:

- `supported`: estimate and uncertainty meet the pre-declared decision rule;
- `not_supported`: an eligible analysis ran but did not meet the rule;
- `mixed`: main and robustness specifications materially disagree;
- `descriptive_only`: the registered output intentionally has no significance test;
- `insufficient_data`: eligibility gates prevented estimation;
- `failed_diagnostics`: estimation completed but required diagnostics invalidated interpretation; and
- `build_error`: an unexpected implementation or input-contract failure.

`build_error` must stop promotion. The other statuses are legitimate research outcomes and may be published.

### 4.6 Reproducibility before sophistication

The first release should use a small set of transparent estimators:

- differences and percentage-point changes;
- compound growth rates;
- linear trends;
- segmented trends with pre-declared break dates;
- Pearson or Spearman association only when appropriate;
- parsimonious OLS with lagged predictors and HAC uncertainty; and
- named event summaries using the existing event-study contract.

More complex models should be added only when they materially improve identification and can be tested reliably.

---

## 5. Proposed repository architecture

### 5.1 New directories and modules

```text
scripts/
  analysis/
    __init__.py
    alignment.py
    descriptive.py
    diagnostics.py
    estimators.py
    eligibility.py
    multiple_testing.py
    robustness.py
    interpretation.py
  builders/
    evidence_report.py
  config/
    evidence_specs.py
  models/
    evidence.py
  validators/
    evidence.py
  build_evidence_layer.py

schemas/
  evidence_report.schema.json

data/
  processed/
    evidence/
      digital-integration.json
      government-investment.json
      private-investment.json
      fiscal-capacity.json
      external-competitiveness.json
      human-capital.json
      capital-resilience.json
      market-performance.json

frontend/
  public/data/
    evidence/
      ...
    schemas/
      evidence_report.schema.json
  src/
    components/
      EvidencePanel.tsx
      EvidenceStatusBadge.tsx
    data/
      types.ts
      runtimeGuards.ts

tests/
  test_evidence_alignment.py
  test_evidence_estimators.py
  test_evidence_eligibility.py
  test_evidence_contract.py
  test_evidence_pipeline.py
  test_evidence_frontend_manifest.py
```

Names may be adjusted during implementation, but the separation among specification, alignment, estimation, validation, publication, and presentation must remain.

### 5.2 Dependency policy

The current runtime requirements are declared in [`requirements/requirements.txt`](../../requirements/requirements.txt) and already include NumPy and pandas. The first implementation should add:

- `scipy` for distributions and diagnostic calculations; and
- `statsmodels` for OLS, HAC covariance, time-series diagnostics, and stable result objects.

Pin compatible minimum versions after testing in the supported Python environment. Do not implement production statistical distributions or HAC covariance manually unless dependency constraints make that unavoidable.

Development requirements should include any static-analysis or testing packages needed to verify numerical outputs. Dependency changes must be reflected in the generated architecture documentation.

---

## 6. Evidence specification registry

Create [`scripts/config/evidence_specs.py`](../../scripts/config/evidence_specs.py) as the analytical equivalent of the focused indicator registry.

### 6.1 Proposed types

```python
class EvidenceClass(str, Enum):
    DESCRIPTIVE = "descriptive"
    ASSOCIATIONAL = "associational"
    EVENT_STUDY = "event_study"
    CAUSAL = "causal"


class EvidenceStatus(str, Enum):
    SUPPORTED = "supported"
    NOT_SUPPORTED = "not_supported"
    MIXED = "mixed"
    DESCRIPTIVE_ONLY = "descriptive_only"
    INSUFFICIENT_DATA = "insufficient_data"
    FAILED_DIAGNOSTICS = "failed_diagnostics"


@dataclass(frozen=True, slots=True)
class SeriesInput:
    asset_path: str
    series_key: str
    role: str
    expected_unit: str
    expected_frequency: str
    allowed_statuses: tuple[ObservationStatus, ...]
    transformation: str | None = None
    lag_periods: int = 0


@dataclass(frozen=True, slots=True)
class EvidenceSpec:
    key: str
    version: str
    lens_key: str
    label: str
    claim: str
    null_hypothesis: str | None
    evidence_class: EvidenceClass
    inputs: tuple[SeriesInput, ...]
    alignment: str
    estimator: str
    covariance: str | None
    minimum_observations: int
    minimum_complete_pairs: int | None
    diagnostics: tuple[str, ...]
    robustness: tuple[str, ...]
    multiple_testing_family: str | None
    alpha: float | None
    causal: bool
    limitation: str
```

Use enums or validated identifiers for transformations, estimators, alignment strategies, and diagnostics. Avoid arbitrary callable references or free-form executable expressions in configuration.

### 6.2 Versioning

Each specification must have a semantic or date-based version. The evidence payload must record:

- specification key;
- specification version;
- code version when available;
- source artifact paths;
- source artifact generation timestamps;
- source coverage;
- analysis generation timestamp; and
- estimator package versions.

If the repository is not running from a Git checkout with a resolvable commit, `code_version` may be `null`; this must not prevent a local build.

### 6.3 Registration tests

Add tests that ensure:

- analysis keys are unique;
- every lens key exists in `FOCUSED_BUNDLES`;
- every input artifact is registered with a known contract;
- every focused input series exists in the relevant bundle definition;
- declared units and frequencies match the focused registry;
- causal analyses cannot be registered without an identification note and required robustness design;
- `alpha` is inside `(0, 1)`;
- model analyses have non-null minimum sample requirements; and
- every inferential analysis belongs to a multiple-testing family or explicitly documents why it is a standalone confirmatory test.

---

## 7. Internal evidence model

Create provider-neutral result models in [`scripts/models/evidence.py`](../../scripts/models/evidence.py). These are analytical records, not extensions to `CanonicalRecord`.

### 7.1 Proposed result objects

```python
@dataclass(frozen=True, slots=True)
class Estimate:
    term: str
    value: float
    unit: str
    standard_error: float | None
    confidence_level: float | None
    confidence_interval_low: float | None
    confidence_interval_high: float | None
    p_value: float | None
    adjusted_p_value: float | None


@dataclass(frozen=True, slots=True)
class DiagnosticResult:
    key: str
    value: float | bool | str | None
    threshold: float | None
    passed: bool | None
    interpretation: str


@dataclass(frozen=True, slots=True)
class RobustnessResult:
    specification: str
    status: EvidenceStatus
    focal_estimate: Estimate | None
    sample_size: int
    note: str


@dataclass(frozen=True, slots=True)
class EvidenceResult:
    analysis_key: str
    specification_version: str
    status: EvidenceStatus
    evidence_class: EvidenceClass
    claim: str
    causal: bool
    sample_size: int
    start_date: date | None
    end_date: date | None
    estimates: tuple[Estimate, ...]
    diagnostics: tuple[DiagnosticResult, ...]
    robustness: tuple[RobustnessResult, ...]
    practical_interpretation: str
    limitation: str
    exclusion_summary: Mapping[str, int]
```

All numerical fields must be finite or `None`. NaN and infinity must be rejected before serialization, consistent with the existing strict JSON exporter.

---

## 8. New `evidence_report` JSON contract

### 8.1 Contract registration

Add:

```python
EVIDENCE_REPORT = "evidence_report.schema.json"
```

to `Contract` in [`scripts/config/indicators.py`](../../scripts/config/indicators.py).

Register promotion routes under `evidence/<lens>.json` in [`scripts/promote_processed_data.py`](../../scripts/promote_processed_data.py). Evidence assets must pass the same revalidation and atomic-write boundary as existing data assets.

### 8.2 Proposed top-level structure

```json
{
  "metadata": {
    "generated_at": "2026-07-27T12:00:00+00:00",
    "lens_key": "fiscal_capacity",
    "label": "Fiscal capacity evidence",
    "research_question": "Can general-government investment be sustained without debt service crowding out future spending?",
    "specification_registry_version": "1.0.0",
    "code_version": "abc123",
    "source_assets": [
      {
        "path": "fiscal-capacity/debt-and-interest-burden.json",
        "contract": "dated_multi_series",
        "generated_at": "2026-07-22T14:00:00+00:00",
        "start_date": "1984-03-31",
        "end_date": "2026-03-31"
      }
    ],
    "multiple_testing": {
      "method": "benjamini_hochberg",
      "family": "fiscal_capacity_primary",
      "alpha": 0.05
    }
  },
  "analyses": [
    {
      "analysis_key": "debt-predicts-interest-burden",
      "specification_version": "1.0.0",
      "label": "Lagged debt and interest burden",
      "claim": "Higher lagged debt is associated with a higher interest burden.",
      "null_hypothesis": "The coefficient on lagged debt is zero.",
      "evidence_class": "associational",
      "causal": false,
      "status": "supported",
      "sample": {
        "n": 39,
        "start_date": "1987-03-31",
        "end_date": "2025-03-31",
        "frequency": "annual",
        "excluded": {
          "missing": 1,
          "status": 2,
          "lag": 1
        }
      },
      "method": {
        "estimator": "ols",
        "formula": "delta_interest_burden ~ lag_debt + lag_primary_balance + trend",
        "covariance": "HAC",
        "max_lags": 2,
        "alignment": "fiscal_year_end_inner_join"
      },
      "estimates": [
        {
          "term": "lag_debt",
          "value": 0.18,
          "unit": "percentage_points_per_debt_percentage_point",
          "standard_error": 0.05,
          "confidence_level": 0.95,
          "confidence_interval": [0.08, 0.28],
          "p_value": 0.002,
          "adjusted_p_value": 0.006
        }
      ],
      "diagnostics": [],
      "robustness": [],
      "practical_interpretation": "A 10 percentage-point higher lagged debt ratio is associated with a 1.8 percentage-point change in the interest-to-revenue burden.",
      "limitation": "This is a historical association and does not isolate a causal debt-service effect."
    }
  ]
}
```

Values above are illustrative and must never appear as fixtures interpreted as actual project findings.

### 8.3 Schema requirements

Create [`schemas/evidence_report.schema.json`](../../schemas/evidence_report.schema.json) using Draft 2020-12. Require:

- top-level `metadata` and `analyses`;
- unique `analysis_key` values;
- enumerated evidence and status values;
- valid ISO dates and timestamps;
- `0 <= p_value <= 1`;
- `0 <= adjusted_p_value <= 1`;
- confidence level inside `(0, 1)`;
- two-item ordered confidence intervals;
- non-negative sample sizes;
- non-empty limitation and practical-interpretation text;
- explicit `causal` boolean;
- nullable estimates for non-estimable analyses;
- a structured eligibility reason when status is `insufficient_data`;
- diagnostic pass/fail fields;
- source artifact provenance; and
- no unknown top-level or analysis-level properties.

JSON Schema cannot enforce every cross-field rule. Python evidence validators must additionally enforce:

- `confidence_interval[0] <= estimate <= confidence_interval[1]`;
- adjusted p-values are present when a multiple-testing method applies;
- inferential statuses contain a focal estimate;
- descriptive-only results do not contain invented p-values;
- insufficient results contain no inferential estimates;
- the sample period lies inside the source-asset period;
- a non-causal result does not use prohibited causal interpretation language;
- analysis order matches `metadata.analysis_order`, if that field is used; and
- the output analyses exactly match the registered analyses for the selected lens.

Copy the schema into `frontend/public/data/schemas/` through the established schema-publication process. Do not maintain divergent backend and frontend copies manually.

---

## 9. Input loading, alignment, and exclusion accounting

### 9.1 Validated input loader

Create one loader that:

1. resolves a registered processed artifact path;
2. loads the JSON;
3. validates it using the registered existing contract;
4. verifies the requested series;
5. parses dates explicitly;
6. verifies unit, entity, and frequency against the evidence specification;
7. preserves observation status;
8. rejects duplicate dates;
9. returns a typed table; and
10. records the source artifact's generation time and coverage.

Analysis modules must not open arbitrary paths supplied at runtime.

### 9.2 Observation-status policy

Each input must declare allowed statuses. Recommended defaults:

- confirmatory historical models: `actual`, `revised`;
- exploratory current models: optionally `provisional`, with a robustness run excluding it;
- government-execution comparisons: preserve `budget`, `estimate`, and `actual` as distinct roles rather than pooling them;
- never silently treat estimates or budgets as actual observations.

The evidence report must count exclusions by status.

### 9.3 Alignment strategies

Implement named, tested strategies:

- `exact_date_inner_join`;
- `calendar_year_inner_join`;
- `fiscal_year_end_inner_join`;
- `quarter_end_inner_join`;
- `monthly_to_quarterly_mean`;
- `monthly_to_quarterly_end`;
- `monthly_to_quarterly_sum`;
- `annual_to_monthly_denominator`, only for already declared measurement transforms;
- `event_window_join`; and
- `lag_then_inner_join`.

The specification must choose the strategy. The estimator must not guess from the input dates.

For REER and current-account analysis, aggregate monthly REER to a quarterly mean before joining it to quarterly current-account observations. The result must disclose the aggregation.

### 9.4 Missing values and rolling windows

Retain the existing rule that null has meaning. Statistical input preparation must:

- never interpolate by default;
- exclude incomplete pairs explicitly;
- distinguish source nulls from lag-created nulls;
- distinguish incomplete rolling-window nulls from missing source data;
- report every exclusion count; and
- fail eligibility if the remaining complete sample is below the registered threshold.

### 9.5 Frequency and date semantics

Fiscal periods must use the existing [`FiscalPeriod`](../../scripts/models/canonical.py) semantics. Do not align Indian fiscal years to calendar years based only on the numeric year.

Academic-year human-capital observations need an explicit alignment policy. Until a defensible mapping is declared, the human-capital evidence result should remain descriptive or insufficient rather than joining academic-year enrolment mechanically to calendar-year employment.

---

## 10. Eligibility gates

Create deterministic eligibility checks in `scripts/analysis/eligibility.py`.

### 10.1 Global gates

Every analysis must pass:

- input contract validation;
- expected series, unit, entity, and frequency checks;
- permitted observation-status checks;
- no duplicate periods;
- finite non-null values;
- minimum total observations;
- minimum complete pairs;
- minimum variation in dependent and focal explanatory variables;
- sufficient residual degrees of freedom;
- no exact multicollinearity;
- no future information introduced by lag or aggregation; and
- a valid, pre-declared specification.

### 10.2 Suggested initial thresholds

Thresholds should live in the registry and be reviewed rather than treated as universal statistical laws.

| Analysis type | Suggested minimum |
|---|---:|
| Descriptive two-period change | 2 valid observations |
| Annual linear trend | 10 observations |
| Monthly trend with seasonality | 36 observations |
| Bivariate annual association | 20 complete pairs |
| Parsimonious annual regression | 30 complete observations and at least 10 observations per fitted parameter |
| Quarterly regression | 24 complete quarters preferred; 16 permitted only as explicitly exploratory |
| Monthly regression | 60 complete months preferred |
| Event comparison | At least 8 pre-declared events; otherwise descriptive |

The current external-competitiveness sample may be allowed under an `exploratory_small_sample` flag, but must receive a low maximum evidence grade regardless of p-value.

### 10.3 Failure output

An ineligible analysis should produce a valid evidence result:

```json
{
  "status": "insufficient_data",
  "eligibility": {
    "required_observations": 20,
    "available_observations": 3,
    "reason": "The crowding-in model requires at least 20 aligned annual observations."
  }
}
```

This is preferable to omitting the analysis because it shows that the research question was assessed and that the limitation is machine-enforced.

---

## 11. Estimators and diagnostics

### 11.1 Descriptive estimators

Implement and test:

- latest minus earliest change;
- latest minus registered baseline average;
- percentage-point change;
- percent change where denominators are valid;
- compound annual growth rate;
- compound monthly growth translated to annualised growth;
- mean execution gap;
- median and interquartile range;
- maximum drawdown and recovery duration, reusing existing market conventions; and
- pre/post differences for named, pre-specified periods.

Descriptive results may include uncertainty only when the uncertainty model is meaningful and declared.

### 11.2 Trend models

Implement:

- linear trend;
- log-linear trend for strictly positive adoption measures;
- month fixed effects for monthly data;
- segmented trend with a pre-declared break date; and
- HAC covariance with registered maximum lags.

UPI transaction values of zero or null require an explicit rule before log transformation. The implementation may use a registered start date after the launch phase; it must not add arbitrary constants merely to make logs possible.

### 11.3 Association and regression models

Initial regression support:

- OLS;
- lagged explanatory variables;
- first differences or growth rates;
- deterministic trend;
- a small number of registered controls; and
- HAC covariance.

Model formulas must be assembled from registered term identifiers, not arbitrary strings executed dynamically.

### 11.4 Diagnostics

Implement structured diagnostics appropriate to each model:

- residual sample size and degrees of freedom;
- condition number or variance-inflation warning;
- residual autocorrelation test;
- heteroskedasticity test where useful;
- unit-root/stationarity checks for level regressions;
- influential-observation sensitivity;
- residual normality as a descriptive diagnostic, not a universal pass/fail condition;
- stability or break test where the sample permits; and
- actual versus fitted/residual summaries for offline review.

The evidence registry must mark diagnostics as:

- required to interpret;
- advisory; or
- not applicable.

A required diagnostic failure should return `failed_diagnostics` or reduce the evidence grade according to a deterministic rule.

### 11.5 Multiple testing

Implement Benjamini–Hochberg correction over pre-declared families. Potential families:

- one primary family per research lens;
- one cross-lens exploratory family; and
- separate robustness estimates that do not each count as independent headline claims.

Bonferroni may be supported for narrowly defined confirmatory families. The output must record:

- method;
- family identifier;
- number of hypotheses;
- raw p-value;
- adjusted p-value; and
- decision threshold.

Do not pool unrelated descriptive results into a multiple-testing family merely because they share an output file.

---

## 12. Evidence grading

Introduce a deterministic grade that cannot be inferred from p-value alone.

### 12.1 Proposed grades

| Grade | Meaning |
|---|---|
| `not_assessed` | No eligible analysis has run |
| `descriptive` | Magnitude is reported without inferential support |
| `limited` | Eligible exploratory evidence with small sample or material diagnostic caveats |
| `moderate` | Direction and magnitude are stable across the main and required robustness specifications |
| `strong` | Pre-declared design, adequate sample, diagnostics, adjusted inference, and robust effect |

No current observational lens should be labelled `causal` merely because it receives a strong associational grade.

### 12.2 Grading inputs

The grade should consider:

- evidence class;
- sample adequacy relative to the registered minimum;
- confidence-interval width;
- adjusted significance decision;
- practical magnitude;
- required diagnostic outcomes;
- robustness direction and magnitude;
- sensitivity to COVID-period removal;
- sensitivity to provisional observations; and
- whether the analysis was designated confirmatory before execution.

Document the exact grading algorithm and test boundary cases. If a fully deterministic grade proves misleading, publish the component assessments and use a conservative manually registered grade with reviewer notes.

---

## 13. Lens-by-lens implementation

## 13.1 Digital integration and tax capacity

### Registered primary analysis

**Claim:** UPI transactions per capita show a persistent adoption trend beyond ordinary month-to-month variation.

**Input:** `upi_transactions_per_capita`, monthly.

**Model:**

```text
log(UPI transactions per capita)
    ~ time trend
    + calendar-month effects
    + registered post-break slope change
```

The break date must be justified and registered before estimating. If the pandemic is selected, distinguish a level disruption from a slope change.

**Uncertainty:** HAC/Newey–West.

**Outputs:**

- annualised adoption growth estimate;
- 95% confidence interval;
- raw and adjusted p-value for the focal trend or slope-change term;
- sample coverage;
- exclusion of launch-period zeros/nulls;
- sensitivity to alternative start date; and
- sensitivity excluding exceptional pandemic months.

### Descriptive supporting analyses

- UPI value/GDP latest versus first complete rolling-12-month observation;
- average transaction value trend and change;
- GST growth gap by year.

### Blocked main mechanism

Do not estimate UPI–GST association until the GST series meets its registered minimum. Publish:

- current complete overlap;
- required overlap;
- specific missing history required; and
- an `insufficient_data` status.

### Data enhancement

Prioritise extending official GST history and matched nominal-GDP growth. Before enabling a relationship model, verify consistent fiscal-year definitions, gross versus net receipts, and revision status.

---

## 13.2 Government investment and execution

### Primary descriptive claims

1. Actual central-government CapEx/GDP changed relative to a registered pre-period baseline.
2. Actual CapEx share of expenditure changed relative to baseline.
3. Delivery differed from the original Budget Estimate.

### Initial methods

- latest actual minus mean of the first three available actual years;
- percentage-point and relative changes;
- median execution ratio;
- mean absolute budget-to-actual execution gap; and
- count of over-execution and under-execution years.

With only 7–9 annual observations, label all outputs `descriptive_only`. Do not imply that repeated budget years constitute independent experimental draws.

### Data enhancement

Extend the historical Union Budget and matching nominal-GDP series. Enable a trend analysis only after at least 10 comparable actual observations and after checking for classification breaks.

### Future model

Once eligible:

```text
actual_capex_pct_gdp ~ trend + post_policy_level + post_policy_trend
```

This remains a descriptive interrupted-trend analysis unless a defensible counterfactual is added.

---

## 13.3 Private investment and crowding-in

### Current result

Register and publish the crowding-in analysis as `insufficient_data`.

The output must state separately:

- 3 private-corporate GFCF observations;
- 5 capacity-utilisation observations;
- 7 lagged public-CapEx observations; and
- number of complete aligned pairs after applying the declared frequency rule.

### Required data enhancement

Choose and document one viable design:

1. longer annual national-accounts series;
2. quarterly national private-investment proxy;
3. state-by-year panel; or
4. industry/firm panel.

The preferred next step is a longer official annual series because it fits the current architecture with the least conceptual change. A panel design would be more powerful but requires entity-aware analytical alignment and clustered uncertainty.

### Future national time-series model

```text
private_corporate_gfcf_pct_gdp[t]
    ~ public_capex_pct_gdp[t-1]
    + GDP_growth[t]
    + real_interest_rate[t]
    + capacity_utilisation[t-1]
```

Constraints:

- keep parameters proportional to available sample size;
- pre-register lag selection;
- test first differences or detrended series;
- report sensitivity across zero-, one-, and two-year lags as robustness, not independent discoveries; and
- retain `causal: false`.

---

## 13.4 Fiscal capacity and debt sustainability

This is the first priority for a complete inferential implementation.

### Primary analysis A

**Claim:** Higher lagged general-government debt is associated with a change in the central-government interest-to-revenue burden.

**Candidate model:**

```text
delta(interest_payments_pct_revenue[t])
    ~ general_government_debt_pct_gdp[t-1]
    + primary_balance_pct_gdp[t-1]
    + trend
```

Before finalising the formula, examine stationarity and ensure that central-government interest burden is not described as a direct decomposition of general-government debt.

### Primary analysis B

**Claim:** The primary balance predicts subsequent movement in general-government debt.

**Candidate model:**

```text
delta(general_government_debt_pct_gdp[t])
    ~ primary_balance_pct_gdp[t-1]
    + lagged_delta_debt[t-1]
    + registered exceptional-period indicators
```

### Required robustness

- levels versus first differences where diagnostics justify both;
- excluding COVID fiscal years;
- excluding provisional/estimate observations;
- alternative HAC lag of one and two years;
- excluding the most influential observation;
- central-government debt used only as a distinct alternative measure, not silently substituted; and
- a parsimonious bivariate form.

### Interpretation constraint

Translate focal coefficients into a meaningful increment, normally a 10 percentage-point debt change or a 1 percentage-point primary-balance change. Always state the mismatch in government coverage where relevant.

---

## 13.5 External competitiveness and resilience

### Alignment

- aggregate monthly REER to quarterly mean;
- optionally aggregate REER deviation in the same manner;
- align to current-account quarter-end dates;
- use non-oil export growth only if its monthly-to-quarterly aggregation is explicitly declared; and
- retain only information observable by the relevant quarter.

### Exploratory analysis

**Claim:** REER appreciation is associated with a weaker subsequent current-account balance.

```text
current_account_pct_gdp[t]
    ~ quarterly_mean_reer_deviation[t-1]
```

With 16 current-account observations, the first version must remain bivariate or nearly so. Label it exploratory and cap the evidence grade at `limited`.

### Robustness

- contemporaneous versus one-quarter lag;
- median rather than mean quarterly REER aggregation;
- exclude extreme pandemic quarters;
- use non-oil export growth as an alternative outcome, not an extra control in an over-parameterised model; and
- influence check for each quarter.

### Interpretation constraint

Never equate an REER index above 100 or a positive trailing deviation with overvaluation or fair-value error. The result concerns historical association with an external outcome.

---

## 13.6 Human-capital and employment conversion

### Current result

Publish `insufficient_data` for the relationship between tertiary GER and employment outcomes.

Provide descriptive changes for:

- tertiary GER;
- educated unemployment; and
- regular salaried employment share.

Do not calculate a correlation from four overlapping annual observations.

### Alignment research

Document how AISHE academic years map to PLFS reference years. Until this is resolved, the evidence layer must not infer an exact contemporaneous relationship.

### Data enhancement

Preferred options:

1. extend published PLFS comparable history;
2. use PLFS unit-level microdata; or
3. construct a state-year panel with consistent education and labour-market definitions.

Microdata would require a new analysis boundary that preserves survey weights, stratification, clustering, and disclosure constraints. It should be planned separately rather than treated as an ordinary focused transform.

---

## 13.7 Domestic capital resilience

### Current result

Publish `insufficient_data`. One provisional observation cannot support an offset relationship or event comparison.

### Accumulation milestone

Continue the prospective NSE raw-snapshot process already documented in the architecture. Do not enable rolling-12-month inference until at least 12 complete monthly periods exist, and do not enable monthly association models at that point merely because the rolling statistic becomes available.

### Event-study implementation

Use the existing:

- [`schemas/event_study.schema.json`](../../schemas/event_study.schema.json);
- [`scripts/builders/event_study.py`](../../scripts/builders/event_study.py); and
- configured global shock definitions.

For each pre-declared event, compute:

- cumulative FPI flow;
- cumulative DII flow;
- DII offset ratio;
- Nifty maximum drawdown;
- currency movement if available; and
- recovery days.

Until at least eight comparable pre-declared events exist, show event summaries descriptively. Thereafter consider:

```text
event_drawdown
    ~ dii_offset_ratio
    + global_market_drawdown
    + event_duration
```

This remains associational because DII buying is endogenous to market conditions.

### Monthly future model

Once at least 60 complete months are available:

```text
Nifty return or realised volatility[t]
    ~ FPI net flow[t]
    + DII net flow[t]
    + interaction(FPI selling, DII offset)[t]
    + global market return[t]
```

Pre-register whether the outcome is return, drawdown, or volatility. Do not select the most significant outcome after estimation.

---

## 13.8 Market-performance supporting evidence

The retained market-performance asset already calculates return, drawdown, rolling volatility, and correlations. It can support the capital-resilience event work and broader peer context.

Required improvements:

- ensure correlation sample periods are identical across pairs;
- include sample count and coverage with each correlation;
- avoid significance tests on raw price levels;
- use returns for correlation and volatility analysis;
- add confidence intervals only after accounting for serial dependence;
- use the existing event-study contract for named shocks; and
- keep market evidence supporting the focused capital-resilience lens rather than creating an eighth disconnected research chapter.

---

## 14. Robustness workflow

For each eligible inferential analysis:

1. Build the aligned analytical sample.
2. Freeze its coverage and exclusion report.
3. Run the registered main specification.
4. Run required diagnostics.
5. Run registered robustness specifications.
6. Apply multiple-testing correction to the declared family.
7. Assign status and evidence grade using deterministic rules.
8. Generate constrained practical interpretation.
9. Validate the evidence payload.
10. Publish atomically.

Robustness should answer concrete threats:

| Threat | Example response |
|---|---|
| Trending levels | First differences, growth rates, trend term, stationarity check |
| Exceptional pandemic period | Exclusion sensitivity and explicit event indicator |
| Provisional data | Actual/revised-only sensitivity |
| Lag arbitrariness | Pre-declared alternative lag sensitivity |
| Single influential year | Leave-one-out or influence diagnostic |
| Frequency mismatch | Alternative registered aggregation |
| Small sample | Parsimonious specification and limited evidence grade |
| Multiple claims | Benjamini–Hochberg adjustment |
| Definition mismatch | Reject alignment or publish limitation |

Robustness results must not be reduced to “passed” merely because they share the same significance threshold. Compare coefficient direction, magnitude, interval, and sample changes.

---

## 15. Pipeline orchestration

### 15.1 New build entry point

Create `scripts/build_evidence_layer.py` with:

```bash
python3 scripts/build_evidence_layer.py
python3 scripts/build_evidence_layer.py fiscal_capacity digital_integration
python3 scripts/build_evidence_layer.py --promote
python3 scripts/build_evidence_layer.py --frontend-build
```

Recommended default behavior:

1. require existing validated focused processed artifacts;
2. build selected evidence reports;
3. validate and atomically publish under `data/processed/evidence/`;
4. promote only with `--promote`, or when called by the full focused pipeline;
5. refresh catalogue evidence references; and
6. optionally run the frontend build.

### 15.2 Integration with focused pipeline

Extend [`scripts/build_focused_pipeline.py`](../../scripts/build_focused_pipeline.py) with:

- `--evidence`;
- `--evidence-only`, if operationally useful;
- dependency ordering so measurement assets build before evidence;
- evidence promotion only after all selected evidence reports validate; and
- frontend build after catalogue and evidence promotion.

Suggested command:

```bash
python3 scripts/build_focused_pipeline.py --evidence --frontend-build
```

The government-investment-before-private-investment dependency must remain. Add measurement-before-evidence dependencies explicitly rather than relying on filesystem timestamps.

### 15.3 Failure behavior

Preserve last-known-good behavior:

- source or measurement failure prevents dependent evidence rebuild;
- statistical ineligibility produces a valid research result;
- unexpected estimator, diagnostic, schema, or interpretation failure stops that evidence artifact;
- a failed evidence artifact cannot overwrite the last valid processed or frontend copy;
- unrelated lens artifacts may continue if the orchestrator reports failures clearly; and
- the command exits non-zero if any requested build has an unexpected failure.

### 15.4 Determinism

For identical input artifacts and code:

- estimates, intervals, diagnostics, statuses, and interpretation must be identical;
- analysis order must be stable;
- timestamps may differ;
- no estimator may use unseeded randomness; and
- any bootstrap method introduced later must use a registered fixed seed and record it.

---

## 16. Promotion and catalogue changes

### 16.1 Promotion routes

Update [`scripts/promote_processed_data.py`](../../scripts/promote_processed_data.py) to register the new contract and stable public paths. Do not infer evidence destinations from arbitrary filenames.

### 16.2 Catalogue representation

Extend the catalogue asset or lens model with an optional evidence reference. Preferred shape:

```json
{
  "id": "fiscal-capacity",
  "label": "Fiscal capacity and debt sustainability",
  "order": 4,
  "evidence_asset_id": "fiscal-capacity-evidence",
  "indicators": []
}
```

Register a corresponding asset:

```json
{
  "fiscal-capacity-evidence": {
    "data_path": "/data/evidence/fiscal-capacity.json",
    "schema_path": "/data/schemas/evidence_report.schema.json",
    "schema": "evidence_report",
    "expected_frequency": "mixed",
    "stale_after_days": 450,
    "cache_strategy": "revalidate",
    "version": "2026-07-27",
    "availability": "active",
    "description": "Registered statistical evidence for the fiscal-capacity lens."
  }
}
```

If `expected_frequency` is inappropriate for evidence assets, revise the catalogue schema so evidence assets have an explicit asset kind and do not pretend to be observation series. Prefer:

```json
{
  "asset_kind": "evidence",
  "schema": "evidence_report"
}
```

with frequency optional for evidence assets.

### 16.3 Availability semantics

Do not overload current measurement availability:

- measurement `active` means all registered series have a non-null value;
- evidence `active` means a valid evidence report exists;
- individual analysis status communicates support or insufficiency.

An evidence asset can be active even when all analyses say `insufficient_data`; publishing that limitation is intentional.

Update [`scripts/sync_focused_catalogue.py`](../../scripts/sync_focused_catalogue.py) to derive evidence availability separately and preserve unrelated legacy sections.

---

## 17. Frontend implementation

### 17.1 Types

Extend [`frontend/src/data/types.ts`](../../frontend/src/data/types.ts):

- add `"evidence_report"` to `DataSchemaName`;
- add evidence metadata, sample, method, estimate, diagnostic, robustness, and analysis types;
- extend `StaticPayload`;
- add `evidence_asset_id?: string` to `CatalogueSection`; and
- consider `asset_kind: "measurement" | "evidence"` on `StaticDataAsset`.

P-values and estimates must remain numeric or null; do not encode formatted statistical strings in the data contract.

### 17.2 Runtime guards

Extend [`frontend/src/data/runtimeGuards.ts`](../../frontend/src/data/runtimeGuards.ts) to detect `evidence_report` by `metadata` plus `analyses`.

Do not send evidence through a chart adapter. Either:

- add a separate evidence component-to-schema mapping; or
- distinguish page-level evidence assets from indicator views in the catalogue.

The second option is cleaner because evidence reports describe a research lens rather than one plotted series.

### 17.3 Static validation

Extend [`frontend/scripts/validate-public-data.mjs`](../../frontend/scripts/validate-public-data.mjs) to:

- compile `evidence_report.schema.json`;
- validate every evidence asset;
- verify each `evidence_asset_id`;
- check evidence/lens-key consistency;
- check unique analysis keys;
- verify measurement source paths refer to registered assets where possible;
- ensure unsupported adapters are not assigned to evidence assets; and
- validate that active evidence files exist.

### 17.4 Evidence presentation

Add an `EvidencePanel` near the top of [`ResearchLensPage.tsx`](../../frontend/src/pages/ResearchLensPage.tsx), before or after the metric jump navigation.

Recommended presentation per analysis:

```text
Claim
Practical interpretation

Estimate [95% confidence interval]       Evidence: Moderate
Sample: 39 annual observations           Association, not causation

Method and coverage
Robustness summary
Diagnostics and limitations
Raw and adjusted p-values (details)
```

For insufficient analyses:

```text
Evidence not yet estimable
3 aligned observations are available; the registered model requires 20.
The chart remains descriptive.
```

### 17.5 Accessibility and formatting

- Do not communicate support by colour alone.
- Give status badges explicit text.
- Format confidence intervals with an en dash and consistent precision.
- Display `p < 0.001` only when the numeric p-value is below that threshold; retain the exact numeric value in the payload.
- Never display `p = 0.000`.
- Explain “95% confidence interval,” “HAC,” and “adjusted p-value” in plain-language disclosure text.
- Keep methodology expandable so the primary claim remains readable.
- Ensure screen readers announce estimate, interval, and status coherently.

---

## 18. Validation and testing plan

### 18.1 Unit tests: alignment

Test:

- exact date joins;
- calendar versus fiscal-year joins;
- monthly-to-quarterly aggregation;
- lags applied in the correct direction;
- no look-ahead leakage;
- missing-value exclusion counts;
- observation-status exclusion;
- duplicate-date rejection; and
- academic-year alignment refusal when no mapping is registered.

### 18.2 Unit tests: estimators

Use small deterministic fixtures with known results:

- exact linear trend;
- known OLS coefficients;
- known confidence intervals within a documented tolerance;
- HAC result compared with a trusted `statsmodels` call;
- compound growth;
- segmented trend;
- zero-variance rejection;
- log-transform rejection for non-positive values; and
- first-difference date retention.

Numerical tests must use appropriate tolerances rather than exact floating-point equality.

### 18.3 Unit tests: multiple testing

Test Benjamini–Hochberg with:

- ordered and unordered p-values;
- ties;
- one hypothesis;
- null p-values excluded with reason;
- monotonic adjusted values; and
- all-zero/all-one boundary inputs.

### 18.4 Unit tests: status and grading

Cover:

- supported;
- not supported;
- mixed robustness;
- descriptive only;
- insufficient data;
- failed required diagnostic;
- small-sample grade cap;
- non-causal wording validation; and
- adjusted versus raw significance disagreement.

### 18.5 Contract tests

Mirror existing schema tests in [`tests/test_focused_pipeline.py`](../../tests/test_focused_pipeline.py) and [`tests/test_pipeline_architecture.py`](../../tests/test_pipeline_architecture.py).

Test:

- a complete valid evidence report;
- a valid insufficient-data report;
- invalid p-values;
- invalid confidence intervals;
- NaN rejection;
- missing source provenance;
- duplicate analysis keys;
- invalid status/evidence combinations;
- unexpected properties;
- inconsistent lens keys; and
- non-empty limitations.

### 18.6 Integration tests

Create fixture measurement artifacts and run:

```text
measurement contract validation
    → evidence build
    → evidence validation
    → atomic processed write
    → promotion
    → catalogue update
```

Verify:

- only registered artifacts are accepted;
- a failed candidate preserves the old output;
- an insufficient result is promoted successfully;
- a measurement timestamp and coverage appear in evidence provenance;
- selected lens builds do not alter unrelated evidence files; and
- output ordering is deterministic.

### 18.7 Frontend tests and checks

At minimum:

- TypeScript compiles;
- catalogue validation includes evidence assets;
- runtime detection accepts evidence and rejects ambiguous payloads;
- `EvidencePanel` renders all statuses;
- absent evidence does not break a lens page;
- insufficient evidence is clearly shown;
- method details are keyboard accessible; and
- production build succeeds.

### 18.8 End-to-end verification command

The implementation is complete only when this sequence succeeds:

```bash
python3 -m unittest discover -s tests
python3 scripts/build_focused_pipeline.py --evidence
python3 scripts/promote_processed_data.py
python3 scripts/sync_focused_catalogue.py
cd frontend
npm run validate:data
npx tsc --noEmit
npm run lint
npm run build
```

If the full pipeline requires network access, add a fixture-backed offline evidence integration command for continuous integration.

---

## 19. Documentation changes

### 19.1 README

Update [`README.md`](../../README.md) with:

- purpose of the evidence layer;
- evidence build commands;
- difference between measurement availability and evidence status;
- location of evidence specifications;
- location of evidence reports;
- supported estimators; and
- warning that evidence is associational unless explicitly labelled otherwise.

### 19.2 Generated architecture document

Update [`scripts/generate_architecture_docx.py`](../../scripts/generate_architecture_docx.py) so the generated architecture document includes:

- the extended pipeline diagram;
- `evidence_report` contract;
- analytical eligibility counts;
- specification registry;
- estimators and diagnostics;
- multiple-testing policy;
- lens-level current evidence status;
- frontend evidence flow;
- build and failure behavior; and
- glossary definitions for effect size, confidence interval, p-value, adjusted p-value, HAC, robustness, and causal identification.

Regenerate [`FOCUSED_PIPELINE_ARCHITECTURE.docx`](../architecture/FOCUSED_PIPELINE_ARCHITECTURE.docx) only after the implementation and tests reflect the documented architecture.

### 19.3 Methodology notes

For each enabled analysis, create or generate a stable methodology note containing:

- claim and null hypothesis;
- data sources and coverage;
- transformations and alignment;
- estimator and covariance;
- exclusions;
- diagnostics;
- robustness specifications;
- multiple-testing family;
- interpretation rule; and
- limitations.

These notes may be embedded in the evidence asset if concise, but the frontend must not rely on undocumented code behavior.

### 19.4 Decision log

Record material analytical decisions, especially:

- UPI trend start date and break date;
- COVID-period definitions;
- fiscal versus calendar alignment;
- REER quarterly aggregation;
- HAC lag selection;
- minimum sample thresholds;
- evidence grading algorithm; and
- criteria for enabling currently blocked analyses.

Use a dated Markdown decision log under `docs/planning/` or `docs/decisions/`.

---

## 20. Implementation phases

## Phase 0 — Analytical design freeze

**Goal:** Prevent model selection from being driven by observed significance.

Tasks:

- confirm the claim, null, estimator, frequency, lag, controls, diagnostics, and robustness for the first two model-eligible analyses;
- approve global eligibility thresholds;
- define multiple-testing families;
- define causal-language policy;
- choose evidence status and grade semantics;
- document exceptional COVID periods;
- document observation-status policy; and
- create the decision log.

Deliverables:

- initial `evidence_specs.py`;
- reviewed design table;
- no statistical output yet.

Acceptance criteria:

- every initial analysis has a stable key and version;
- every specification maps to registered focused series;
- no free-form post-result model choices remain.

## Phase 1 — Contract and core models

**Goal:** Establish a validated publication format before implementing estimators.

Tasks:

- add `Contract.EVIDENCE_REPORT`;
- create evidence result dataclasses;
- create Draft 2020-12 schema;
- implement evidence builder;
- implement cross-field validator;
- add strict serialization tests;
- add promotion routes; and
- copy/publish the schema to the frontend data directory.

Acceptance criteria:

- valid supported, descriptive, and insufficient fixtures pass;
- malformed intervals, p-values, statuses, and provenance fail;
- atomic promotion preserves the last valid artifact.

## Phase 2 — Loading, alignment, and eligibility

**Goal:** Make sample construction explicit and auditable.

Tasks:

- implement registered artifact loader;
- validate input contracts;
- implement date/frequency alignment strategies;
- implement lagging and differencing;
- implement status and missing-data exclusions;
- produce exclusion accounting;
- implement global and analysis-specific eligibility gates; and
- generate valid insufficient-data outputs.

Acceptance criteria:

- fiscal and calendar joins cannot be confused;
- no look-ahead leakage in fixtures;
- all seven lenses can produce either an eligible sample or a structured insufficiency report.

## Phase 3 — Descriptive evidence

**Goal:** Add useful evidence to every lens without overstating inference.

Tasks:

- implement change, baseline, growth, execution-gap, and drawdown summaries;
- register descriptive results for government investment and human capital;
- add coverage/readiness results for private investment and capital resilience;
- add practical interpretation generation;
- validate non-causal language; and
- publish initial evidence reports for all seven lenses.

Acceptance criteria:

- every lens has an active evidence report;
- ineligible relationships are explicitly labelled;
- no descriptive result contains a p-value without a declared uncertainty model.

## Phase 4 — First inferential analyses

**Goal:** Deliver the two strongest current model families.

Priority:

1. fiscal capacity;
2. digital UPI adoption trend.

Tasks:

- implement OLS and HAC covariance;
- implement trend and log-trend models;
- implement diagnostics;
- implement registered robustness;
- implement Benjamini–Hochberg adjustment;
- implement evidence grading; and
- compare numerical results with independently constructed notebook checks.

Acceptance criteria:

- fixture results match trusted calculations;
- main and robustness results are published;
- intervals, adjusted p-values, diagnostics, and exclusions are visible;
- interpretation remains associational.

## Phase 5 — Exploratory external-competitiveness model

**Goal:** Add a clearly limited quarterly association.

Tasks:

- implement monthly-to-quarterly REER aggregation;
- register bivariate lagged model;
- enforce small-sample grade cap;
- run influence and COVID sensitivity;
- publish current-account and export-outcome analyses separately; and
- document why findings are exploratory.

Acceptance criteria:

- the model uses no more parameters than pre-declared;
- all 16-or-fewer-quarter limitations are visible;
- no fair-value or causal language appears.

## Phase 6 — Frontend evidence experience

**Goal:** Make evidence understandable without turning the dashboard into a statistical report.

Tasks:

- extend catalogue and frontend types;
- extend validation and runtime guards;
- implement evidence data loading;
- build `EvidencePanel` and status badges;
- add expandable methods, diagnostics, and robustness;
- add plain-language glossary text;
- test responsive layout and accessibility; and
- integrate into each `ResearchLensPage`.

Acceptance criteria:

- all statuses render;
- missing or invalid evidence fails safely;
- charts remain usable independently;
- evidence is displayed before p-value detail;
- production frontend checks pass.

## Phase 7 — Data-extension programme

**Goal:** Move currently insufficient research questions toward eligibility.

Priorities:

1. extend private corporate GFCF history;
2. extend comparable government CapEx history;
3. extend GST history;
4. extend PLFS/AISHE comparable history or design a panel;
5. accumulate NSE institutional-flow history;
6. complete named global-shock event inputs; and
7. acquire control series only when required by registered models.

Each new source must follow the existing extractor → immutable raw evidence → canonical record → transform → validation process. Statistical urgency does not justify bypassing source provenance or contract checks.

---

## 21. Review and governance

### 21.1 Analytical review checklist

Before promoting a new or changed analysis:

- Is the claim already within the focused research scope?
- Was the specification declared before inspecting the final result?
- Are units and government/entity coverage comparable?
- Is the sample construction reproducible?
- Is the frequency alignment economically defensible?
- Is the minimum sample gate satisfied?
- Are trend and autocorrelation addressed?
- Are provisional and exceptional periods handled explicitly?
- Is the focal effect practically interpretable?
- Is multiple testing handled?
- Do robustness results materially agree?
- Does the language match the evidence class?
- Is `causal` false unless identification is independently justified?

### 21.2 Code review checklist

- No statistical computation occurs in React.
- No extractor performs inferential analysis.
- No evidence value is inserted into `CanonicalRecord`.
- No arbitrary runtime formula execution is allowed.
- No NaN or infinity is serialized.
- No unregistered artifact path is loaded.
- Every output is schema- and quality-validated before atomic publication.
- Tests cover numerical, contract, failure, and interpretation behavior.
- Generated documentation matches implementation.

### 21.3 Change control

The following require a specification-version change:

- dependent or explanatory variable change;
- frequency or aggregation change;
- lag change;
- estimator or covariance change;
- sample start/end rule change;
- control-set change;
- break-date change;
- eligibility threshold change; or
- multiple-testing-family change.

Pure label corrections that do not affect interpretation may be patched without a model version change, but the evidence artifact version and generation timestamp should still update.

---

## 22. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Significant results created by shared trends | Prefer differences/growth, include trend, check stationarity, disclose level-model limitations |
| Tiny samples produce unstable coefficients | Enforce eligibility gates and grade caps |
| Many metrics create false positives | Pre-register families and adjust p-values |
| COVID dominates short histories | Report exclusion sensitivity without erasing the main sample |
| Provisional observations revise materially | Record status and run actual/revised-only sensitivity |
| Mixed frequencies introduce arbitrary alignment | Named, registered alignment strategies |
| Central and general government series are conflated | Enforce entity/coverage metadata and interpretation warnings |
| Frontend implies causality | Controlled templates, causal badge, prohibited-language validation |
| Model changes silently alter results | Specification versions and source/code provenance |
| Evidence becomes stale after data refresh | Rebuild evidence after dependent measurement artifacts and expose generation timestamps |
| Complex statistics obscure the project | Lead with effect and practical interpretation; keep methods expandable |
| Failed new models overwrite valid results | Reuse validation and atomic publication boundaries |

---

## 23. Definition of done

The statistical evidence layer is complete for its first release when:

1. `evidence_report` is a registered, schema-validated contract.
2. Evidence specifications are typed, versioned, and mapped to existing focused series.
3. All evidence inputs come from validated registered artifacts.
4. Alignment, exclusions, and eligibility are explicit and tested.
5. All seven focused lenses publish an evidence report, including legitimate insufficient-data results.
6. Fiscal-capacity and UPI-adoption analyses include effect sizes, intervals, diagnostics, HAC uncertainty, robustness, and adjusted p-values.
7. External competitiveness is either published as explicitly exploratory or withheld by its eligibility gate.
8. No current private-investment, human-capital, or capital-resilience output overstates what its sample supports.
9. Promotion is atomic and preserves the last valid evidence artifact.
10. Catalogue and frontend validation understand evidence assets.
11. Lens pages lead with practical interpretation and clearly label descriptive, associational, and insufficient results.
12. Python tests and frontend validation, type, lint, and production builds pass.
13. README and generated architecture documentation describe the implemented evidence path.
14. A reviewer can trace every displayed result to its specification, input artifacts, sample coverage, estimator, diagnostics, and limitations.

---

## 24. Recommended first implementation slice

To minimise risk, implement one vertical slice before generalising:

```text
fiscal-capacity measurement artifact
    → registered lagged-debt specification
    → validated alignment
    → eligibility report
    → OLS/HAC estimate
    → diagnostics and COVID sensitivity
    → evidence_report JSON
    → atomic promotion
    → catalogue reference
    → EvidencePanel
```

After the fiscal-capacity slice passes end-to-end tests:

1. generalise the shared estimator and builder;
2. add the UPI trend model;
3. publish descriptive and insufficient-data reports for the other lenses;
4. add the exploratory external model; and
5. begin the data-extension programme.

This order proves the new contract and frontend path using the strongest current sample, while ensuring that every other lens gains an honest evidence status without forcing an invalid significance test.
