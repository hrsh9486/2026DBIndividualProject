import { lazy, Suspense, useState } from "react";
import type { Indicator, StaticDataAsset } from "../data/types";
import { useIndicatorData } from "../hooks/useIndicatorData";
import { assertAdapterMatchesSchema } from "../data/runtimeGuards";
import ChartView from "./ChartView";
import DataStatusBadge from "./DataStatusBadge";
import InsightRail from "./InsightRail";
import SourcePanel from "./SourcePanel";
import { ErrorPanel, LoadingPanel, PlannedPanel } from "./StatePanel";

const CapexCorrelationView = lazy(() => import("./CapexCorrelationView"));
const CorporateFundamentalsView = lazy(() => import("./CorporateFundamentalsView"));
const FiscalBridgeView = lazy(() => import("./FiscalBridgeView"));
const CapexScenarioLab = lazy(() => import("./CapexScenarioLab"));
const InvestmentQualityView = lazy(() => import("./InvestmentQualityView"));
const StateCapexEvaluationView = lazy(() => import("./StateCapexEvaluationView"));
const CrowdingInView = lazy(() => import("./CrowdingInView"));

export default function MetricPanel({ indicator, assets }: { indicator: Indicator; assets: Record<string, StaticDataAsset> }) {
  const [viewId, setViewId] = useState(indicator.default_view);
  const view = indicator.views.find((candidate) => candidate.id === viewId) ?? indicator.views[0];
  const asset = assets[view.asset_id];
  const query = useIndicatorData(asset);
  if (!asset) return <ErrorPanel message={`Missing catalogue asset ${view.asset_id}`} />;

  return <article id={indicator.id} className="metric-panel">
    <header className="metric-header"><div><span>{asset.expected_frequency} · {asset.schema.replaceAll("_", " ")}</span><h2>{indicator.title}</h2><p>{indicator.summary}</p></div>{query.data && <DataStatusBadge generatedAt={String(query.data.metadata.generated_at)} staleAfterDays={asset.stale_after_days} />}</header>
    {indicator.views.length > 1 && <div className="view-tabs">{indicator.views.map((candidate) => <button key={candidate.id} className={candidate.id === view.id ? "active" : ""} onClick={() => setViewId(candidate.id)}>{candidate.label}</button>)}</div>}
    {view.note && <p className="metric-note">{view.note}</p>}
    {asset.availability === "planned" && <PlannedPanel />}
    {query.isLoading && <LoadingPanel />}
    {query.error && <ErrorPanel message={query.error.message} />}
    {query.data && <Suspense fallback={<LoadingPanel />}>{(() => {
      assertAdapterMatchesSchema(view.presentation.component, asset.schema);
      if (view.presentation.component === "capex-correlation" && "series" in query.data) {
        return <><CapexCorrelationView payload={query.data} /><SourcePanel payload={query.data} /></>;
      }
      if (view.presentation.component === "corporate-fundamentals" && "series" in query.data) {
        return <><CorporateFundamentalsView payload={query.data} /><SourcePanel payload={query.data} /></>;
      }
      if (view.presentation.component === "fiscal-bridge" && "series" in query.data) {
        return <><FiscalBridgeView payload={query.data} /><SourcePanel payload={query.data} /></>;
      }
      if (view.presentation.component === "capex-scenario-lab" && "series" in query.data) {
        return <><CapexScenarioLab payload={query.data} /><SourcePanel payload={query.data} /></>;
      }
      if (view.presentation.component === "investment-quality" && "series" in query.data) {
        return <><InvestmentQualityView payload={query.data} /><SourcePanel payload={query.data} /></>;
      }
      if (view.presentation.component === "state-capex-evaluation" && "series" in query.data) {
        return <><StateCapexEvaluationView payload={query.data} /><SourcePanel payload={query.data} /></>;
      }
      if (view.presentation.component === "crowding-in" && "series" in query.data) {
        return <><CrowdingInView payload={query.data} /><SourcePanel payload={query.data} /></>;
      }
      return <><div className="analysis-grid"><section className="chart-card"><div className="chart-title"><div><span>Time series</span><h3>{indicator.title}</h3></div><b>{asset.expected_frequency}</b></div><ChartView key={view.id} payload={query.data} presentation={view.presentation} /></section><aside className="ranking-card"><div className="rail-heading"><span>Latest reading</span><h3>Selected series</h3></div><InsightRail payload={query.data} presentation={view.presentation} /></aside></div><SourcePanel payload={query.data} /></>;
    })()}</Suspense>}
  </article>;
}
