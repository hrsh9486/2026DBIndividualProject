import { useState } from "react";
import Panel from "../../components/Panel";
import { METRICS, formatMetricValue } from "../../lib/metrics";

export default function EquityRankings({ data }) {
  const [metricKey, setMetricKey] = useState("cagr");
  const metric = METRICS.find((m) => m.key === metricKey);
  const ranking = data.rankings[metricKey] ?? [];

  return (
    <Panel title="Rankings" subtitle="Best to worst, by metric">
      <select
        value={metricKey}
        onChange={(e) => setMetricKey(e.target.value)}
        className="mb-3 w-full bg-[var(--color-panel-raised)] border border-[var(--color-border)] rounded-md px-2 py-1.5 text-sm font-mono text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-marigold)]"
      >
        {METRICS.map((m) => (
          <option key={m.key} value={m.key}>
            {m.label}
          </option>
        ))}
      </select>

      <ol className="space-y-1">
        {ranking.map((market, i) => {
          const value = data.summary[market]?.[metricKey];
          const isTop = i === 0;
          const isBottom = i === ranking.length - 1;
          return (
            <li
              key={market}
              className="flex items-center gap-3 py-1.5 px-2 rounded-md hover:bg-[var(--color-panel-raised)]"
            >
              <span
                className={[
                  "w-5 text-xs font-mono tabular-figures text-right",
                  isTop ? "text-[var(--color-marigold)]" : "text-[var(--color-text-faint)]",
                ].join(" ")}
              >
                {i + 1}
              </span>
              <span className="flex-1 text-sm truncate">{market}</span>
              <span
                className={[
                  "text-xs font-mono tabular-figures",
                  isTop ? "text-[var(--color-teal)]" : isBottom ? "text-[var(--color-brick)]" : "text-[var(--color-text-muted)]",
                ].join(" ")}
              >
                {metric ? formatMetricValue(value, metric.format) : value}
              </span>
            </li>
          );
        })}
      </ol>
    </Panel>
  );
}
