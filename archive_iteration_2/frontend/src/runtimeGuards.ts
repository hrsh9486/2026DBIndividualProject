import type {
  DataSchemaName,
  EvidenceReportPayload,
  StaticPayload,
} from "./types";

const objectLike = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

const evidenceStatuses = new Set([
  "supported",
  "not_supported",
  "mixed",
  "descriptive_only",
  "insufficient_data",
  "failed_diagnostics",
]);

export function isEvidenceReportPayload(payload: unknown): payload is EvidenceReportPayload {
  if (!objectLike(payload) || !objectLike(payload.metadata) || !Array.isArray(payload.analyses)) {
    return false;
  }
  if (
    typeof payload.metadata.generated_at !== "string"
    || typeof payload.metadata.lens_key !== "string"
    || typeof payload.metadata.specification_registry_version !== "string"
    || !Array.isArray(payload.metadata.source_assets)
  ) {
    return false;
  }
  return payload.analyses.length > 0 && payload.analyses.every((analysis) => (
    objectLike(analysis)
    && typeof analysis.analysis_key === "string"
    && typeof analysis.label === "string"
    && typeof analysis.status === "string"
    && evidenceStatuses.has(analysis.status)
    && objectLike(analysis.sample)
    && typeof analysis.sample.n === "number"
    && objectLike(analysis.method)
    && Array.isArray(analysis.estimates)
    && Array.isArray(analysis.diagnostics)
    && Array.isArray(analysis.robustness)
    && typeof analysis.practical_interpretation === "string"
    && typeof analysis.limitation === "string"
  ));
}

export function detectSchema(payload: unknown): DataSchemaName | null {
  if (!objectLike(payload)) return null;
  if (objectLike(payload.metadata) && Array.isArray(payload.india) && objectLike(payload.peers)) {
    return "annual_country_series";
  }
  if (objectLike(payload.metadata) && objectLike(payload.series)) return "dated_multi_series";
  if (isEvidenceReportPayload(payload)) return "evidence_report";
  if (objectLike(payload.metadata) && objectLike(payload.markets)) return "market_performance";
  return null;
}

export function assertPayload(payload: unknown, expected: DataSchemaName): asserts payload is StaticPayload {
  const detected = detectSchema(payload);
  if (detected !== expected) {
    throw new Error(`Expected ${expected}, received ${detected ?? "an unknown payload"}`);
  }
}

export function assertEvidenceReport(payload: unknown): asserts payload is EvidenceReportPayload {
  if (!isEvidenceReportPayload(payload)) {
    throw new Error("The evidence report failed its runtime structure guard");
  }
}

export function assertAdapterMatchesSchema(component: string, schema: DataSchemaName): void {
  const expected: Record<string, DataSchemaName> = {
    "country-comparison-line": "annual_country_series",
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
