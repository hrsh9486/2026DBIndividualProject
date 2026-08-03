import { useMemo, useState } from "react";
import {
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { DatedPayload } from "../data/types";

type LagEstimate = {
  key: string;
  outcome_key: string;
  label: string;
  role: string;
  lag: number;
  n: number;
  pearson: number | null;
  spearman: number | null;
  eligible: boolean;
  required_observations: number;
};
type PairRow = { estimate_key: string; date: string; capex_growth: number; outcome: number };

export default function CrowdingInView({ payload }: { payload: DatedPayload }) {
  const estimates = (payload.metadata.lag_estimates as LagEstimate[] | undefined) ?? [];
  const pairs = (payload.metadata.pair_observations as PairRow[] | undefined) ?? [];
  const outcomes = useMemo(() => [...new Map(estimates.map((item) => [item.outcome_key, item.label])).entries()], [estimates]);
  const [outcome, setOutcome] = useState(outcomes[0]?.[0] ?? "private_gfcf");
  const [lag, setLag] = useState(0);
  const estimate = estimates.find((item) => item.outcome_key === outcome && item.lag === lag);
  const selected = pairs.filter((row) => row.estimate_key === estimate?.key);
  const label = outcomes.find(([key]) => key === outcome)?.[1] ?? "Outcome";
  const line = useMemo(() => {
    if (selected.length < 2) return [];
    const meanX = selected.reduce((sum, row) => sum + row.capex_growth, 0) / selected.length;
    const meanY = selected.reduce((sum, row) => sum + row.outcome, 0) / selected.length;
    const variance = selected.reduce((sum, row) => sum + (row.capex_growth - meanX) ** 2, 0);
    const slope = variance ? selected.reduce((sum, row) => sum + (row.capex_growth - meanX) * (row.outcome - meanY), 0) / variance : 0;
    const min = Math.min(...selected.map((row) => row.capex_growth));
    const max = Math.max(...selected.map((row) => row.capex_growth));
    return [{ capex_growth: min, outcome: meanY + slope * (min - meanX) }, { capex_growth: max, outcome: meanY + slope * (max - meanX) }];
  }, [selected]);

  return <div className="depth-view">
    <div className="depth-toolbar crowd-toolbar">
      <div><span>Outcome</span><select value={outcome} onChange={(event) => setOutcome(event.target.value)}>{outcomes.map(([key, value]) => <option value={key} key={key}>{value}</option>)}</select></div>
      <div className="lag-buttons"><span>CapEx leads by</span>{[0, 1, 2, 3].map((value) => <button key={value} className={lag === value ? "active" : ""} onClick={() => setLag(value)}>{value}y</button>)}</div>
    </div>
    <div className="depth-kpis">
      <article><span>Pearson</span><b>{estimate?.pearson?.toFixed(2) ?? "—"}</b><small>linear association</small></article>
      <article><span>Spearman</span><b>{estimate?.spearman?.toFixed(2) ?? "—"}</b><small>rank association</small></article>
      <article><span>Aligned observations</span><b>{estimate?.n ?? 0}/{estimate?.required_observations ?? 8}</b><small>available / registered minimum</small></article>
      <article className={estimate?.eligible ? "positive" : "negative"}><span>Inference status</span><b>{estimate?.eligible ? "Associational" : "Insufficient"}</b><small>{estimate?.eligible ? "still not causal" : "coefficient is descriptive only"}</small></article>
    </div>
    <div className="depth-chart">
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart margin={{ top: 18, right: 24, bottom: 18, left: 10 }}>
          <CartesianGrid stroke="#ded9cf" strokeDasharray="2 5" />
          <XAxis type="number" dataKey="capex_growth" name="Nominal CapEx growth" unit="%" label={{ value: "Actual nominal CapEx growth (%)", position: "insideBottom", offset: -10 }} />
          <YAxis type="number" dataKey="outcome" name={label} width={62} />
          <ReferenceLine x={0} stroke="#928b80" />
          <Tooltip cursor={{ strokeDasharray: "3 3" }} formatter={(value, name) => [`${Number(value).toFixed(2)}%`, name]} labelFormatter={(_, items) => items?.[0]?.payload?.date?.slice(0, 4) ?? ""} />
          <Scatter data={selected} fill="#a53f2b" name={label} />
          <Scatter data={line} fill="transparent" line={{ stroke: "#31566f", strokeWidth: 2 }} shape={() => <g />} name="Best fit" legendType="line" />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
    <div className="method-callout"><b>Why the gate matters</b><p>{estimate?.role}. A large coefficient based on three observations is not stronger evidence. The explorer therefore shows every registered lag but withholds an inference until at least eight aligned annual observations exist.</p></div>
  </div>;
}
