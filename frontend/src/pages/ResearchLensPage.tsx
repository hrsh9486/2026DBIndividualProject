import { useEffect } from "react";
import { Navigate, useLocation, useParams } from "react-router-dom";
import EvidencePanel from "../components/EvidencePanel";
import CapexVerdict from "../components/CapexVerdict";
import MetricPanel from "../components/MetricPanel";
import { ErrorPanel, LoadingPanel } from "../components/StatePanel";
import { useCatalogue } from "../hooks/useCatalogue";

export default function ResearchLensPage() {
  const { sectionId } = useParams();
  const location = useLocation();
  const { data, isLoading, error } = useCatalogue();
  useEffect(() => {
    if (!data || !location.hash) return;
    requestAnimationFrame(() => document.getElementById(location.hash.slice(1))?.scrollIntoView());
  }, [data, location.hash, sectionId]);
  if (isLoading) return <LoadingPanel />;
  if (error || !data) return <ErrorPanel message={error?.message ?? "Catalogue unavailable"} />;
  const section = data.sections.find((candidate) => candidate.id === sectionId);
  if (!section) return <Navigate to="/" replace />;
  const available = section.indicators.filter((indicator) => {
    const view = indicator.views.find((candidate) => candidate.id === indicator.default_view) ?? indicator.views[0];
    return data.assets[view.asset_id]?.availability !== "planned";
  }).length;
  const evidenceAsset = section.evidence_asset_id
    ? data.assets[section.evidence_asset_id]
    : undefined;
  return <div className="lens-page">
    <header className="lens-header"><span>Research lens {String(section.order).padStart(2, "0")}</span><h1>{section.label}</h1><p>{available} of {section.indicators.length} metric{section.indicators.length === 1 ? "" : "s"} currently available. Scroll through definitions and evidence.</p></header>
    <nav className="lens-jump" aria-label={`${section.label} metrics`}>
      {evidenceAsset && <a href="#evidence"><span>E</span>Evidence assessment</a>}
      {section.indicators.map((indicator, index) => <a key={indicator.id} href={`#${indicator.id}`}><span>{String(index + 1).padStart(2, "0")}</span>{indicator.title}</a>)}
    </nav>
    {section.id === "capex-transmission" && <CapexVerdict />}
    {evidenceAsset && <EvidencePanel asset={evidenceAsset} />}
    <div className="metric-stack">{section.indicators.map((indicator) => <MetricPanel key={indicator.id} indicator={indicator} assets={data.assets} />)}</div>
  </div>;
}
