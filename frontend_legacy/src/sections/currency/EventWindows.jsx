import Panel from "../../components/Panel";
import { LoadingBlock, ErrorBlock } from "../../components/DataState";
import { useJson } from "../../lib/dataLoader";

export default function EventWindows() {
  const { data, loading, error } = useJson("currency", "event_windows");

  return (
    <Panel title="Stress Episodes" subtitle="Notable INR moves and their drivers">
      {loading && <LoadingBlock label="Loading events" />}
      {error && <ErrorBlock message={error} />}
      {data && (
        <ul className="space-y-3">
          {data.events.map((ev) => (
            <li key={ev.label} className="border-l-2 border-[var(--color-brick-dim)] pl-3">
              <div className="flex items-baseline justify-between gap-3">
                <span className="text-sm font-medium">{ev.label}</span>
                <span className="text-xs font-mono tabular-figures text-[var(--color-brick)] shrink-0">
                  {ev.pair} {ev.move_pct > 0 ? "+" : ""}
                  {ev.move_pct.toFixed(1)}%
                </span>
              </div>
              <div className="text-xs font-mono text-[var(--color-text-faint)] mt-0.5">
                {ev.start} → {ev.end}
              </div>
              <p className="text-xs text-[var(--color-text-muted)] mt-1 leading-relaxed">{ev.note}</p>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}
