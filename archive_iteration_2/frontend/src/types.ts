export type DataSchemaName =
  | "annual_country_series"
  | "dated_multi_series"
  | "evidence_report"
  | "market_performance";

export type ChartAdapterName =
  | "country-comparison-line"
  | "multi-series-line"
  | "market-performance"
  | "capex-correlation"
  | "corporate-fundamentals"
  | "fiscal-bridge"
  | "capex-scenario-lab"
  | "investment-quality"
  | "state-capex-evaluation"
  | "crowding-in";

export interface ValueFormat {
  style: "number" | "percent" | "currency" | "ratio" | "index" | "months" | "compact";
  scale: number;
  decimals: number;
  currency?: string;
  prefix?: string;
  suffix?: string;
}

export interface Presentation {
  component: ChartAdapterName;
  chart_type: "line" | "scatter" | "bar";
  x_axis: "year" | "date";
  market_field?: "price" | "normalized_value" | "relative_to_nifty50" | "return" | "drawdown" | "rolling_volatility";
  default_visible: string[];
  value_format?: ValueFormat;
  controls: { date_range: boolean; entity_toggle: boolean; series_toggle: boolean };
  summary_fields?: Array<{ key: string; label: string; format: ValueFormat }>;
  zero_line?: boolean;
  show_source: boolean;
  show_methodology: boolean;
}

export interface StaticDataAsset {
  data_path: string;
  schema_path?: string;
  schema: DataSchemaName;
  expected_frequency: "daily" | "weekly" | "monthly" | "quarterly" | "annual" | "mixed";
  stale_after_days: number;
  cache_strategy?: "no-cache" | "revalidate" | "immutable";
  version?: string;
  description?: string;
  availability?: "active" | "partial" | "planned";
}

export interface IndicatorView { id: string; label: string; asset_id: string; presentation: Presentation; note?: string }
export interface Indicator { id: string; title: string; summary: string; default_view: string; views: IndicatorView[] }
export interface CatalogueSection {
  id: string;
  label: string;
  order: number;
  evidence_asset_id?: string;
  indicators: Indicator[];
}
export interface Catalogue {
  schema_version: string;
  generated_at: string;
  public_data_root: string;
  assets: Record<string, StaticDataAsset>;
  sections: CatalogueSection[];
  roadmap_total?: number;
}

export interface YearValue { year: number; value: number | null }
export interface AnnualCountryPayload {
  metadata: Record<string, unknown> & { generated_at: string; source: string; country: string; peers: string[]; label: string; unit: string };
  india: YearValue[];
  peers: Record<string, YearValue[]>;
}

export interface DatedValue { date: string; value: number | null; status?: string; period_label?: string }
export interface DatedPayload {
  metadata: Record<string, unknown> & { generated_at: string; source: Array<{ name: string }>; label: string; series_order: string[] };
  series: Record<string, {
    label: string;
    entity: string;
    unit: string;
    is_derived?: boolean;
    methodology?: string;
    source_note?: string;
    values: DatedValue[];
  }>;
}

export interface MarketPoint {
  date: string; price: number | null; normalized_value: number | null; return?: number | null;
  relative_to_nifty50?: number | null; drawdown?: number | null; rolling_volatility?: number | null;
}
export interface MarketPayload {
  metadata: Record<string, unknown> & { generated_at: string; source: string; start_date: string; end_date: string };
  markets: Record<string, {
    label: string; ticker: string; currency: string;
    summary: Record<string, number | null>; series: MarketPoint[];
  }>;
  correlations?: Array<{ market_a: string; market_b: string; correlation: number | null }>;
}

export type EvidenceStatus =
  | "supported"
  | "not_supported"
  | "mixed"
  | "descriptive_only"
  | "insufficient_data"
  | "failed_diagnostics";

export type EvidenceGrade =
  | "not_assessed"
  | "descriptive"
  | "limited"
  | "moderate"
  | "strong";

export interface EvidenceEstimate {
  term: string;
  value: number;
  unit: string;
  is_focal: boolean;
  standard_error: number | null;
  confidence_level: number | null;
  confidence_interval: [number, number] | null;
  p_value: number | null;
  adjusted_p_value: number | null;
}

export interface EvidenceDiagnostic {
  key: string;
  value: number | boolean | string | null;
  threshold: number | null;
  passed: boolean | null;
  interpretation: string;
}

export interface EvidenceRobustness {
  specification: string;
  status: EvidenceStatus;
  focal_estimate: EvidenceEstimate | null;
  sample_size: number;
  note: string;
}

export interface EvidenceAnalysis {
  analysis_key: string;
  specification_version: string;
  label: string;
  claim: string;
  null_hypothesis: string | null;
  evidence_class: "descriptive" | "associational" | "event_study" | "causal";
  causal: boolean;
  focal_terms: string[];
  expected_direction: "positive" | "negative" | "two_sided";
  support_rule: string;
  status: EvidenceStatus;
  grade: EvidenceGrade;
  sample: {
    n: number;
    start_date: string | null;
    end_date: string | null;
    frequency: string;
    excluded: Record<string, number>;
  };
  method: {
    estimator: string;
    formula: string;
    covariance: string | null;
    max_lags: number | null;
    alignment: string;
  };
  estimates: EvidenceEstimate[];
  diagnostics: EvidenceDiagnostic[];
  robustness: EvidenceRobustness[];
  eligibility: {
    eligible: boolean;
    required_observations: number;
    available_observations: number;
    reason: string;
    checks: Record<string, boolean>;
  } | null;
  practical_interpretation: string;
  limitation: string;
}

export interface EvidenceReportPayload {
  metadata: {
    generated_at: string;
    lens_key: string;
    label: string;
    research_question: string;
    specification_registry_version: string;
    code_version: string;
    source_assets: Array<{
      path: string;
      contract: string;
      sha256: string;
      generated_at: string;
      start_date: string;
      end_date: string;
    }>;
    analysis_order: string[];
    multiple_testing: {
      method: string;
      family: string;
      alpha: number;
    };
    software_versions: Record<string, string>;
  };
  analyses: EvidenceAnalysis[];
}

export type StaticPayload =
  | AnnualCountryPayload
  | DatedPayload
  | EvidenceReportPayload
  | MarketPayload;
export interface ChartRow { period: string; [seriesKey: string]: string | number | null }
