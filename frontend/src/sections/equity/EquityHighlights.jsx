import Panel from "../../components/Panel";
import { formatMetricValue } from "../../lib/metrics";

const HIGHLIGHT_METRICS = [
  { key: "cagr", label: "Best CAGR", format: "percent" },
  { key: "sharpe_ratio", label: "Best Sharpe", format: "ratio" },
  { key: "annual_volatility", label: "Lowest Volatility", format: "percent" },
  { key: "max_drawdown", label: "Shallowest Drawdown", format: "percent" },
];

export default function EquityHighlights({ data }) {
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
      {HIGHLIGHT_METRICS.map(({ key, label, format }) => {
        const ranking = data.rankings[key] ?? [];
        const winner = ranking[0];
        const value = winner ? data.summary[winner]?.[key] : null;
        return (
          <Panel key={key}>
            <div className="text-xs font-mono uppercase tracking-wide text-[var(--color-text-faint)]">
              {label}
            </div>
            <div className="mt-2 text-lg font-semibold text-[var(--color-text-primary)] truncate" title={winner}>
              {winner ?? "—"}
            </div>
            <div className="mt-0.5 font-mono text-sm tabular-figures text-[var(--color-marigold)]">
              {value !== undefined ? formatMetricValue(value, format) : "—"}
            </div>
          </Panel>
        );
      })}
    </div>
  );
}
