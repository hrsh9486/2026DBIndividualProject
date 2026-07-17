import { useMemo, useState } from "react";
import { CartesianGrid, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { annualCountryToRows } from "../adapters/annualCountryToRows";
import { datedSeriesToRows } from "../adapters/datedSeriesToRows";
import { marketPerformanceToRows } from "../adapters/marketPerformanceToRows";
import type { AnnualCountryPayload, DatedPayload, MarketPayload, Presentation, StaticPayload } from "../data/types";
import { countryName, formatValue } from "../lib/format";
import EntityControls from "./EntityControls";

const COLORS = ["#d45132", "#176b87", "#6b7a3d", "#7b5c9a", "#c18b2f", "#4d6670"];

export default function ChartView({ payload, presentation }: { payload: StaticPayload; presentation: Presentation }) {
  const initialKeys = "india" in payload
    ? [payload.metadata.country, ...Object.keys(payload.peers)]
    : presentation.default_visible;
  const [visible, setVisible] = useState(initialKeys);
  const { rows, keys, labels } = useMemo(() => {
    if ("india" in payload) {
      const annual = payload as AnnualCountryPayload;
      const entityKeys = [annual.metadata.country, ...Object.keys(annual.peers)];
      return { rows: annualCountryToRows(annual), keys: entityKeys, labels: Object.fromEntries(entityKeys.map((key) => [key, countryName(key)])) };
    }
    if ("series" in payload) {
      const dated = payload as DatedPayload;
      const seriesKeys = dated.metadata.series_order ?? Object.keys(dated.series);
      return { rows: datedSeriesToRows(dated), keys: seriesKeys, labels: Object.fromEntries(seriesKeys.map((key) => [key, dated.series[key]?.label ?? key])) };
    }
    const market = payload as MarketPayload;
    const marketKeys = Object.keys(market.markets);
    const field = presentation.market_field ?? "normalized_value";
    return { rows: marketPerformanceToRows(market, field), keys: marketKeys, labels: Object.fromEntries(marketKeys.map((key) => [key, market.markets[key].label])) };
  }, [payload, presentation.market_field]);

  const active = visible.filter((key) => keys.includes(key));
  const plotted = active.length ? active : keys.slice(0, 1);
  const toggle = (key: string) => setVisible((current) => current.includes(key) ? current.filter((item) => item !== key) : [...current, key]);

  return <div>
    {(presentation.controls.entity_toggle || presentation.controls.series_toggle) && <EntityControls keys={keys} visible={plotted} onToggle={toggle} />}
    <div className="chart-wrap">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={rows} margin={{ top: 12, right: 16, bottom: 4, left: 0 }}>
          <CartesianGrid vertical={false} stroke="#ded9cf" strokeDasharray="2 5" />
          <XAxis dataKey="period" minTickGap={42} tickLine={false} axisLine={{ stroke: "#c8c0b2" }} tick={{ fill: "#706a61", fontSize: 11 }} />
          <YAxis width={62} tickLine={false} axisLine={false} tick={{ fill: "#706a61", fontSize: 11 }} tickFormatter={(value) => formatValue(value, presentation.value_format)} />
          {presentation.zero_line && <ReferenceLine y={0} stroke="#9b9489" />}
          <Tooltip contentStyle={{ background: "#fffdf8", border: "1px solid #cec6b9", borderRadius: 2 }} formatter={(value, name) => [formatValue(Number(value), presentation.value_format), labels[String(name)] ?? name]} />
          <Legend formatter={(key) => labels[String(key)] ?? key} />
          {plotted.map((key, index) => <Line key={key} dataKey={key} name={key} type="monotone" connectNulls={false} stroke={COLORS[index % COLORS.length]} strokeWidth={key === "IND" ? 2.8 : 1.8} dot={false} activeDot={{ r: 4 }} />)}
        </LineChart>
      </ResponsiveContainer>
    </div>
  </div>;
}
