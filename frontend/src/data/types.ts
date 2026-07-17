export type DataSchemaName =
  | "annual_country_series"
  | "dated_multi_series"
  | "market_performance";

export type ChartAdapterName =
  | "country-comparison-line"
  | "multi-series-line"
  | "market-performance";

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
  chart_type: "line";
  x_axis: "year" | "date";
  market_field?: "price" | "normalized_value" | "return" | "drawdown" | "rolling_volatility";
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
export interface CatalogueSection { id: string; label: string; order: number; indicators: Indicator[] }
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
  series: Record<string, { label: string; entity: string; unit: string; values: DatedValue[] }>;
}

export interface MarketPoint {
  date: string; price: number | null; normalized_value: number | null; return?: number | null;
  drawdown?: number | null; rolling_volatility?: number | null;
}
export interface MarketPayload {
  metadata: Record<string, unknown> & { generated_at: string; source: string; start_date: string; end_date: string };
  markets: Record<string, {
    label: string; ticker: string; currency: string;
    summary: Record<string, number | null>; series: MarketPoint[];
  }>;
  correlations?: Array<{ market_a: string; market_b: string; correlation: number | null }>;
}

export type StaticPayload = AnnualCountryPayload | DatedPayload | MarketPayload;
export interface ChartRow { period: string; [seriesKey: string]: string | number | null }
