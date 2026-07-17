import { relativeFreshness } from "../lib/format";

export default function DataStatusBadge({ generatedAt, staleAfterDays }: { generatedAt: string; staleAfterDays: number }) {
  const freshness = relativeFreshness(generatedAt, staleAfterDays);
  return <span className={`status-badge ${freshness.stale ? "stale" : "fresh"}`}><i />{freshness.stale ? "Stale" : freshness.label}</span>;
}
