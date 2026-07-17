import type { AnnualCountryPayload, MarketPayload, Presentation, StaticPayload } from "../data/types";
import { countryName, formatValue } from "../lib/format";

function latest(values: Array<{ value: number | null; year?: number }>) {
  return [...values].reverse().find((item) => item.value !== null);
}

export default function InsightRail({ payload, presentation }: { payload: StaticPayload; presentation: Presentation }) {
  if ("india" in payload) {
    const annual = payload as AnnualCountryPayload;
    const entries = [[annual.metadata.country, annual.india], ...Object.entries(annual.peers)] as const;
    const ranked = entries.map(([key, values]) => ({ key, point: latest(values) })).filter((item) => item.point).sort((a, b) => (b.point?.value ?? 0) - (a.point?.value ?? 0));
    return <div className="insight-list">{ranked.map(({ key, point }, index) => <div key={key} className={key === "IND" ? "highlight" : ""}><span>{String(index + 1).padStart(2, "0")}</span><strong>{countryName(key)}</strong><b>{formatValue(point?.value, presentation.value_format)}</b></div>)}</div>;
  }
  if ("markets" in payload) {
    const market = payload as MarketPayload;
    return <div className="insight-list">{Object.entries(market.markets).slice(0, 6).map(([key, item], index) => <div key={key}><span>{String(index + 1).padStart(2, "0")}</span><strong>{item.label}</strong><b>{formatValue(item.summary.total_return, { style: "percent", scale: 100, decimals: 1 })}</b></div>)}</div>;
  }
  return null;
}
