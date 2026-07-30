import { useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { DatedPayload } from "../data/types";

const METRICS = [
  ["revenue_growth", "Revenue growth"],
  ["ebitda_growth", "EBITDA growth"],
  ["capex_growth", "Company CapEx growth"],
  ["net_ppe_growth", "Net PPE growth"],
  ["roce_proxy", "ROCE proxy"],
  ["debt_growth", "Debt growth"],
] as const;

type Coverage = {
  company_key: string;
  company: string;
  group: "capital_goods" | "infrastructure";
  start_year: number;
  end_year: number;
  observations: number;
};

export default function CorporateFundamentalsView({ payload }: { payload: DatedPayload }) {
  const [metric, setMetric] = useState<(typeof METRICS)[number][0]>("revenue_growth");
  const rows = useMemo(() => {
    const byDate = new Map<string, Record<string, string | number>>();
    for (const group of ["capital_goods", "infrastructure"] as const) {
      for (const point of payload.series[`${group}_${metric}`]?.values ?? []) {
        if (typeof point.value !== "number") continue;
        const row = byDate.get(point.date) ?? { date: point.period_label ?? point.date };
        row[group] = point.value;
        byDate.set(point.date, row);
      }
    }
    return [...byDate.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([, row]) => row);
  }, [metric, payload.series]);
  const coverage = (payload.metadata.company_coverage ?? []) as Coverage[];

  return <div className="corporate-fundamentals-view">
    <div className="corporate-metric-tabs">
      {METRICS.map(([key, label]) => <button
        key={key}
        className={metric === key ? "active" : ""}
        onClick={() => setMetric(key)}
      >{label}</button>)}
    </div>
    <div className="corporate-bar-wrap">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} margin={{ top: 14, right: 18, bottom: 8, left: 0 }}>
          <CartesianGrid vertical={false} stroke="#ded9cf" strokeDasharray="2 5" />
          <XAxis dataKey="date" tick={{ fontSize: 11 }} />
          <YAxis width={60} tick={{ fontSize: 11 }} tickFormatter={(value) => `${Number(value).toFixed(0)}%`} />
          <ReferenceLine y={0} stroke="#8e887e" />
          <Tooltip formatter={(value) => `${Number(value).toFixed(1)}%`} />
          <Legend />
          <Bar dataKey="capital_goods" name="Capital-goods group median" fill="#d45132" />
          <Bar dataKey="infrastructure" name="Infrastructure group median" fill="#176b87" />
        </BarChart>
      </ResponsiveContainer>
    </div>
    <section className="company-basket">
      <header><span>Frozen case-study basket</span><h4>Company coverage</h4></header>
      <div className="company-basket-grid">
        {(["capital_goods", "infrastructure"] as const).map((group) => <div key={group}>
          <b>{group === "capital_goods" ? "Capital goods" : "Infrastructure"}</b>
          {coverage.filter((item) => item.group === group).map((item) => <p key={item.company_key}>
            <span>{item.company}</span><small>{item.start_year}–{item.end_year} · {item.observations} statements</small>
          </p>)}
        </div>)}
      </div>
    </section>
    <p className="metric-note">Growth rates are calculated within each company before taking the unweighted group median. This reduces domination by the largest firm but does not correct accounting differences.</p>
  </div>;
}
