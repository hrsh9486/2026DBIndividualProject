// Config for every metric in etf_base_stats.json's summary/rankings blocks.
// `higherIsBetter: false` is only true for annual_volatility — everything else,
// including max_drawdown, is "higher (closer to zero) is better" since these
// are stored as negative numbers.

export const METRICS = [
  { key: "total_return", label: "Total Return", short: "Total Ret.", format: "percent", higherIsBetter: true },
  { key: "cagr", label: "CAGR", short: "CAGR", format: "percent", higherIsBetter: true },
  { key: "annual_return", label: "Annual Return", short: "Ann. Ret.", format: "percent", higherIsBetter: true },
  { key: "annual_volatility", label: "Annual Volatility", short: "Ann. Vol.", format: "percent", higherIsBetter: false },
  { key: "sharpe_ratio", label: "Sharpe Ratio", short: "Sharpe", format: "ratio", higherIsBetter: true },
  { key: "sortino_ratio", label: "Sortino Ratio", short: "Sortino", format: "ratio", higherIsBetter: true },
  { key: "max_drawdown", label: "Max Drawdown", short: "Max DD", format: "percent", higherIsBetter: true },
  { key: "calmar_ratio", label: "Calmar Ratio", short: "Calmar", format: "ratio", higherIsBetter: true },
];

export const getMetric = (key) => METRICS.find((m) => m.key === key);

export function formatMetricValue(value, format) {
  if (value === null || value === undefined) return "—";
  if (format === "percent") return `${(value * 100).toFixed(1)}%`;
  return value.toFixed(2);
}
