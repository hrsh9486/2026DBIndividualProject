import { useMemo, useState } from "react";
import {
  CartesianGrid,
  ReferenceLine,
  ReferenceLine as ScatterReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { DatedPayload } from "../data/types";

type PanelRow = {
  state: string;
  year: number;
  date: string;
  period_label: string;
  capex_pct_gsdp: number;
  next_year_real_gsdp_growth: number;
};

type PanelEstimate = {
  coefficient: number | null;
  clustered_standard_error: number | null;
  confidence_interval_95: [number | null, number | null] | null;
  n: number;
  states: number;
  years: number;
  eligible: boolean;
  interpretation: string;
  limitation: string;
};

type StateDotProps = {
  cx?: number;
  cy?: number;
  payload?: PanelRow;
  selectedState: string;
  selectedYear: string;
};

function StateDot({ cx, cy, payload, selectedState, selectedYear }: StateDotProps) {
  if (cx === undefined || cy === undefined || !payload) return null;
  const inYear = selectedYear === "all" || payload.year === Number(selectedYear);
  const highlighted = selectedState !== "all" && payload.state === selectedState;
  const opacity = inYear ? (selectedState === "all" ? .72 : highlighted ? 1 : .32) : 0;

  return <circle
    cx={cx}
    cy={cy}
    r={4.5}
    fill={highlighted ? "#a53f2b" : "#b7afa3"}
    opacity={opacity}
    pointerEvents={inYear ? "auto" : "none"}
    style={{ transition: "opacity 220ms ease-in-out" }}
  />;
}

function fixedDomain(values: number[]): [number, number] | undefined {
  if (!values.length) return undefined;
  const minimum = Math.min(...values);
  const maximum = Math.max(...values);
  const padding = (maximum - minimum || Math.abs(maximum) || 1) * 0.05;
  return [minimum - padding, maximum + padding];
}

export default function StateCapexEvaluationView({ payload }: { payload: DatedPayload }) {
  const observations = (payload.metadata.panel_observations as PanelRow[] | undefined) ?? [];
  const estimate = payload.metadata.panel_estimate as PanelEstimate | undefined;
  const states = useMemo(() => [...new Set(observations.map((row) => row.state))], [observations]);
  const years = useMemo(() => [...new Set(observations.map((row) => row.year))].sort(), [observations]);
  const xDomain = useMemo(() => fixedDomain(observations.map((row) => row.capex_pct_gsdp)), [observations]);
  const yDomain = useMemo(() => fixedDomain(observations.map((row) => row.next_year_real_gsdp_growth)), [observations]);
  const [state, setState] = useState("all");
  const [year, setYear] = useState("all");
  const selected = observations.filter((row) => (state === "all" || row.state === state) && (year === "all" || row.year === Number(year)));
  const means = selected.length ? {
    x: selected.reduce((sum, row) => sum + row.capex_pct_gsdp, 0) / selected.length,
    y: selected.reduce((sum, row) => sum + row.next_year_real_gsdp_growth, 0) / selected.length,
  } : null;
  const interval = estimate?.confidence_interval_95;

  return <div className="depth-view">
    <div className="depth-toolbar">
      <div><span>State filter</span><select value={state} onChange={(event) => setState(event.target.value)}><option value="all">All states</option>{states.map((value) => <option key={value}>{value}</option>)}</select></div>
      <div><span>CapEx year</span><select value={year} onChange={(event) => setYear(event.target.value)}><option value="all">All actual years</option>{years.map((value) => <option value={value} key={value}>FY{value - 1}-{String(value).slice(-2)}</option>)}</select></div>
    </div>
    <div className="depth-kpis">
      <article><span>Fixed-effects association</span><b>{estimate?.coefficient === null || estimate?.coefficient === undefined ? "—" : `${estimate.coefficient > 0 ? "+" : ""}${estimate.coefficient.toFixed(2)}pp`}</b><small>next-year growth per 1pp CapEx/GSDP</small></article>
      <article><span>95% interval</span><b>{interval ? `${interval[0]?.toFixed(2)} to ${interval[1]?.toFixed(2)}` : "—"}</b><small>state-clustered uncertainty</small></article>
      <article><span>Panel coverage</span><b>{estimate?.n ?? 0}</b><small>{estimate?.states ?? 0} states · {estimate?.years ?? 0} years</small></article>
      <article className={estimate?.eligible ? "positive" : "negative"}><span>Evidence gate</span><b>{estimate?.eligible ? "Eligible" : "Not eligible"}</b><small>associational, never causal</small></article>
    </div>
    <div className="depth-chart state-panel-chart">
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart margin={{ top: 18, right: 24, bottom: 18, left: 10 }}>
          <CartesianGrid stroke="#ded9cf" strokeDasharray="2 5" />
          <XAxis type="number" dataKey="capex_pct_gsdp" domain={xDomain} tickFormatter={(value) => Number(value).toFixed(0)} name="Capital outlay/GSDP" unit="%" label={{ value: "Capital outlay / GSDP (%)", position: "insideBottom", offset: -10 }} />
          <YAxis type="number" dataKey="next_year_real_gsdp_growth" domain={yDomain} tickFormatter={(value) => Number(value).toFixed(0)} name="Next-year real GSDP growth" unit="%" width={62} label={{ value: "Next-year real growth (%)", angle: -90, position: "insideLeft" }} />
          {means && <><ReferenceLine x={means.x} stroke="#928b80" strokeDasharray="3 5" /><ScatterReferenceLine y={means.y} stroke="#928b80" strokeDasharray="3 5" /></>}
          <Tooltip cursor={{ strokeDasharray: "3 3" }} formatter={(value, name) => [`${Number(value).toFixed(3)}%`, name]} labelFormatter={(_, items) => `${items?.[0]?.payload?.state ?? ""} · ${items?.[0]?.payload?.period_label ?? ""}`} />
          <Scatter
            data={observations}
            isAnimationActive={false}
            name="State-years"
            shape={<StateDot selectedState={state} selectedYear={year} />}
          />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
    <div className="method-callout"><b>How to read the estimate</b><p>{estimate?.interpretation} {estimate?.limitation}</p></div>
  </div>;
}
