import type {
  DataSchemaName,
  StaticPayload,
} from "./types";

const objectLike = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

export function detectSchema(payload: unknown): DataSchemaName | null {
  if (!objectLike(payload)) return null;
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
    "multi-series-line": "dated_multi_series",
    "market-performance": "market_performance",
    "capex-correlation": "dated_multi_series",
    "corporate-fundamentals": "dated_multi_series",
    "fiscal-bridge": "dated_multi_series",
    "capex-scenario-lab": "dated_multi_series",
    "investment-quality": "dated_multi_series",
    "state-capex-evaluation": "dated_multi_series",
    "crowding-in": "dated_multi_series",
  };
  if (expected[component] !== schema) throw new Error(`${component} cannot render ${schema}`);
}
