import { useMemo, useState } from "react";
import {
  Bar,
  BarChart,
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
  primaryBalance: number;
  uncertainty: number;
};

type Projection = ReturnType<typeof project>;
type LabView = "projection" | "risk" | "sensitivity" | "frontier" | "backtest";

const PRESETS: Record<string, Assumptions> = {
  Conservative: { capex: .5, execution: 75, multiplier: .6, lag: 2, crowdIn: -.1, overrun: 20, borrowing: 100, interest: 7.5, growth: 9, revenue: 12, primaryBalance: -3, uncertainty: 100 },
  Central: { capex: .5, execution: 90, multiplier: 1, lag: 1, crowdIn: .15, overrun: 10, borrowing: 75, interest: 7, growth: 10, revenue: 15, primaryBalance: -2, uncertainty: 100 },
  Optimistic: { capex: .5, execution: 100, multiplier: 1.5, lag: 0, crowdIn: .35, overrun: 5, borrowing: 50, interest: 6.5, growth: 11, revenue: 18, primaryBalance: -1, uncertainty: 100 },
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
  { key: "multiplier", label: "Fiscal multiplier", min: .2, max: 2, step: .1, suffix: "×", help: "GDP generated per unit of productive investment." },
  { key: "lag", label: "Implementation lag", min: 0, max: 3, step: 1, suffix: " yrs", help: "Delay before the GDP effect begins." },
  { key: "crowdIn", label: "Private-investment response", min: -.3, max: .6, step: .05, suffix: "×", help: "Private investment induced per unit delivered; negative means crowding out." },
  { key: "overrun", label: "Cost overrun", min: 0, max: 40, step: 1, suffix: "%", help: "Reduces productive output from each rupee executed." },
  { key: "borrowing", label: "Borrowing-financed share", min: 0, max: 100, step: 5, suffix: "%", help: "Applied to executed, not announced, CapEx." },
  { key: "interest", label: "Effective interest rate", min: 4, max: 10, step: .25, suffix: "%", help: "Nominal financing cost in the debt equation." },
  { key: "growth", label: "Nominal GDP growth", min: 5, max: 14, step: .5, suffix: "%", help: "Baseline denominator growth." },
  { key: "primaryBalance", label: "Baseline primary balance", min: -8, max: 4, step: .25, suffix: "% GDP", help: "A deficit is negative; a surplus lowers debt." },
  { key: "revenue", label: "Revenue feedback", min: 0, max: 30, step: 1, suffix: "%", help: "Share of additional GDP returned as revenue." },
  { key: "uncertainty", label: "Uncertainty range", min: 0, max: 150, step: 10, suffix: "%", help: "Scales the registered Monte Carlo ranges." },
];

const RANGES: Partial<Record<keyof Assumptions, number>> = {
  capex: .2, execution: 10, multiplier: .35, crowdIn: .2, overrun: 8,
  borrowing: 20, interest: 1, growth: 1.5, revenue: 5, primaryBalance: 1,
};

function latestSettled(payload: DatedPayload, key: string, fallback: number) {
  const values = payload.series[key]?.values.filter(
    (row) => typeof row.value === "number" && row.status !== "budget" && row.status !== "estimate",
  ) ?? [];
  const row = values.at(-1);
  return { value: Number(row?.value ?? fallback), period: row?.period_label ?? "latest non-budget observation" };
}

