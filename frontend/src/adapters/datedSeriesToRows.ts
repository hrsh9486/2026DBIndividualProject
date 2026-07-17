import type { ChartRow, DatedPayload } from "../data/types";

export function datedSeriesToRows(payload: DatedPayload): ChartRow[] {
  const rows = new Map<string, ChartRow>();
  Object.entries(payload.series).forEach(([key, series]) => {
    series.values.forEach(({ date, value }) => {
      const row = rows.get(date) ?? { period: date };
      row[key] = value;
      rows.set(date, row);
    });
  });
  return [...rows.values()].sort((a, b) => a.period.localeCompare(b.period));
}
