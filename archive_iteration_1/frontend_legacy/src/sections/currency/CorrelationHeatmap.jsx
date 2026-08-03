import Panel from "../../components/Panel";
import { LoadingBlock, ErrorBlock } from "../../components/DataState";
import { useJson } from "../../lib/dataLoader";

// Maps a correlation coefficient [-1, 1] to a background color,
// teal for positive, brick for negative, intensity by magnitude.
function cellStyle(value) {
  const magnitude = Math.min(Math.abs(value), 1);
  const alpha = 0.15 + magnitude * 0.65;
  const color = value >= 0 ? `rgba(79, 184, 168, ${alpha})` : `rgba(217, 99, 90, ${alpha})`;
  return { backgroundColor: color };
}

export default function CorrelationHeatmap() {
  const { data, loading, error } = useJson("currency", "correlation_summary");

  return (
    <Panel title="Cross-Pair Correlation" subtitle={data ? `${data.metadata.window_days}-day rolling` : undefined}>
      {loading && <LoadingBlock label="Loading correlations" />}
      {error && <ErrorBlock message={error} />}
      {data && (
        <div className="overflow-x-auto">
          <table className="text-xs font-mono border-separate" style={{ borderSpacing: 3 }}>
            <thead>
              <tr>
                <th className="w-16" />
                {data.pairs.map((p) => (
                  <th key={p} className="px-1 pb-1 text-[var(--color-text-faint)] font-medium">
                    {p.replace("INR", "")}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.matrix.map((row, i) => (
                <tr key={data.pairs[i]}>
                  <td className="pr-2 text-[var(--color-text-faint)] text-right">{data.pairs[i].replace("INR", "")}</td>
                  {row.map((value, j) => (
                    <td
                      key={j}
                      className="w-12 h-8 text-center align-middle rounded tabular-figures text-[var(--color-text-primary)]"
                      style={cellStyle(value)}
                    >
                      {value.toFixed(2)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Panel>
  );
}
