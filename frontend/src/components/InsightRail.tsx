import type { DatedPayload, MarketPayload, Presentation, StaticPayload } from "../data/types";
import { formatValue } from "../lib/format";

function latest(values: Array<{ value: number | null; year?: number }>) {
  return [...values].reverse().find((item) => item.value !== null);
}

export default function InsightRail({ payload, presentation }: { payload: StaticPayload; presentation: Presentation }) {
  if ("markets" in payload) {
    const market = payload as MarketPayload;
    return <div className="insight-list">{Object.entries(market.markets).slice(0, 6).map(([key, item], index) => <div key={key}><span>{String(index + 1).padStart(2, "0")}</span><strong>{item.label}</strong><b>{formatValue(item.summary.total_return, { style: "percent", scale: 100, decimals: 1 })}</b></div>)}</div>;
  }
  if ("series" in payload) {
    const dated = payload as DatedPayload;
    const selected = presentation.default_visible.length
      ? presentation.default_visible
      : dated.metadata.series_order;
    const entries = selected
      .map((key) => ({ key, series: dated.series[key], point: latest(dated.series[key]?.values ?? []) }))
      .filter((item) => item.series && item.point);
    return <div className="insight-list">{entries.map(({ key, series, point }, index) => <div key={key}>
      <span>{String(index + 1).padStart(2, "0")}</span>
      <strong>{series.label}</strong>
      <b>{formatValue(point?.value, presentation.value_format)}</b>
    </div>)}</div>;
  }
  return null;
}
