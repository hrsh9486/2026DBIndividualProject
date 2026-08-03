export type DataSchemaName =
  | "annual_country_series"
  | "dated_multi_series"
  | "market_performance";

export type ChartAdapterName =
  | "country-comparison-line"
  | "multi-series-line"
  | "market-performance";

export interface StaticDataAsset {
  data_path: string;
  schema_path?: string;
  schema: DataSchemaName;
  expected_frequency:
    | "daily"
    | "weekly"
    | "monthly"
    | "quarterly"
    | "annual"
    | "mixed";
  stale_after_days: number;
  cache_strategy?: "no-cache" | "revalidate" | "immutable";
  version?: string;
  description?: string;
  availability?: "active" | "partial" | "planned";
}

export interface ChartRow {
  period: string;
  [seriesKey: string]: string | number | null;
}

export function assertAdapterMatchesSchema(
  adapter: ChartAdapterName,
  schema: DataSchemaName,
): void {
  const expected: Record<ChartAdapterName, DataSchemaName> = {
    "country-comparison-line": "annual_country_series",
    "multi-series-line": "dated_multi_series",
    "market-performance": "market_performance",
  };

  if (expected[adapter] !== schema) {
    throw new Error(
      `Adapter ${adapter} cannot render payload schema ${schema}`,
    );
  }
}
