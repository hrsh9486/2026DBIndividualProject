import { useMemo, useState } from "react";
import { CartesianGrid, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { datedSeriesToRows } from "../adapters/datedSeriesToRows";
import { marketPerformanceToRows } from "../adapters/marketPerformanceToRows";
import type { DatedPayload, MarketPayload, Presentation, StaticPayload } from "../data/types";
import { formatValue } from "../lib/format";
import { seriesColor } from "../lib/seriesColors";
import EntityControls from "./EntityControls";

const MAX_VISIBLE_POINT_MARKERS = 250;

export default function ChartView({ payload, presentation }: { payload: StaticPayload; presentation: Presentation }) {
  const [visible, setVisible] = useState(presentation.default_visible);
  const { rows, keys, labels } = useMemo(() => {
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
  const plotted = active;
  const pointCounts = useMemo(
    () => Object.fromEntries(keys.map((key) => [
      key,
      rows.reduce((count, row) => count + (typeof row[key] === "number" ? 1 : 0), 0),
    ])),
    [keys, rows],
  );
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
          {plotted.map((key) => {
            const color = seriesColor(keys.indexOf(key));
            const showPoints = presentation.show_points !== false && pointCounts[key] <= MAX_VISIBLE_POINT_MARKERS;
            return <Line
              key={key}
              dataKey={key}
              name={key}
              type="monotone"
              connectNulls={false}
              stroke={color}
              strokeWidth={1.8}
              dot={showPoints ? { r: 2.5, fill: "#fffdf8", stroke: color, strokeWidth: 1.5 } : false}
              activeDot={{ r: 4 }}
            />;
          })}
        </LineChart>
      </ResponsiveContainer>
    </div>
  </div>;
}