function project(a: Assumptions, startingDebt: number) {
  const delivered = a.capex * a.execution / 100;
  const productive = delivered / (1 + a.overrun / 100);
  const annualImpact = productive * (a.multiplier + a.crowdIn);
  let baselineDebt = startingDebt;
  let incrementalDebt = 0;
  let cumulativeGdp = 0;
  const rows = Array.from({ length: 6 }, (_, year) => {
    if (year > 0) {
      baselineDebt = baselineDebt * (1 + a.interest / 100) / (1 + a.growth / 100) - a.primaryBalance;
      const benefit = year > a.lag ? annualImpact : 0;
      cumulativeGdp += benefit;
      incrementalDebt = incrementalDebt * (1 + a.interest / 100) / (1 + a.growth / 100)
        + delivered * a.borrowing / 100 - benefit * a.revenue / 100;
    }
    const scenarioDebt = (baselineDebt + incrementalDebt) / (1 + cumulativeGdp / 100);
    return {
      year: year === 0 ? "Start" : `Year ${year}`,
      baselineDebt,
      scenarioDebt,
      debtChange: scenarioDebt - baselineDebt,
      cumulativeGdp,
    };
  });
  return {
    rows,
    delivered,
    annualImpact,
    cumulativeGdp,
    debtChange: rows.at(-1)?.debtChange ?? 0,
    gdpPerRupee: a.capex > 0 ? cumulativeGdp / (a.capex * 5) : 0,
  };
}

function random(seed: number) {
  let value = seed >>> 0;
  return () => {
    value += 0x6D2B79F5;
    let result = value;
    result = Math.imul(result ^ result >>> 15, result | 1);
    result ^= result + Math.imul(result ^ result >>> 7, result | 61);
    return ((result ^ result >>> 14) >>> 0) / 4294967296;
  };
}

function percentile(values: number[], probability: number) {
  const ordered = [...values].sort((a, b) => a - b);
  const index = Math.min(ordered.length - 1, Math.max(0, Math.round((ordered.length - 1) * probability)));
  return ordered[index];
}

function clamp(key: keyof Assumptions, value: number) {
  const control = CONTROLS.find((item) => item.key === key);
  return control ? Math.min(control.max, Math.max(control.min, value)) : value;
}

function simulate(a: Assumptions, startingDebt: number, draws = 1200) {
  const rng = random(20260803);
  const projections: Projection[] = [];
  for (let draw = 0; draw < draws; draw += 1) {
    const sampled = { ...a };
    for (const [key, range] of Object.entries(RANGES) as Array<[keyof Assumptions, number]>) {
      const centred = (rng() + rng() + rng() - 1.5) / 1.5;
      sampled[key] = clamp(key, a[key] + centred * range * a.uncertainty / 100);
    }
    projections.push(project(sampled, startingDebt));
  }
  const rows = Array.from({ length: 6 }, (_, year) => {
    const values = projections.map((item) => item.rows[year].scenarioDebt);
    return { year: year === 0 ? "Start" : `Year ${year}`, p10: percentile(values, .1), p50: percentile(values, .5), p90: percentile(values, .9) };
  });
  const final = projections.map((item) => item.debtChange);
  return {
    rows,
    lowerDebtProbability: final.filter((value) => value <= 0).length / final.length * 100,
    productiveProbability: projections.filter((item) => item.gdpPerRupee >= 1).length / projections.length * 100,
    finalP10: percentile(final, .1), finalP50: percentile(final, .5), finalP90: percentile(final, .9),
  };
}

function breakEvenMultiplier(a: Assumptions, startingDebt: number) {
  let low = 0;
  let high = 5;
  if (project({ ...a, multiplier: high }, startingDebt).debtChange > 0) return null;
  for (let iteration = 0; iteration < 50; iteration += 1) {
    const middle = (low + high) / 2;
    if (project({ ...a, multiplier: middle }, startingDebt).debtChange <= 0) high = middle;
    else low = middle;
  }
  return high;
}

function backtest(payload: DatedPayload, a: Assumptions) {
  const debt = payload.series.general_government_debt_pct_gdp?.values.filter((row) => typeof row.value === "number" && row.status !== "budget" && row.status !== "estimate") ?? [];
  const primary = new Map((payload.series.primary_balance_pct_gdp?.values ?? []).filter((row) => typeof row.value === "number").map((row) => [row.date, Number(row.value)]));
  const rows = [];
  for (let index = 1; index < debt.length; index += 1) {
    const current = debt[index];
    const previous = debt[index - 1];
    const balance = primary.get(current.date);
    if (balance === undefined || current.value === null || previous.value === null) continue;
    const predicted = previous.value * (1 + a.interest / 100) / (1 + a.growth / 100) - balance;
    rows.push({ year: current.period_label ?? current.date.slice(0, 4), actual: current.value, predicted, error: predicted - current.value });
  }
  const recent = rows.slice(-10);
  return {
    rows: recent,
    mae: recent.length ? recent.reduce((sum, row) => sum + Math.abs(row.error), 0) / recent.length : 0,
    rmse: recent.length ? Math.sqrt(recent.reduce((sum, row) => sum + row.error ** 2, 0) / recent.length) : 0,
  };
}

