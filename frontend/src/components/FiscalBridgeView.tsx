import { useMemo } from "react";
import {
  CartesianGrid,
  Cell,
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
import type { DatedPayload, DatedValue } from "../data/types";

type EvidenceItem = {
  key: string;
  status: "supported" | "partially_supported" | "unsupported" | "inconclusive";
  interpretation: string;
};

const EVIDENCE_LABELS: Record<string, string> = {
  capex_intensity: "Policy effort",
  sector_transmission: "Market transmission",
  real_economy_conversion: "Real-economy conversion",
  fiscal_sustainability: "Fiscal pressure",
};

const STATUS_LABELS: Record<EvidenceItem["status"], string> = {
  supported: "Strong evidence",
  partially_supported: "Partial evidence",
  unsupported: "Little evidence",
  inconclusive: "Inconclusive",
};

function valuesByDate(values: DatedValue[]) {
  return new Map(values.filter((row) => typeof row.value === "number").map((row) => [row.date, row]));
}

function median(values: number[]) {
  const sorted = [...values].sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2;
}

function debtColour(debt: number | null, minimum: number, maximum: number) {
  if (debt === null || maximum === minimum) return "#8b918e";
  const intensity = (debt - minimum) / (maximum - minimum);
  return `rgb(${Math.round(62 + intensity * 145)}, ${Math.round(119 - intensity * 45)}, ${Math.round(112 - intensity * 55)})`;
}

export default function FiscalBridgeView({ payload }: { payload: DatedPayload }) {
  const points = useMemo(() => {
    const capex = valuesByDate(payload.series.actual_capex_pct_expenditure?.values ?? []);
    const interest = valuesByDate(payload.series.interest_payments_pct_expenditure?.values ?? []);
    const debt = valuesByDate(payload.series.general_government_debt_pct_gdp?.values ?? []);
    return [...capex.entries()].flatMap(([date, capexRow]) => {
      const interestRow = interest.get(date);
      if (typeof capexRow.value !== "number" || typeof interestRow?.value !== "number") return [];
      const debtValue = debt.get(date)?.value;
      return [{
        capex: capexRow.value,
        interest: interestRow.value,
        debt: typeof debtValue === "number" ? debtValue : null,
        period: capexRow.period_label ?? date,
      }];
    });
  }, [payload.series]);
  const capexMedian = median(points.map((point) => point.capex));
  const interestMedian = median(points.map((point) => point.interest));
  const debts = points.flatMap((point) => point.debt === null ? [] : [point.debt]);
  const debtMinimum = debts.length ? Math.min(...debts) : 0;
  const debtMaximum = debts.length ? Math.max(...debts) : 0;
  const ratios = payload.series.capex_to_interest_allocation_ratio?.values
    .filter((row) => typeof row.value === "number") ?? [];
  const latestRatio = ratios.at(-1);
  const evidence = (payload.metadata.transmission_evidence ?? []) as EvidenceItem[];

  return <div className="fiscal-bridge-view">
    <section className="fiscal-bridge-summary">
      <div>
        <span>Latest allocation ratio</span>
        <b>{typeof latestRatio?.value === "number" ? latestRatio.value.toFixed(2) : "—"}</b>
        <p>₹ of CapEx per ₹1 represented by interest expenditure</p>
        <small>{latestRatio?.period_label}</small>
      </div>
      <div className="fiscal-evidence-chain">
        {evidence.map((item) => <article key={item.key}>
          <span>{EVIDENCE_LABELS[item.key] ?? item.key}</span>
          <b className={item.status}>{STATUS_LABELS[item.status]}</b>
        </article>)}
      </div>
    </section>
    <section className="fiscal-quadrant">
      <header>
        <div><span>Fiscal allocation map</span><h3>Productive spending versus debt-service pressure</h3></div>
        <p>Dot colour darkens as general-government debt/GDP rises.</p>
      </header>
      <div className="fiscal-scatter-wrap">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 22, right: 34, bottom: 28, left: 10 }}>
            <CartesianGrid stroke="#ded9cf" strokeDasharray="2 5" />
            <XAxis type="number" dataKey="capex" unit="%" tick={{ fontSize: 11 }} label={{ value: "Actual CapEx share of expenditure", position: "bottom", offset: 10 }} />
            <YAxis type="number" dataKey="interest" unit="%" width={66} tick={{ fontSize: 11 }} label={{ value: "Interest share", angle: -90, position: "insideLeft" }} />
            <ZAxis range={[80, 80]} />
            <ReferenceLine x={capexMedian} stroke="#8d877e" strokeDasharray="4 4" label={{ value: "CapEx median", fontSize: 10 }} />
            <ReferenceLine y={interestMedian} stroke="#8d877e" strokeDasharray="4 4" label={{ value: "Interest median", fontSize: 10 }} />
            <Tooltip
              cursor={{ strokeDasharray: "3 3" }}
              formatter={(value, name) => [`${Number(value).toFixed(1)}%`, name]}
            />
            <Scatter data={points}>
              {points.map((point) => <Cell key={point.period} fill={debtColour(point.debt, debtMinimum, debtMaximum)} />)}
              <LabelList dataKey="period" position="top" fontSize={10} fill="#554f47" />
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
      </div>
      <div className="quadrant-key">
        <span><b>High CapEx · low interest</b> strongest allocation position</span>
        <span><b>High CapEx · high interest</b> investment with servicing pressure</span>
        <span><b>Low CapEx · low interest</b> fiscal room, less investment</span>
        <span><b>Low CapEx · high interest</b> greatest crowding-out pressure</span>
      </div>
      <p className="metric-note">The median lines describe this sample only. Debt sustainability also depends on growth, borrowing costs, maturity, inflation and expenditure quality.</p>
    </section>
  </div>;
}
