import type { DataSchemaName, StaticPayload } from "./types";

const objectLike = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

export function detectSchema(payload: unknown): DataSchemaName | null {
  if (!objectLike(payload)) return null;
  if (objectLike(payload.metadata) && Array.isArray(payload.india) && objectLike(payload.peers)) {
    return "annual_country_series";
  }
  if (objectLike(payload.metadata) && objectLike(payload.series)) return "dated_multi_series";
  if (objectLike(payload.metadata) && objectLike(payload.markets)) return "market_performance";
  return null;
}

export function assertPayload(payload: unknown, expected: DataSchemaName): asserts payload is StaticPayload {
  const detected = detectSchema(payload);
  if (detected !== expected) {
    throw new Error(`Expected ${expected}, received ${detected ?? "an unknown payload"}`);
  }
}

export function assertAdapterMatchesSchema(component: string, schema: DataSchemaName): void {
  const expected: Record<string, DataSchemaName> = {
    "country-comparison-line": "annual_country_series",
    "multi-series-line": "dated_multi_series",
    "market-performance": "market_performance",
  };
  if (expected[component] !== schema) throw new Error(`${component} cannot render ${schema}`);
}
