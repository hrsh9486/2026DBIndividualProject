import { useMemo, useState } from "react";
import {
  CartesianGrid,
  LabelList,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";
import type { DatedPayload } from "../data/types";

type Estimate = {
  label: string;
  lag: number;
  lag_unit: "months" | "years";
  outcome_type: "market" | "real_economy";
  direction?: "capex_leads" | "market_leads";
  pearson: number | null;
  spearman: number | null;
  n: number;
  pearson_excluding_pandemic: number | null;
  n_excluding_pandemic: number;
};

type Point = { capex: number; outcome: number; period: string };
type RegressionSegment = [{ x: number; y: number }, { x: number; y: number }];

const MIN_SAMPLE = 4;
const lagLabel = (estimate: Estimate) => estimate.direction === "market_leads"
  ? `Market leads CapEx by ${estimate.lag} ${estimate.lag_unit}`
  : estimate.lag === 0
    ? "Immediate response"
    : `Response after ${estimate.lag} ${estimate.lag_unit}`;

function heatColour(value: number | null, eligible: boolean) {
  if (!eligible || value === null) return "#e6e1d8";
  const strength = Math.min(Math.abs(value), 1);
  return value >= 0
    ? `rgba(40, 116, 96, ${0.16 + strength * 0.68})`
    : `rgba(181, 73, 51, ${0.16 + strength * 0.68})`;
}

function alignedPoints(payload: DatedPayload, seriesKey: string, excludePandemic: boolean): Point[] {
  const capex = new Map(
    (payload.series.nominal_capex_growth?.values ?? [])
      .filter((row) => typeof row.value === "number")
      .map((row) => [row.date, row]),
  );
  return (payload.series[seriesKey]?.values ?? []).flatMap((row) => {
    const x = capex.get(row.date);
    if (typeof x?.value !== "number" || typeof row.value !== "number") return [];
    const year = Number(row.date.slice(0, 4));
    if (excludePandemic && (year === 2021 || year === 2022)) return [];
    return [{ capex: x.value, outcome: row.value, period: row.period_label ?? row.date }];
  });
}

function regressionSegment(points: Point[]): RegressionSegment | null {
  if (points.length < 2) return null;
  const meanX = points.reduce((sum, point) => sum + point.capex, 0) / points.length;
  const meanY = points.reduce((sum, point) => sum + point.outcome, 0) / points.length;
  const denominator = points.reduce((sum, point) => sum + (point.capex - meanX) ** 2, 0);
  if (denominator === 0) return null;
  const slope = points.reduce(
    (sum, point) => sum + (point.capex - meanX) * (point.outcome - meanY),
    0,
  ) / denominator;
  const intercept = meanY - slope * meanX;
  const minX = Math.min(...points.map((point) => point.capex));
  const maxX = Math.max(...points.map((point) => point.capex));
  return [
    { x: minX, y: intercept + slope * minX },
    { x: maxX, y: intercept + slope * maxX },
  ];
}

function MiniScatter({
  payload,
  seriesKey,
  estimate,
  method,
  excludePandemic,
  active,
  onSelect,
}: {
  payload: DatedPayload;
  seriesKey: string;
  estimate: Estimate;
  method: "pearson" | "spearman";
  excludePandemic: boolean;
  active: boolean;
  onSelect: () => void;
}) {
  const points = alignedPoints(payload, seriesKey, excludePandemic);
  const value = excludePandemic ? estimate.pearson_excluding_pandemic : estimate[method];
  const n = excludePandemic ? estimate.n_excluding_pandemic : estimate.n;
  const trend = regressionSegment(points);
  return <article className={active ? "mini-scatter active" : "mini-scatter"}>
    <button onClick={onSelect}>
      <span>{estimate.label}</span>
      <b>{n >= MIN_SAMPLE && value !== null ? `r = ${value.toFixed(2)}` : "Insufficient"}</b>
      <small>n = {n}</small>
    </button>
    <div className="mini-scatter-chart">
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart margin={{ top: 8, right: 8, bottom: 8, left: -18 }}>
          <CartesianGrid stroke="#e5dfd5" strokeDasharray="2 5" />
          <XAxis type="number" dataKey="capex" tick={{ fontSize: 9 }} />
          <YAxis type="number" dataKey="outcome" tick={{ fontSize: 9 }} />
          <ZAxis range={[38, 38]} />
          <Tooltip formatter={(tooltipValue) => `${Number(tooltipValue).toFixed(1)}%`} />
          {trend && <ReferenceLine segment={trend} stroke="#4d5960" strokeWidth={1.5} />}
          <Scatter data={points} fill={active ? "#d45132" : "#176b87"} />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  </article>;
}

export default function CapexCorrelationView({ payload }: { payload: DatedPayload }) {
  const estimates = (payload.metadata.correlation_estimates ?? {}) as Record<string, Estimate>;
  const keys = Object.keys(estimates);
  const [selected, setSelected] = useState(keys[0] ?? "");
  const [method, setMethod] = useState<"pearson" | "spearman">("pearson");
  const [excludePandemic, setExcludePandemic] = useState(false);
  const [direction, setDirection] = useState<"capex_leads" | "market_leads">("capex_leads");
  const selectedEstimate = estimates[selected];
  const visibleKeys = keys.filter((key) => {
    const estimate = estimates[key];
    const estimateDirection = estimate.direction ?? "capex_leads";
    return direction === "capex_leads"
      ? estimateDirection === "capex_leads"
      : estimate.outcome_type === "market" && estimateDirection === "market_leads";
  });
  const outcomeLabels = [...new Set(visibleKeys.map((key) => estimates[key].label))];
  const selectedOutcome = selectedEstimate?.label ?? outcomeLabels[0] ?? "";
  const windowKeys = visibleKeys.filter((key) => estimates[key].label === selectedOutcome);
  const changeDirection = (nextDirection: "capex_leads" | "market_leads") => {
    setDirection(nextDirection);
    setSelected(keys.find((key) => {
      const estimate = estimates[key];
      const estimateDirection = estimate.direction ?? "capex_leads";
      return nextDirection === "capex_leads"
        ? estimateDirection === "capex_leads"
        : estimate.outcome_type === "market" && estimateDirection === "market_leads";
    }) ?? keys[0]);
  };

  const points = useMemo(
    () => alignedPoints(payload, selected, excludePandemic),
    [excludePandemic, payload, selected],
  );
  const trend = useMemo(() => regressionSegment(points), [points]);

  const displayedCorrelation = excludePandemic
    ? selectedEstimate?.pearson_excluding_pandemic
    : selectedEstimate?.[method];
  const displayedN = excludePandemic
    ? selectedEstimate?.n_excluding_pandemic
    : selectedEstimate?.n;
  const eligible = (displayedN ?? 0) >= MIN_SAMPLE;
  const comparableMarketKeys = selectedEstimate?.outcome_type === "market"
    ? keys.filter((key) => {
        const estimate = estimates[key];
        return estimate.outcome_type === "market"
          && estimate.lag === selectedEstimate.lag
          && estimate.lag_unit === selectedEstimate.lag_unit
          && (estimate.direction ?? "capex_leads") === (selectedEstimate.direction ?? "capex_leads");
      })
    : [];

  return <div className="correlation-explorer">
    <section className="correlation-guide">
      <span>How to read this stage</span>
      <ol>
        <li><b>Choose timing direction.</b> “CapEx leads” asks whether market performance followed recorded spending. “Nifty leads CapEx” asks whether markets moved before the spending observation, consistent with anticipation.</li>
        <li><b>Choose the timing window.</b> A six-month lead identifies which variable occurs first and the distance between the observations; it does not mean that variable caused the other.</li>
        <li><b>Read the coefficient.</b> Positive values mean higher CapEx growth and stronger relative returns tend to occur together; negative values mean they tend to move in opposite directions.</li>
        <li><b>Check sample size and sensitivity.</b> Treat small <i>n</i> as exploratory, then compare the result after excluding pandemic fiscal years.</li>
        <li><b>Inspect the scatter.</b> Each dot is a fiscal year. Look for a broad pattern and influential outliers rather than relying only on <i>r</i>.</li>
      </ol>
    </section>
    <section className="correlation-switcher" aria-label="Scatter plot controls">
      <div className="switcher-direction">
        <span>Timing</span>
        <div className="segmented">
          <button className={direction === "capex_leads" ? "active" : ""} onClick={() => changeDirection("capex_leads")}>CapEx leads</button>
          <button className={direction === "market_leads" ? "active" : ""} onClick={() => changeDirection("market_leads")}>Nifty leads</button>
        </div>
      </div>
      <label><span>Relationship</span><select value={selectedOutcome} onChange={(event) => {
        const next = visibleKeys.find((key) => estimates[key].label === event.target.value);
        if (next) setSelected(next);
      }}>{outcomeLabels.map((label) => <option key={label} value={label}>{label}</option>)}</select></label>
      <label><span>Window</span><select value={selected} onChange={(event) => setSelected(event.target.value)}>
        {windowKeys.map((key) => <option key={key} value={key}>{lagLabel(estimates[key])}</option>)}
      </select></label>
      <div>
        <span>Method</span>
        <div className="segmented">
          <button className={method === "pearson" ? "active" : ""} onClick={() => setMethod("pearson")}>Pearson</button>
          <button className={method === "spearman" ? "active" : ""} onClick={() => { setMethod("spearman"); setExcludePandemic(false); }}>Spearman</button>
        </div>
      </div>
      <label className="pandemic-toggle"><input type="checkbox" checked={excludePandemic} disabled={method === "spearman"} onChange={(event) => setExcludePandemic(event.target.checked)} /> Exclude pandemic years</label>
    </section>

    {selectedEstimate && <section className="correlation-scatter">
      <header>
        <div><span>Selected relationship</span><h3>{selectedEstimate.label}</h3><p>{lagLabel(selectedEstimate)}</p></div>
        <div className={eligible ? "correlation-reading" : "correlation-reading insufficient"}>
          <b>{eligible && displayedCorrelation !== null ? displayedCorrelation.toFixed(2) : "—"}</b>
          <span>{eligible ? `${method} correlation · n=${displayedN}` : `Insufficient data · n=${displayedN ?? 0}`}</span>
        </div>
      </header>
      <div className="scatter-wrap">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 18, right: 30, bottom: 24, left: 8 }}>
            <CartesianGrid stroke="#ded9cf" strokeDasharray="2 5" />
            <XAxis type="number" dataKey="capex" name="Nominal CapEx growth" unit="%" tick={{ fontSize: 11 }} label={{ value: "Actual nominal CapEx growth (%)", position: "bottom", offset: 8 }} />
            <YAxis type="number" dataKey="outcome" name={selectedEstimate.label} unit="%" width={66} tick={{ fontSize: 11 }} />
            <ZAxis range={[70, 70]} />
            <Tooltip cursor={{ strokeDasharray: "3 3" }} formatter={(value) => `${Number(value).toFixed(1)}%`} />
            {trend && <ReferenceLine segment={trend} stroke="#263f48" strokeWidth={2} />}
            <Scatter data={points} fill="#176b87">
              <LabelList dataKey="period" position="top" fontSize={10} fill="#5f5a52" />
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
      </div>
      <p className="metric-note">Each dot is one fiscal year. The fitted line is an ordinary least-squares visual summary and updates with the selected sample. The horizontal measure occurs first; association does not identify a causal effect.</p>
      {comparableMarketKeys.length > 1 && <div className="scatter-comparison">
        <div className="scatter-comparison-heading">
          <span>Same response window</span>
          <h4>Compare all major indices</h4>
          <p>Select any panel to open it in the detailed scatter above.</p>
        </div>
        <div className="mini-scatter-grid">
          {comparableMarketKeys.map((key) => <MiniScatter
            key={key}
            payload={payload}
            seriesKey={key}
            estimate={estimates[key]}
            method={method}
            excludePandemic={excludePandemic}
            active={key === selected}
            onSelect={() => setSelected(key)}
          />)}
        </div>
      </div>}
    </section>}
    <section className="correlation-heatmap" aria-label="Full correlation heatmap">
      <header className="heatmap-heading">
        <span>Correlation overview</span>
        <h3>Full lead and lag heatmap</h3>
      </header>
      <div className="heatmap-grid">
        {visibleKeys.map((key) => {
          const estimate = estimates[key];
          const value = excludePandemic ? estimate.pearson_excluding_pandemic : estimate[method];
          const n = excludePandemic ? estimate.n_excluding_pandemic : estimate.n;
          const enough = n >= MIN_SAMPLE;
          return <button
            key={key}
            className={selected === key ? "heat-cell selected" : "heat-cell"}
            style={{ background: heatColour(value, enough) }}
            onClick={() => setSelected(key)}
            title={`${estimate.label}; ${lagLabel(estimate)}; n=${n}`}
          >
            <span>{estimate.label}</span>
            <small>{lagLabel(estimate)}</small>
            <b>{enough && value !== null ? `r = ${value.toFixed(2)}` : "Insufficient data"}</b>
            <em>n = {n}</em>
          </button>;
        })}
      </div>
    </section>
  </div>;
}
