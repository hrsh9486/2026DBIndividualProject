import type { AnnualCountryPayload, ChartRow } from "../data/types";

export function annualCountryToRows(payload: AnnualCountryPayload): ChartRow[] {
  const rows = new Map<number, ChartRow>();
  const add = (key: string, values: Array<{ year: number; value: number | null }>) => {
    values.forEach(({ year, value }) => {
      const row = rows.get(year) ?? { period: String(year) };
      row[key] = value;
      rows.set(year, row);
    });
  };
  add(payload.metadata.country || "IND", payload.india);
  Object.entries(payload.peers).forEach(([entity, values]) => add(entity, values));
  return [...rows.entries()].sort(([a], [b]) => a - b).map(([, row]) => row);
}
