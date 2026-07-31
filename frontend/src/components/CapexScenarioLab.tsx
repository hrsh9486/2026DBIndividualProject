import { useMemo, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { DatedPayload } from "../data/types";

type Assumptions = {
  capex: number;
  execution: number;
  multiplier: number;
  lag: number;
  crowdIn: number;
  overrun: number;
  borrowing: number;
  interest: number;
  growth: number;
  revenue: number;
};

const PRESETS: Record<string, Assumptions> = {
  Conservative: { capex: .5, execution: 75, multiplier: .6, lag: 2, crowdIn: -.1, overrun: 20, borrowing: 100, interest: 7.5, growth: 9, revenue: 12 },
  Central: { capex: .5, execution: 90, multiplier: 1, lag: 1, crowdIn: .15, overrun: 10, borrowing: 75, interest: 7, growth: 10, revenue: 15 },
  Optimistic: { capex: .5, execution: 100, multiplier: 1.5, lag: 0, crowdIn: .35, overrun: 5, borrowing: 50, interest: 6.5, growth: 11, revenue: 18 },
};

const CONTROLS: Array<{
  key: keyof Assumptions;
  label: string;
  min: number;
  max: number;
  step: number;
  suffix: string;
  help: string;
}> = [
  { key: "capex", label: "Additional annual CapEx", min: .1, max: 2, step: .1, suffix: "% GDP", help: "Sustained for five fiscal years." },
  { key: "execution", label: "Execution rate", min: 50, max: 100, step: 1, suffix: "%", help: "Share of the allocation that is spent." },
  { key: "multiplier", label: "Fiscal multiplier", min: .2, max: 2, step: .1, suffix: "×", help: "GDP generated per unit of effective investment." },
  { key: "lag", label: "Implementation lag", min: 0, max: 3, step: 1, suffix: " yrs", help: "Delay before the GDP effect begins." },
  { key: "crowdIn", label: "Private-investment response", min: -.3, max: .6, step: .05, suffix: "×", help: "Private investment induced per unit delivered; negative means crowding out." },
  { key: "overrun", label: "Cost overrun", min: 0, max: 40, step: 1, suffix: "%", help: "Reduces productive output from each rupee executed." },
  { key: "borrowing", label: "Borrowing-financed share", min: 0, max: 100, step: 5, suffix: "%", help: "Remainder is funded by reprioritisation or revenue." },
  { key: "interest", label: "Effective interest rate", min: 4, max: 10, step: .25, suffix: "%", help: "Nominal financing cost on incremental debt." },
  { key: "growth", label: "Nominal GDP growth", min: 5, max: 14, step: .5, suffix: "%", help: "Baseline denominator growth." },
  { key: "revenue", label: "Revenue feedback", min: 0, max: 30, step: 1, suffix: "%", help: "Share of additional GDP returned as government revenue." },
];

function latestSettled(payload: DatedPayload, key: string, fallback: number) {
  const values = payload.series[key]?.values.filter(
    (row) => typeof row.value === "number" && row.status !== "budget" && row.status !== "estimate",
  ) ?? [];
  const row = values.at(-1);
  return {
    value: Number(row?.value ?? fallback),
    period: row?.period_label ?? "latest non-budget observation",
  };
}

function formatSigned(value: number, suffix = "") {
  return `${value > 0 ? "+" : ""}${value.toFixed(2)}${suffix}`;
}

export default function CapexScenarioLab({ payload }: { payload: DatedPayload }) {
  const [assumptions, setAssumptions] = useState(PRESETS.Central);
  const [preset, setPreset] = useState("Central");
  const debtBaseline = latestSettled(payload, "general_government_debt_pct_gdp", 82);
  const startingDebt = debtBaseline.value;

  const result = useMemo(() => {
    const delivered = assumptions.capex * assumptions.execution / 100;
    const productive = delivered / (1 + assumptions.overrun / 100);
    const directImpact = productive * assumptions.multiplier;
    const privateImpact = productive * assumptions.crowdIn;
    const annualImpact = directImpact + privateImpact;
    let incrementalDebt = 0;
    let cumulativeGdp = 0;
    const rows = Array.from({ length: 6 }, (_, year) => {
      if (year > 0) {
        const benefit = year > assumptions.lag ? annualImpact : 0;
        cumulativeGdp += benefit;
        const revenueFeedback = benefit * assumptions.revenue / 100;
        const borrowing = assumptions.capex * assumptions.borrowing / 100;
        incrementalDebt = incrementalDebt * (1 + assumptions.interest / 100) / (1 + assumptions.growth / 100)
          + borrowing - revenueFeedback;
      }
      const denominatorEffect = cumulativeGdp / 100;
      const scenarioDebt = (startingDebt + incrementalDebt) / (1 + denominatorEffect);
      return {
        year: year === 0 ? "Start" : `Year ${year}`,
        baselineDebt: startingDebt,
        scenarioDebt,
        debtChange: scenarioDebt - startingDebt,
        cumulativeGdp,
      };
    });
    return {
      rows,
      delivered,
      annualImpact,
      cumulativeGdp,
      debtChange: rows.at(-1)?.debtChange ?? 0,
      gdpPerRupee: assumptions.capex > 0 ? cumulativeGdp / (assumptions.capex * 5) : 0,
    };
  }, [assumptions, startingDebt]);

  const verdict = result.debtChange <= 0
    ? "Growth feedback outweighs the incremental debt burden."
    : result.cumulativeGdp > assumptions.capex * 5
      ? "Output gains exceed the five-year CapEx impulse, but debt remains above baseline."
      : "The assumed transmission is too weak to offset the financing burden.";

  const update = (key: keyof Assumptions, value: number) => {
    setPreset("Custom");
    setAssumptions((current) => ({ ...current, [key]: value }));
  };

  return <div className="scenario-lab">
    <section className="scenario-controls">
      <header>
        <div><span>Assumption set</span><h3>Build a five-year CapEx scenario</h3></div>
        <div className="scenario-presets">
          {Object.entries(PRESETS).map(([name, values]) => <button
            key={name}
            className={preset === name ? "active" : ""}
            onClick={() => { setPreset(name); setAssumptions(values); }}
          >{name}</button>)}
        </div>
      </header>
      <div className="scenario-sliders">
        {CONTROLS.map((control) => <label key={control.key}>
          <span><b>{control.label}</b><output>{assumptions[control.key].toFixed(control.step < .1 ? 2 : control.step < 1 ? 1 : 0)}{control.suffix}</output></span>
          <input
            type="range"
            min={control.min}
            max={control.max}
            step={control.step}
            value={assumptions[control.key]}
            onChange={(event) => update(control.key, Number(event.target.value))}
          />
          <small>{control.help}</small>
        </label>)}
      </div>
    </section>

    <section className="scenario-results">
      <div className="scenario-verdict">
        <span>Model interpretation · {preset}</span>
        <h3>{verdict}</h3>
        <p>Starting general-government debt: {startingDebt.toFixed(1)}% of GDP ({debtBaseline.period}). Results are changes against a flat debt-ratio baseline, not forecasts.</p>
      </div>
      <div className="scenario-kpis">
        <article><span>Effective delivery</span><b>{result.delivered.toFixed(2)}%</b><small>of GDP each year</small></article>
        <article><span>Annual GDP effect</span><b>{formatSigned(result.annualImpact, "%")}</b><small>after the lag</small></article>
        <article><span>5-year GDP gain</span><b>{formatSigned(result.cumulativeGdp, "%")}</b><small>cumulative level effect</small></article>
        <article className={result.debtChange <= 0 ? "positive" : "negative"}><span>Year-5 debt change</span><b>{formatSigned(result.debtChange, "pp")}</b><small>versus baseline</small></article>
        <article><span>GDP per ₹1 CapEx</span><b>₹{result.gdpPerRupee.toFixed(2)}</b><small>within five years</small></article>
      </div>
      <div className="scenario-chart">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={result.rows} margin={{ top: 18, right: 26, bottom: 8, left: 8 }}>
            <CartesianGrid vertical={false} stroke="#ded9cf" strokeDasharray="2 5" />
            <XAxis dataKey="year" tickLine={false} />
            <YAxis tickFormatter={(value) => `${Number(value).toFixed(0)}%`} domain={["auto", "auto"]} width={52} />
            <Tooltip formatter={(value, name) => [`${Number(value).toFixed(2)}%`, name === "scenarioDebt" ? "Scenario debt/GDP" : "Baseline debt/GDP"]} />
            <Legend formatter={(name) => name === "scenarioDebt" ? "Scenario debt/GDP" : "Baseline debt/GDP"} />
            <ReferenceLine y={startingDebt} stroke="#928b80" strokeDasharray="4 4" />
            <Line dataKey="baselineDebt" stroke="#928b80" strokeWidth={1.5} dot={false} strokeDasharray="4 4" />
            <Line dataKey="scenarioDebt" stroke="#a53f2b" strokeWidth={2.8} dot={{ r: 3 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <details className="scenario-method">
        <summary>How the model works</summary>
        <p>Executed CapEx is discounted for cost overruns, then multiplied by the selected fiscal multiplier and private-investment response after the chosen lag. Borrowing adds to incremental debt; nominal growth dilutes it and the selected revenue-feedback rate offsets part of the cost. The model applies the same additional CapEx in each of five years.</p>
      </details>
    </section>
  </div>;
}
