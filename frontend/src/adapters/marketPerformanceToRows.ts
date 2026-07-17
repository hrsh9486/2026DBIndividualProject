import type { ChartRow, MarketPayload, MarketPoint } from "../data/types";

export function marketPerformanceToRows(payload: MarketPayload, field: keyof MarketPoint): ChartRow[] {
  const rows = new Map<string, ChartRow>();
  Object.entries(payload.markets).forEach(([key, market]) => {
    market.series.forEach((point) => {
      const row = rows.get(point.date) ?? { period: point.date };
      const value = point[field];
      row[key] = typeof value === "number" || value === null ? value : null;
      rows.set(point.date, row);
    });
  });
  return [...rows.values()].sort((a, b) => a.period.localeCompare(b.period));
}