function formatSigned(value: number, suffix = "") { return `${value > 0 ? "+" : ""}${value.toFixed(2)}${suffix}`; }

export default function CapexScenarioLab({ payload }: { payload: DatedPayload }) {
  const debtBaseline = latestSettled(payload, "general_government_debt_pct_gdp", 82);
  const primaryObserved = latestSettled(payload, "primary_balance_pct_gdp", -2);
  const [assumptions, setAssumptions] = useState(() => ({ ...PRESETS.Central, primaryBalance: primaryObserved.value }));
  const [preset, setPreset] = useState("Latest fiscal");
  const [view, setView] = useState<LabView>("projection");
  const startingDebt = debtBaseline.value;
  const result = useMemo(() => project(assumptions, startingDebt), [assumptions, startingDebt]);
  const risk = useMemo(() => simulate(assumptions, startingDebt), [assumptions, startingDebt]);
  const breakEven = useMemo(() => breakEvenMultiplier(assumptions, startingDebt), [assumptions, startingDebt]);
  const historical = useMemo(() => backtest(payload, assumptions), [payload, assumptions]);
  const sensitivity = useMemo(() => Object.entries(RANGES).map(([rawKey, range]) => {
    const key = rawKey as keyof Assumptions;
    const label = CONTROLS.find((item) => item.key === key)?.label ?? key;
    const scaledRange = range * assumptions.uncertainty / 100;
    const low = project({ ...assumptions, [key]: clamp(key, assumptions[key] - scaledRange) }, startingDebt).debtChange;
    const high = project({ ...assumptions, [key]: clamp(key, assumptions[key] + scaledRange) }, startingDebt).debtChange;
    return { parameter: label, low: low - result.debtChange, high: high - result.debtChange };
  }).sort((a, b) => Math.max(Math.abs(b.low), Math.abs(b.high)) - Math.max(Math.abs(a.low), Math.abs(a.high))), [assumptions, result.debtChange, startingDebt]);

  const verdict = result.debtChange <= 0
    ? "Growth and revenue feedback lower debt/GDP relative to the dynamic baseline."
    : result.gdpPerRupee > 1
      ? "Output gains exceed the CapEx impulse, but financing still raises debt/GDP."
      : "The assumed transmission is too weak to compensate for its financing burden.";
  const update = (key: keyof Assumptions, value: number) => { setPreset("Custom"); setAssumptions((current) => ({ ...current, [key]: value })); };
  const frontierCapex = [.25, .5, .75, 1, 1.25, 1.5];
  const frontierMultiplier = [.4, .7, 1, 1.3, 1.6, 1.9];

  return <div className="scenario-lab">
    <section className="scenario-controls">
      <header>
        <div><span>Assumption set</span><h3>Build a five-year CapEx scenario</h3></div>
        <div className="scenario-presets"><button className={preset === "Latest fiscal" ? "active" : ""} onClick={() => { setPreset("Latest fiscal"); setAssumptions({ ...PRESETS.Central, primaryBalance: primaryObserved.value }); }}>Latest fiscal</button>{Object.entries(PRESETS).map(([name, values]) => <button key={name} className={preset === name ? "active" : ""} onClick={() => { setPreset(name); setAssumptions(values); }}>{name}</button>)}</div>
      </header>
      <div className="scenario-sliders">{CONTROLS.map((control) => <label key={control.key}>
        <span><b>{control.label}</b><output>{assumptions[control.key].toFixed(control.step < .1 ? 2 : control.step < 1 ? 1 : 0)}{control.suffix}</output></span>
        <input type="range" min={control.min} max={control.max} step={control.step} value={assumptions[control.key]} onChange={(event) => update(control.key, Number(event.target.value))} />
        <small>{control.help}</small>
      </label>)}</div>
    </section>

    <section className="scenario-results">
      <div className="scenario-verdict"><span>Model interpretation · {preset}</span><h3>{verdict}</h3><p>Start: {startingDebt.toFixed(1)}% debt/GDP ({debtBaseline.period}). The baseline now rolls forward using debt dynamics: prior debt × (1+r)/(1+g) − primary balance. Latest observed primary balance: {primaryObserved.value.toFixed(1)}% ({primaryObserved.period}).</p></div>
      <div className="scenario-view-tabs">{(["projection", "risk", "sensitivity", "frontier", "backtest"] as LabView[]).map((item) => <button key={item} className={view === item ? "active" : ""} onClick={() => setView(item)}>{item === "risk" ? "Uncertainty" : item[0].toUpperCase() + item.slice(1)}</button>)}</div>
      <div className="scenario-kpis">
        <article><span>Effective delivery</span><b>{result.delivered.toFixed(2)}%</b><small>of GDP each year</small></article>
        <article><span>5-year GDP gain</span><b>{formatSigned(result.cumulativeGdp, "%")}</b><small>cumulative level effect</small></article>
        <article className={result.debtChange <= 0 ? "positive" : "negative"}><span>Year-5 debt change</span><b>{formatSigned(result.debtChange, "pp")}</b><small>versus dynamic baseline</small></article>
        <article><span>Break-even multiplier</span><b>{breakEven === null ? ">5.00×" : `${breakEven.toFixed(2)}×`}</b><small>holding other assumptions fixed</small></article>
        <article><span>Debt improvement odds</span><b>{risk.lowerDebtProbability.toFixed(0)}%</b><small>1,200 seeded draws</small></article>
      </div>

      {view === "frontier" ? <div className="frontier-wrap">
        <div className="frontier-heading"><b>Year-5 debt change frontier</b><span>Click a cell to apply its CapEx and multiplier</span></div>
        <div className="frontier-grid" style={{ gridTemplateColumns: `90px repeat(${frontierMultiplier.length}, minmax(58px, 1fr))` }}>
          <span>CapEx ↓ / multiplier →</span>{frontierMultiplier.map((value) => <b key={value}>{value.toFixed(1)}×</b>)}
          {frontierCapex.flatMap((capex) => [<b key={`${capex}-label`}>{capex.toFixed(2)}%</b>, ...frontierMultiplier.map((multiplier) => {
            const debtChange = project({ ...assumptions, capex, multiplier }, startingDebt).debtChange;
            return <button key={`${capex}-${multiplier}`} className={debtChange <= 0 ? "sustainable" : "unsustainable"} style={{ opacity: Math.min(1, .45 + Math.abs(debtChange) / 4) }} onClick={() => { setPreset("Custom"); setAssumptions((current) => ({ ...current, capex, multiplier })); }}>{formatSigned(debtChange, "pp")}</button>;
          })])}
        </div>
      </div> : <div className="scenario-chart"><ResponsiveContainer width="100%" height="100%">
        {view === "projection" ? <LineChart data={result.rows} margin={{ top: 18, right: 26, bottom: 8, left: 8 }}>
          <CartesianGrid vertical={false} stroke="#ded9cf" strokeDasharray="2 5" /><XAxis dataKey="year" tickLine={false} /><YAxis tickFormatter={(value) => `${Number(value).toFixed(0)}%`} domain={["auto", "auto"]} width={52} />
          <Tooltip formatter={(value, name) => [`${Number(value).toFixed(2)}%`, name === "scenarioDebt" ? "Scenario debt/GDP" : "Dynamic baseline debt/GDP"]} /><Legend formatter={(name) => name === "scenarioDebt" ? "Scenario debt/GDP" : "Dynamic baseline debt/GDP"} />
          <Line dataKey="baselineDebt" stroke="#928b80" strokeWidth={1.5} dot={false} strokeDasharray="4 4" /><Line dataKey="scenarioDebt" stroke="#a53f2b" strokeWidth={2.8} dot={{ r: 3 }} />
        </LineChart> : view === "risk" ? <LineChart data={risk.rows} margin={{ top: 18, right: 26, bottom: 8, left: 8 }}>
          <CartesianGrid vertical={false} stroke="#ded9cf" strokeDasharray="2 5" /><XAxis dataKey="year" tickLine={false} /><YAxis tickFormatter={(value) => `${Number(value).toFixed(0)}%`} domain={["auto", "auto"]} width={52} />
          <Tooltip formatter={(value, name) => [`${Number(value).toFixed(2)}%`, String(name).toUpperCase()]} /><Legend formatter={(name) => String(name).toUpperCase()} />
          <Line dataKey="p10" stroke="#9eb2b7" dot={false} strokeDasharray="4 4" /><Line dataKey="p50" stroke="#a53f2b" strokeWidth={2.8} dot={false} /><Line dataKey="p90" stroke="#9eb2b7" dot={false} strokeDasharray="4 4" />
        </LineChart> : view === "sensitivity" ? <BarChart data={sensitivity} layout="vertical" margin={{ top: 8, right: 28, bottom: 16, left: 150 }}>
          <CartesianGrid horizontal={false} stroke="#ded9cf" strokeDasharray="2 5" /><XAxis type="number" tickFormatter={(value) => `${Number(value).toFixed(1)}pp`} /><YAxis type="category" dataKey="parameter" width={145} tick={{ fontSize: 10 }} /><ReferenceLine x={0} stroke="#30393b" />
          <Tooltip formatter={(value, name) => [`${Number(value).toFixed(2)}pp`, name === "low" ? "Low assumption" : "High assumption"]} /><Legend formatter={(name) => name === "low" ? "Low assumption" : "High assumption"} /><Bar dataKey="low" fill="#31566f" /><Bar dataKey="high" fill="#a53f2b" />
        </BarChart> : <LineChart data={historical.rows} margin={{ top: 18, right: 26, bottom: 8, left: 8 }}>
          <CartesianGrid vertical={false} stroke="#ded9cf" strokeDasharray="2 5" /><XAxis dataKey="year" tickLine={false} /><YAxis tickFormatter={(value) => `${Number(value).toFixed(0)}%`} domain={["auto", "auto"]} width={52} />
          <Tooltip formatter={(value, name) => [`${Number(value).toFixed(2)}%`, name === "actual" ? "Observed debt/GDP" : "One-year model prediction"]} /><Legend formatter={(name) => name === "actual" ? "Observed debt/GDP" : "One-year prediction"} />
          <Line dataKey="actual" stroke="#30393b" strokeWidth={2.4} /><Line dataKey="predicted" stroke="#a53f2b" strokeWidth={2.2} strokeDasharray="4 3" />
        </LineChart>}
      </ResponsiveContainer></div>}
      {view === "risk" && <p className="scenario-inline-note">Year-5 debt change: P10 {formatSigned(risk.finalP10, "pp")}, median {formatSigned(risk.finalP50, "pp")}, P90 {formatSigned(risk.finalP90, "pp")}. Probability GDP per ₹1 CapEx reaches ₹1: {risk.productiveProbability.toFixed(0)}%.</p>}
      {view === "backtest" && <p className="scenario-inline-note">Last {historical.rows.length} aligned one-year observations: MAE {historical.mae.toFixed(2)}pp; RMSE {historical.rmse.toFixed(2)}pp. Residuals include stock-flow adjustments, denominator revisions and the use of fixed r and g assumptions.</p>}
      <details className="scenario-method"><summary>Model contract and limitations</summary><p>Executed CapEx is discounted for overruns, then multiplied by the fiscal multiplier and private response after the selected lag. The fiscal baseline is dynamic, not flat. Monte Carlo draws use a fixed seed and registered symmetric ranges, so identical assumptions reproduce identical results. The frontier solves debt arithmetic under assumptions; it is neither a forecast nor a causal estimate.</p></details>
    </section>
  </div>;
}
