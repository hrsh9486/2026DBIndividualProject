import { useState } from "react";
import Panel from "../../components/Panel";
import { METRICS, formatMetricValue } from "../../lib/metrics";

export default function EquitySummaryTable({ data }) {
  const markets = data.metadata.markets;
  const [sortKey, setSortKey] = useState("cagr");
  const [sortDir, setSortDir] = useState("desc");

  const metric = METRICS.find((m) => m.key === sortKey);

  const rows = [...markets].sort((a, b) => {
    const va = data.summary[a]?.[sortKey] ?? -Infinity;
    const vb = data.summary[b]?.[sortKey] ?? -Infinity;
    return sortDir === "desc" ? vb - va : va - vb;
  });

  function toggleSort(key) {
    if (key === sortKey) {
      setSortDir((d) => (d === "desc" ? "asc" : "desc"));
    } else {
      setSortKey(key);
      const m = METRICS.find((mm) => mm.key === key);
      setSortDir(m?.higherIsBetter === false ? "asc" : "desc");
    }
  }

  return (
    <Panel
      title="Index & ETF Summary"
      subtitle={`${data.metadata.start_date} → ${data.metadata.end_date} · ${data.metadata.trading_days.toLocaleString()} trading days`}
    >
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-[var(--color-text-faint)] font-mono text-xs uppercase tracking-wide">
              <th className="pb-2 pr-4 font-medium sticky left-0 bg-[var(--color-panel)]">Market</th>
              {METRICS.map((m) => (
                <th key={m.key} className="pb-2 px-2 font-medium text-right">
                  <button
                    onClick={() => toggleSort(m.key)}
                    className={[
                      "hover:text-[var(--color-text-primary)] transition-colors whitespace-nowrap",
                      sortKey === m.key ? "text-[var(--color-marigold)]" : "",
                    ].join(" ")}
                    title={m.label}
                  >
                    {m.short}
                    {sortKey === m.key && (sortDir === "desc" ? " ▾" : " ▴")}
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((market) => (
              <tr key={market} className="border-t border-[var(--color-border-soft)]">
                <td className="py-2 pr-4 font-medium sticky left-0 bg-[var(--color-panel)] whitespace-nowrap">
                  {market}
                </td>
                {METRICS.map((m) => {
                  const value = data.summary[market]?.[m.key];
                  const isNegativeGood = m.key === "max_drawdown";
                  return (
                    <td
                      key={m.key}
                      className={[
                        "py-2 px-2 text-right font-mono tabular-figures whitespace-nowrap",
                        isNegativeGood ? "text-[var(--color-brick)]" : "text-[var(--color-text-muted)]",
                        sortKey === m.key ? "text-[var(--color-text-primary)]" : "",
                      ].join(" ")}
                    >
                      {formatMetricValue(value, m.format)}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {metric && (
        <p className="mt-3 text-xs text-[var(--color-text-faint)]">
          Sorted by {metric.label} ({sortDir === "desc" ? "highest first" : "lowest first"}). Click any column to re-sort.
        </p>
      )}
    </Panel>
  );
}
