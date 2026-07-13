import Panel from "../../components/Panel";
import { LoadingBlock, ErrorBlock } from "../../components/DataState";
import { useJson } from "../../lib/dataLoader";

function percentileBar(pct) {
  const color = pct >= 75 ? "bg-[var(--color-brick)]" : pct >= 50 ? "bg-[var(--color-marigold)]" : "bg-[var(--color-teal)]";
  return (
    <div className="w-16 h-1.5 rounded-full bg-[var(--color-border)] overflow-hidden">
      <div className={`h-full ${color}`} style={{ width: `${pct}%` }} />
    </div>
  );
}

export default function VolatilityTable() {
  const { data, loading, error } = useJson("currency", "volatility_summary");

  return (
    <Panel title="Volatility Summary" subtitle={data ? `${data.metadata.window_days}-day annualized` : undefined}>
      {loading && <LoadingBlock label="Loading volatility" />}
      {error && <ErrorBlock message={error} />}
      {data && (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-[var(--color-text-faint)] font-mono text-xs uppercase tracking-wide">
              <th className="pb-2 font-medium">Pair</th>
              <th className="pb-2 font-medium text-right">Ann. Vol</th>
              <th className="pb-2 font-medium text-right">Current</th>
              <th className="pb-2 font-medium text-right">1Y Percentile</th>
            </tr>
          </thead>
          <tbody>
            {data.pairs.map((row) => (
              <tr key={row.pair} className="border-t border-[var(--color-border-soft)]">
                <td className="py-2 font-medium">{row.pair}</td>
                <td className="py-2 text-right font-mono tabular-figures text-[var(--color-text-muted)]">
                  {row.annualized_vol_pct.toFixed(1)}%
                </td>
                <td className="py-2 text-right font-mono tabular-figures">{row.current_vol_pct.toFixed(1)}%</td>
                <td className="py-2">
                  <div className="flex items-center justify-end gap-2">
                    <span className="font-mono tabular-figures text-xs text-[var(--color-text-muted)]">
                      {row.vol_percentile_1y}
                    </span>
                    {percentileBar(row.vol_percentile_1y)}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Panel>
  );
}
