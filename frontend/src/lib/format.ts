import type { ValueFormat } from "../data/types";

export function formatValue(value: number | null | undefined, format?: ValueFormat): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "—";
  const scaled = value * (format?.scale ?? 1);
  const decimals = format?.decimals ?? 1;
  if (format?.style === "currency") {
    return new Intl.NumberFormat("en-IN", {
      style: "currency", currency: format.currency ?? "INR", maximumFractionDigits: decimals,
    }).format(scaled);
  }
  if (format?.style === "compact") {
    return new Intl.NumberFormat("en-IN", { notation: "compact", maximumFractionDigits: decimals }).format(scaled);
  }
  const rendered = scaled.toLocaleString("en-IN", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
  const suffix = format?.style === "percent" ? "%" : format?.suffix ?? "";
  return `${format?.prefix ?? ""}${rendered}${suffix}`;
}

export function relativeFreshness(generatedAt: string, staleAfterDays: number): { label: string; stale: boolean } {
  const days = Math.max(0, Math.floor((Date.now() - new Date(generatedAt).getTime()) / 86_400_000));
  return { label: days === 0 ? "Updated today" : `Updated ${days}d ago`, stale: days > staleAfterDays };
}
