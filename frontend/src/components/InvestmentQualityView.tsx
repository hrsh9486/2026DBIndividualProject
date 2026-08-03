import { useMemo, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
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

type QualityRow = {
  sector: string;
  year: number;
  date: string;
  projects_monitored: number | null;
  on_schedule_share: number | null;
  delayed_share: number | null;
  without_date_share: number | null;
  cost_overrun_pct: number | null;
};

const LABELS: Record<string, string> = {
  "all sectors": "All sectors",
  "surface transport": "Roads, shipping & ports",
  railways: "Railways",
  power: "Power",
  petroleum: "Petroleum",
  coal: "Coal",
};

const pretty = (value: string) => LABELS[value] ?? value.replaceAll("-", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());

export default function InvestmentQualityView({ payload }: { payload: DatedPayload }) {
  const quality = (payload.metadata.sector_quality as QualityRow[] | undefined) ?? [];
  const sectors = useMemo(() => [...new Set(quality.map((row) => row.sector))], [quality]);
  const [sector, setSector] = useState("all sectors");
  const [mode, setMode] = useState<"trend" | "map">("trend");
  const selected = quality.filter((row) => row.sector === sector);
  const latest = selected.at(-1);
  const latestYear = Math.max(...quality.map((row) => row.year));
  const sectorMap = quality.filter((row) => row.year === latestYear && row.delayed_share !== null && row.cost_overrun_pct !== null);

  return <div className="depth-view">
    <div className="depth-toolbar">
      <div>
        <span>Explore delivery quality</span>
        <select value={sector} onChange={(event) => setSector(event.target.value)} disabled={mode === "map"}>
          {sectors.map((value) => <option value={value} key={value}>{pretty(value)}</option>)}
        </select>
      </div>
      <div className="depth-tabs">
        <button className={mode === "trend" ? "active" : ""} onClick={() => setMode("trend")}>Trend</button>
        <button className={mode === "map" ? "active" : ""} onClick={() => setMode("map")}>Sector map</button>
      </div>
    </div>

    <div className="depth-kpis">
      <article><span>Projects monitored</span><b>{latest?.projects_monitored?.toLocaleString() ?? "—"}</b><small>{pretty(sector)} · {latest?.year ?? "—"}</small></article>
      <article><span>Ahead / on schedule</span><b>{latest?.on_schedule_share?.toFixed(1) ?? "—"}%</b><small>share of monitored projects</small></article>
      <article><span>Delayed</span><b>{latest?.delayed_share?.toFixed(1) ?? "—"}%</b><small>share of monitored projects</small></article>
      <article><span>Cost overrun</span><b>{latest?.cost_overrun_pct?.toFixed(1) ?? "—"}%</b><small>of original delayed-project cost</small></article>
    </div>

    <div className="depth-chart">
      <ResponsiveContainer width="100%" height="100%">
        {mode === "trend" ? <LineChart data={selected} margin={{ top: 18, right: 24, bottom: 8, left: 4 }}>
          <CartesianGrid vertical={false} stroke="#ded9cf" strokeDasharray="2 5" />
          <XAxis dataKey="year" tickLine={false} />
          <YAxis domain={[0, "auto"]} tickFormatter={(value) => `${value}%`} width={48} />
          <Tooltip formatter={(value, name) => [`${Number(value).toFixed(1)}%`, name === "on_schedule_share" ? "Ahead / on schedule" : name === "delayed_share" ? "Delayed" : "Cost overrun"]} labelFormatter={(value) => `End-March ${value}`} />
          <Legend formatter={(name) => name === "on_schedule_share" ? "Ahead / on schedule" : name === "delayed_share" ? "Delayed" : "Cost overrun"} />
          <ReferenceLine x={2011} stroke="#817a70" strokeDasharray="4 4" label={{ value: "Coverage break", fill: "#817a70", fontSize: 10 }} />
          <Line type="monotone" dataKey="on_schedule_share" stroke="#386641" strokeWidth={2.4} dot={false} connectNulls />
          <Line type="monotone" dataKey="delayed_share" stroke="#a53f2b" strokeWidth={2.4} dot={false} connectNulls />
          <Line type="monotone" dataKey="cost_overrun_pct" stroke="#31566f" strokeWidth={2.4} dot={false} connectNulls />
        </LineChart> : <ScatterChart margin={{ top: 18, right: 26, bottom: 18, left: 10 }}>
          <CartesianGrid stroke="#ded9cf" strokeDasharray="2 5" />
          <XAxis type="number" dataKey="delayed_share" name="Delayed share" unit="%" label={{ value: "Delayed projects (%)", position: "insideBottom", offset: -10 }} />
          <YAxis type="number" dataKey="cost_overrun_pct" name="Cost overrun" unit="%" width={60} label={{ value: "Cost overrun (%)", angle: -90, position: "insideLeft" }} />
          <ZAxis type="number" dataKey="projects_monitored" range={[55, 440]} />
          <Tooltip cursor={{ strokeDasharray: "3 3" }} formatter={(value, name) => [name === "Projects monitored" ? Number(value).toFixed(0) : `${Number(value).toFixed(1)}%`, name]} labelFormatter={(_, items) => pretty(String(items?.[0]?.payload?.sector ?? ""))} />
          <Scatter data={sectorMap} fill="#a53f2b" name={`Sectors · ${latestYear}`} />
        </ScatterChart>}
      </ResponsiveContainer>
    </div>
    <p className="depth-footnote">{String(payload.metadata.break_note ?? "")} Bubble size in the sector map represents monitored projects. A high delay or overrun share is a delivery warning, not proof that completed assets have low social value.</p>
  </div>;
}
