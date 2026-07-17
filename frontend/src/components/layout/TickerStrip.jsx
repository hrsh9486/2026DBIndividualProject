import { useJson } from "../../lib/dataLoader";

function TickerItem({ label, value, delta, unit = "", pending = false }) {
  const isUp = typeof delta === "number" && delta > 0;
  const isDown = typeof delta === "number" && delta < 0;
  return (
    <div className="flex items-baseline gap-2 px-4 border-r border-[var(--color-border-soft)] last:border-r-0 whitespace-nowrap">
      <span className="text-[11px] font-mono uppercase tracking-wide text-[var(--color-text-faint)]">
        {label}
      </span>
      {pending ? (
        <span className="text-sm font-mono text-[var(--color-text-faint)]">pending</span>
      ) : (
        <>
          <span className="text-sm font-mono tabular-figures text-[var(--color-text-primary)]">
            {value}
            {unit}
          </span>
          {typeof delta === "number" && (
            <span
              className={[
                "text-xs font-mono tabular-figures",
                isUp ? "text-[var(--color-teal)]" : isDown ? "text-[var(--color-brick)]" : "text-[var(--color-text-faint)]",
              ].join(" ")}
            >
              {isUp ? "▲" : isDown ? "▼" : "•"} {Math.abs(delta).toFixed(2)}%
            </span>
          )}
        </>
      )}
    </div>
  );
}

export default function TickerStrip() {
  const { data } = useJson("currency", "rebased_performance");

  let usdinrValue = null;
  let usdinrDelta = null;
  if (data?.series?.length >= 2) {
    const last = data.series[data.series.length - 1];
    const prev = data.series[data.series.length - 2];
    usdinrValue = last.USDINR?.toFixed(1);
    usdinrDelta = prev.USDINR ? ((last.USDINR - prev.USDINR) / prev.USDINR) * 100 : null;
  }

  return (
    <div className="flex items-center h-10 border-b border-[var(--color-border)] bg-[var(--color-panel)] overflow-x-auto">
      <TickerItem label="USD/INR (rebased)" value={usdinrValue ?? "—"} delta={usdinrDelta} />
      <TickerItem label="Nifty 50" pending />
      <TickerItem label="Repo Rate" pending />
      <TickerItem label="CPI YoY" pending />
      <TickerItem label="Brent" pending />
      <div className="ml-auto px-4 text-[11px] font-mono text-[var(--color-text-faint)]">
        last sync 2026-07-01
      </div>
    </div>
  );
}
