import Panel from "../../components/Panel";
import { LoadingBlock, ErrorBlock } from "../../components/DataState";
import { getCountryKeys, getCountrySeries, countryLabel, latestValue, earliestValue } from "../../lib/demographics";

export default function PeerComparisonTable({ data, loading, error }) {
  if (loading) return <Panel title="Loading…"><LoadingBlock label="Loading comparison" /></Panel>;
  if (error) return <Panel title="Error"><ErrorBlock message={error} /></Panel>;
  if (!data) return null;

  const keys = getCountryKeys(data);
  const indiaKey = keys.find((k) => k.toLowerCase() === "india");

  const rows = keys
    .map((key) => {
      const latest = latestValue(getCountrySeries(data, key));
      const earliest = earliestValue(getCountrySeries(data, key));
      const change = latest && earliest ? latest.value - earliest.value : null;
      return { key, latest, earliest, change };
    })
    .filter((r) => r.latest)
    .sort((a, b) => b.latest.value - a.latest.value);

  return (
    <Panel title="Peer Comparison" subtitle="Most recent available value per country">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-[var(--color-text-faint)] font-mono text-xs uppercase tracking-wide">
            <th className="pb-2 font-medium">Country</th>
            <th className="pb-2 font-medium text-right">Latest</th>
            <th className="pb-2 font-medium text-right">Year</th>
            <th className="pb-2 font-medium text-right">
              Since {data.metadata.start_year}
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const isIndia = row.key === indiaKey;
            const isUp = typeof row.change === "number" && row.change > 0;
            const isDown = typeof row.change === "number" && row.change < 0;
            return (
              <tr
                key={row.key}
                className={[
                  "border-t border-[var(--color-border-soft)]",
                  isIndia ? "bg-[var(--color-panel-raised)]" : "",
                ].join(" ")}
              >
                <td className={`py-2 ${isIndia ? "font-semibold" : "font-medium"}`}>
                  {countryLabel(row.key)}
                </td>
                <td className="py-2 text-right font-mono tabular-figures">
                  {row.latest.value.toFixed(1)}
                </td>
                <td className="py-2 text-right font-mono tabular-figures text-[var(--color-text-faint)]">
                  {row.latest.year}
                </td>
                <td
                  className={[
                    "py-2 text-right font-mono tabular-figures",
                    isUp ? "text-[var(--color-teal)]" : isDown ? "text-[var(--color-brick)]" : "text-[var(--color-text-muted)]",
                  ].join(" ")}
                >
                  {row.change !== null ? `${row.change > 0 ? "+" : ""}${row.change.toFixed(1)}` : "—"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </Panel>
  );
}
